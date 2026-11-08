# Copyright 2026 TagLab contributors. Licensed under Apache-2.0.
"""Argilla extension: immutable review bundles and validated human proposals.

No model calls, automatic gold-label writes, or credentials in exported bundles.
"""
import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import argilla as rg
import httpx

SCHEMA_VERSION = 'taglab-argilla-v1'

def offline_client():
    """Real SDK, explicitly mocked authentication; never a live-server check."""
    def handle(request):
        if request.url.path == '/api/v1/me':
            return httpx.Response(200, json={'id': '00000000-0000-0000-0000-000000000001',
                                            'username': 'offline-fixture', 'role': 'owner'})
        raise AssertionError('Unexpected offline HTTP request: ' + request.url.path)
    return rg.Argilla(api_url='http://offline.invalid', api_key='not-a-real-key',
                      retries=0, transport=httpx.MockTransport(handle))

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def input_hash(title, text):
    return fingerprint({'title': title, 'text': text})

def seal(bundle):
    body = {k: v for k, v in bundle.items() if k != 'fingerprint'}
    return {**body, 'fingerprint': fingerprint(body)}

def validate_bundle(bundle):
    if bundle.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('Unsupported bundle version')
    if seal(bundle)['fingerprint'] != bundle.get('fingerprint'):
        raise ValueError('Bundle fingerprint mismatch')
    if bundle['mode'] not in ('blind', 'review'):
        raise ValueError('Unknown mode')
    ids = set()
    for row in bundle['records']:
        if row['split'] not in ('pilot', 'dev'):
            raise ValueError('Test records cannot enter this development bridge')
        if row['record_id'] in ids:
            raise ValueError('Duplicate record ID')
        ids.add(row['record_id'])
        if row['input_hash'] != input_hash(row['title'], row['text']):
            raise ValueError('Input fingerprint mismatch')
        if bundle['mode'] == 'blind' and (row.get('candidate') or row.get('candidate_error')):
            raise ValueError('Blind annotation must not expose model suggestions')
    if not ids:
        raise ValueError('Empty bundle')
    return True

def settings(bundle, client=None):
    """Argilla schema. Max-three and exact quotations are checked on return."""
    tax = bundle['taxonomy']
    guidelines = '\n'.join(tax['rules']) + '\n\n' + '\n'.join(
        f"{x['name']}: {x['definition']} 反例: {x['exclude']}" for x in tax['topics'])
    guidelines += '\n\n每个已选主题填写连续原文。最多3个主题。缺少形式证据时选unknown。提交不等于裁决。'
    questions = [
        rg.MultiLabelQuestion(name='topics', title='主要主题（最多3个，无适用可留空）', required=False,
                              labels={x['id']: x['name'] for x in tax['topics']}, client=client),
        rg.LabelQuestion(name='format', title='节目形式', labels={x['id']: x['name'] for x in tax['formats']}, client=client),
        rg.LabelQuestion(name='review_state', title='是否已能确定判断？',
                         labels={'confirmed': '已确认', 'needs_review': '仍需复核'}, client=client),
    ]
    questions += [rg.TextQuestion(name='evidence_' + x['id'], title=x['name'] + '：连续原文依据',
                                 required=False, client=client) for x in tax['topics']]
    questions += [rg.TextQuestion(name='evidence_format', title='节目形式：连续原文依据', required=False, client=client),
                  rg.TextQuestion(name='notes', title='判断说明、争议或缺失信息', required=False, client=client)]
    if bundle['mode'] == 'review':
        questions.append(rg.LabelQuestion(name='semantic_support', title='候选结论是否被原文充分支持？',
                         labels={'supported': '支持', 'unsupported': '不支持', 'uncertain': '无法确定'}, client=client))
    fields = [rg.TextField(name='title', title='节目标题', use_markdown=False),
              rg.TextField(name='description', title='实际输入简介', use_markdown=False)]
    if bundle['mode'] == 'review':
        fields.append(rg.TextField(name='candidate', title='机器候选（不是人工答案）', use_markdown=False))
    return rg.Settings(guidelines=guidelines, fields=fields, questions=questions,
                       metadata=[rg.TermsMetadataProperty(name='split', options=['pilot', 'dev'], visible_for_annotators=False),
                                 rg.TermsMetadataProperty(name='input_hash', visible_for_annotators=False)])

