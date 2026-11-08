"""Opt-in localhost integration check; synthetic data never enters the real corpus.

Requires a running server and private/runtime.env from prepare_runtime.py.
This creates a labelled QA workspace/dataset and automated fixture responses,
not independent human annotations. Credentials and response text are not printed.
"""
import argparse
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

import argilla as rg
import taglab_argilla as bridge

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'workbench'))
import core
import argilla_bridge as local
from tests_support import seed


def runtime_client():
    path = ROOT / 'private/runtime.env'
    values = dict(line.split('=', 1) for line in path.read_text(encoding='utf-8').splitlines()
                  if line and not line.startswith('#'))
    return rg.Argilla(api_url='http://127.0.0.1:6900', api_key=values['ARGILLA_API_KEY'], retries=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-local-qa', action='store_true', required=True)
    parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    qa_root = ROOT / 'private' / ('live-qa-' + stamp)
    qa_root.mkdir(parents=True, exist_ok=False)
    core.ROOT, core.DB = qa_root, qa_root / 'fixture.sqlite3'
    seed(qa_root)
    core.init()
    core.prepare()
    bundle = local.build_bundle('pilot', 'blind')
    bundle['records'] = bundle['records'][:4]
    bundle = bridge.seal(bundle)
    bridge.validate_bundle(bundle)
    client = runtime_client()
    workspace = client.workspaces(name='taglab-qa')
    if workspace is None:
        workspace = rg.Workspace(name='taglab-qa', client=client).create()
    bot = client.users(username='taglab-qa-bot')
    if bot is None:
        bot = rg.User(username='taglab-qa-bot', first_name='Automated QA fixtures',
                      password=secrets.token_urlsafe(24), client=client).create()
        bot.add_to_workspace(workspace)
    dataset = rg.Dataset(name='qa-synthetic-' + stamp, workspace=workspace,
                         settings=bridge.settings(bundle, client), client=client).create()
    records = bridge.records(bundle, client)
    for index, record in enumerate(records):
        values = {'topics': ['business'], 'format': 'unknown', 'review_state': 'confirmed',
                  'evidence_business': '企业经营与市场竞争',
                  'notes': 'AUTOMATED SYNTHETIC FIXTURE; NOT A HUMAN QUALITY REFERENCE'}
        if index == 2:
            values['evidence_business'] = '企业经营...市场竞争'
        fields = record.fields.to_dict()
        if index == 3:
            fields['description'] += ' REMOTE CHANGE FOR INTEGRITY TEST'
        responses = [rg.Response(question_name=k, value=v, user_id=bot.id,
                                 status='draft' if index == 1 else 'submitted')
                     for k, v in values.items()]
        records[index] = rg.Record(id=record.id, fields=fields, metadata=record.metadata.to_dict(),
                                   responses=responses)
    dataset.records.log(records)
    exported = [bridge.export_record(r) for r in dataset.records(with_responses=True)]
    assert len(exported) == 4, 'Server record count mismatch'
    result = bridge.proposals(bundle, exported)
    assert len(result['proposals']) == 1, 'Only the valid submitted response should be accepted'
    assert len(result['rejected']) == 2, 'Invalid quote and changed input should be rejected'
    assert any('Quote' in r['error'] for r in result['rejected'])
    assert any('modified' in r['error'] for r in result['rejected'])
    assert core.stats()['reviewed'] == 0
    local.stage(result, bundle)
    local.stage(result, bundle)
    assert core.stats()['reviewed'] == 0, 'Staging must not change references'
    with core.db() as connection:
        assert connection.execute('SELECT COUNT(*) FROM argilla_proposals').fetchone()[0] == 1
    proposal_id = result['proposals'][0]['proposal_id']
    local.adjudicate(proposal_id, 'automated-qa-fixture', 'Synthetic integration check only; excluded from real metrics')
    assert core.stats()['reviewed'] == 1
    try:
        local.adjudicate(proposal_id, 'automated-qa-fixture', 'Duplicate integration check')
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate adjudication must fail')
    report = {'at': stamp, 'server_sync': True, 'synthetic_only': True,
              'workspace': workspace.name, 'dataset': dataset.name, 'dataset_id': str(dataset.id),
              'server_records': 4, 'valid_submitted': 1, 'draft_ignored': 1,
              'invalid_quote_rejected': True, 'modified_input_rejected': True,
              'staging_did_not_change_references': True, 'staging_idempotent': True,
              'isolated_fixture_adjudicated': True, 'duplicate_adjudication_rejected': True,
              'qa_database': str(core.DB), 'real_corpus_modified': False,
              'browser_submission_tested': False}
    (qa_root / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