def external_id(row):
    return row['record_id'] + ':' + row['input_hash'][:16]

def records(bundle, client=None):
    validate_bundle(bundle)
    result = []
    for row in bundle['records']:
        fields = {'title': row['title'], 'description': row['text']}
        suggestions = []
        candidate = row.get('candidate')
        if bundle['mode'] == 'review':
            fields['candidate'] = json.dumps(candidate or {'error': row.get('candidate_error', 'No valid output')}, ensure_ascii=False)
            if candidate:
                agent = 'taglab:' + bundle['experiment_id'] + ':' + bundle['strategy']
                suggestions = [rg.Suggestion(question_name='topics', value=candidate['topics'], agent=agent),
                               rg.Suggestion(question_name='format', value=candidate['format'], agent=agent)]
        result.append(rg.Record(id=external_id(row), fields=fields,
                               metadata={'split': row['split'], 'input_hash': row['input_hash']}, suggestions=suggestions))
    return result

def validate_answer(bundle, row, values):
    tax = bundle['taxonomy']
    topics = values.get('topics') or []
    if not isinstance(topics, list) or any(not isinstance(t, str) for t in topics):
        raise ValueError('Topic IDs must be a list of strings')
    if len(topics) > 3 or len(set(topics)) != len(topics) or set(topics) - {x['id'] for x in tax['topics']}:
        raise ValueError('Choose up to three valid unique topics')
    fmt = values.get('format')
    if fmt not in {x['id'] for x in tax['formats']}:
        raise ValueError('Invalid format')
    state = values.get('review_state')
    if state not in ('confirmed', 'needs_review'):
        raise ValueError('Missing review decision')
    text = row['title'] + '\n' + row['text']
    evidence = {k: values.get('evidence_' + k, '') for k in topics}
    evidence['format'] = values.get('evidence_format', '')
    for k in topics + (['format'] if fmt != 'unknown' else []):
        quote = evidence[k]
        if not isinstance(quote, str) or not 2 <= len(quote) <= 500 or quote not in text:
            raise ValueError('Quote must be an exact continuous input substring: ' + k)
    note = values.get('notes') or ''
    if not isinstance(note, str):
        raise ValueError('Notes must be text')
    if not topics and not note.strip():
        raise ValueError('Empty topics require an explanation')
    semantic = values.get('semantic_support')
    if bundle['mode'] == 'review' and semantic not in ('supported', 'unsupported', 'uncertain'):
        raise ValueError('Missing semantic support judgment')
    return {'topics': topics, 'format': fmt, 'evidence': evidence,
            'needs_review': state == 'needs_review', 'note': note, 'semantic_support': semantic}

def export_record(record):
    """Preserve submission status, which upstream Record.to_dict omits."""
    data = record.to_dict()
    responses = defaultdict(list)
    for response in record.responses:
        status = getattr(response.status, 'value', response.status)
        responses[response.question_name].append({'value': response.value,
            'user_id': str(response.user_id), 'status': status})
    data['responses'] = dict(responses)
    return data

def proposals(bundle, exported_records):
    """Decode status-preserving export. Never read suggestions as responses."""
    validate_bundle(bundle)
    manifest = {external_id(r): r for r in bundle['records']}
    accepted, rejected = [], []
    for record in exported_records:
        rid = record.get('id')
        try:
            if rid not in manifest:
                raise ValueError('Record is not part of this bundle')
            source = manifest[rid]
            fields = record.get('fields', {})
            if fields.get('title') != source['title'] or fields.get('description') != source['text']:
                raise ValueError('Remote input was modified')
            by_user = defaultdict(dict)
            for question, responses in record.get('responses', {}).items():
                for response in responses:
                    if response.get('status') != 'submitted':
                        continue
                    uid = str(response.get('user_id') or '')
                    if not uid:
                        raise ValueError('Missing response author')
                    if question in by_user[uid]:
                        raise ValueError('Duplicate response for same author/question')
                    by_user[uid][question] = response.get('value')
            for uid, values in by_user.items():
                try:
                    label = validate_answer(bundle, source, values)
                    body = {'bundle_fingerprint': bundle['fingerprint'], 'mode': bundle['mode'],
                            'record_id': source['record_id'], 'input_hash': source['input_hash'],
                            'annotation_revision': source['annotation_revision'], 'reviewer': 'argilla:' + uid,
                            'label': label, 'taxonomy_hash': fingerprint(bundle['taxonomy'])}
                    accepted.append({**body, 'proposal_id': fingerprint(body)[:24], 'status': 'staged'})
                except ValueError as exc:
                    rejected.append({'record_id': source['record_id'], 'user_id': uid, 'error': str(exc)})
        except ValueError as exc:
            rejected.append({'record_id': rid, 'error': str(exc)})
    return {'schema_version': SCHEMA_VERSION, 'bundle_fingerprint': bundle['fingerprint'],
            'proposals': accepted, 'rejected': rejected}

def safe_url(url):
    p = urlparse(url)
    return not p.username and not p.password and not p.query and not p.fragment and (
        p.scheme == 'https' or (p.scheme == 'http' and p.hostname in ('127.0.0.1', 'localhost')))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['validate', 'push', 'pull'])
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--dataset', default=None)
    parser.add_argument('--workspace', default='default')
    parser.add_argument('--output', type=Path, default=Path('private/proposals.json'))
    parser.add_argument('--confirm-upload', action='store_true')
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding='utf-8-sig'));validate_bundle(bundle)
    if args.action == 'validate':
        # SDK construction does not test server availability.
        offline_client()
        s = settings(bundle);rr = records(bundle)
        for r in rr:
            r.api_model().model_dump(mode='json')
        print(json.dumps({'records': len(rr), 'questions': len(s.questions), 'sdk_validation': 'passed', 'server_sync': False}))
        return
    url = os.environ.get('ARGILLA_API_URL', 'http://127.0.0.1:6900')
    if not safe_url(url):
        raise ValueError('Use localhost HTTP or a credential-free HTTPS endpoint')
    key = os.environ.get('ARGILLA_API_KEY')
    if not key:
        raise ValueError('ARGILLA_API_KEY is required; it is not a model-provider key')
    client = rg.Argilla(api_url=url, api_key=key, retries=0)
    name = args.dataset or 'taglab-' + bundle['mode'] + '-' + bundle['fingerprint'][:12]
    if args.action == 'push':
        if not args.confirm_upload:
            raise ValueError('Inspect bundle and endpoint, then pass --confirm-upload')
        if client.datasets(name=name, workspace=args.workspace) is not None:
            raise ValueError('Dataset exists; refusing to overwrite immutable input')
        dataset = rg.Dataset(name=name, workspace=args.workspace, settings=settings(bundle, client), client=client).create()
        dataset.records.log(records(bundle, client))
        print(json.dumps({'dataset': name, 'records': len(bundle['records']), 'server_sync': True}))
    else:
        dataset = client.datasets(name=name, workspace=args.workspace)
        if dataset is None:
            raise ValueError('Dataset not found')
        exported = [export_record(r) for r in dataset.records(with_responses=True)]
        result = proposals(bundle, exported)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'staged': len(result['proposals']), 'rejected': len(result['rejected']), 'gold_updated': False}))

if __name__ == '__main__':
    main()
