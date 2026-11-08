"""Re-evaluate saved outputs against current references; never call a model.

This is a reference-revision analysis, not a new blinded benchmark. The original
experiment remains unchanged. Inputs and taxonomy must match the original run.
"""
import argparse
import copy
import json
from pathlib import Path

import core

VERSION = 'reference-audit-v2'


def rescore(experiment, current_records, taxonomy):
    if experiment['status'] not in ('completed', 'completed_with_errors', 'failed'):
        raise ValueError('Only finished experiments can be audited')
    if core.digest(experiment['taxonomy_snapshot']) != core.digest(taxonomy) or core.digest(taxonomy) != core.digest(core.TAX):
        raise ValueError('Taxonomy changed; do not reuse outputs under a new label definition')
    current = {record['record_id']: record for record in current_records}
    rows = copy.deepcopy(experiment['rows'])
    references, changes = [], []
    for row in rows:
        record = current.get(row['record_id'])
        if record is None:
            raise ValueError('Source record missing: ' + row['record_id'])
        original_hash = core.digest({'title': row['title'], 'text': row['text']})
        current_hash = core.digest({'title': record['episode_title'], 'text': core.input_text(record)})
        if original_hash != row['input_hash'] or current_hash != original_hash:
            raise ValueError('Input changed: ' + row['record_id'])
        reference = record['annotation']
        if reference:
            if reference.get('taxonomy_hash') != core.digest(taxonomy):
                raise ValueError('Reference taxonomy mismatch: ' + row['record_id'])
            if reference.get('input_hash') != original_hash:
                raise ValueError('Reference input mismatch: ' + row['record_id'])
            core.validate_labels(reference, row['title'] + '\n' + row['text'], True)
        old_reference = row['reference']
        snapshot = {'record_id': row['record_id'], 'revision': record['revision'],
                    'input_hash': original_hash, 'reference': copy.deepcopy(reference)}
        references.append(snapshot)
        if core.digest(old_reference) != core.digest(reference):
            fields = ('topics', 'format', 'evidence', 'needs_review')
            changes.append({'record_id': row['record_id'], 'current_revision': record['revision'],
                            'old_reference_hash': core.digest(old_reference),
                            'new_reference_hash': core.digest(reference),
                            'changed_label_fields': [field for field in fields
                                if (old_reference or {}).get(field) != (reference or {}).get(field)]})
        row['reference'] = copy.deepcopy(reference)
    source_hash = core.digest(experiment)
    predictions_hash = core.digest([{'record_id': row['record_id'], 'input_hash': row['input_hash'],
                                     'predictions': row['predictions']} for row in experiment['rows']])
    reference_hash = core.digest(references)
    identity = {'version': VERSION, 'source_experiment_hash': source_hash,
                'predictions_hash': predictions_hash, 'reference_hash': reference_hash}
    revised_metrics = {strategy: core.score(rows, strategy) for strategy in ('A', 'B')}
    for metrics in revised_metrics.values():
        metrics['note'] = '仅对当前参考快照评分，复用已保存预测；事后参考修订，不代表新的独立模型评测。'
    return {'audit_id': core.digest(identity)[:16], **identity,
            'type': 'reference_revision_analysis', 'source_experiment_id': experiment['id'],
            'created_at': core.now(), 'sample_count': len(rows), 'model_calls': 0,
            'original_metrics': copy.deepcopy(experiment['metrics']),
            'revised_metrics': revised_metrics,
            'reference_changes': changes, 'reference_snapshot': references,
            'source_experiment_modified': False,
            'interpretation': 'Score changes come from reference revisions, not new model outputs or model improvement; post-output revisions are not independent test references.'}


def markdown(audit):
    lines = ['# 参考修订后的评分对照', '',
             f"来源实验：`{audit['source_experiment_id']}`；分析：`{audit['audit_id']}`。",
             f"输入 {audit['sample_count']} 条，新增模型调用 **0 次**。原实验、原输出和原分数保持不变。", '',
             '| 指标 | A 原参考 | A 修订参考 | B 原参考 | B 修订参考 |',
             '| --- | ---: | ---: | ---: | ---: |']
    for name, key in [('有效参考数', 'reference_count'), ('主题 micro F1', 'f1'),
                      ('形式匹配率', 'format_accuracy'), ('完全匹配率', 'exact_match')]:
        values = [audit[which][strategy].get(key) for strategy in ('A', 'B')
                  for which in ('original_metrics', 'revised_metrics')]
        lines.append('| ' + name + ' | ' + ' | '.join('不可计算' if value is None else f'{value:.4g}' for value in values) + ' |')
    lines += ['', '## 变化来源', '',
              '本表复用原预测，仅更新参考快照。分数上升或下降不表示模型能力发生变化。看过输出后的参考修订属于事后复核，不能当作新的独立测试集结果。', '',
              '程序核对了输入哈希、标签规范和参考对应关系。带“仍需复核”的参考不会进入评分；机器复核反馈不会自动变成人工参考。', '',
              '## 参考修订记录', '']
    for change in audit['reference_changes']:
        lines.append(f"- `{change['record_id']}`：当前参考版本 {change['current_revision']}，变化字段：" + ('、'.join(change['changed_label_fields']) or '仅元数据变化') + '。')
    lines += ['', '原实验保存了原参考内容快照，但未保存原参考的数字修订号；这里以原内容哈希追溯，不补造旧修订号。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_id')
    args = parser.parse_args()
    experiment = core.experiment(args.experiment_id)
    audit = rescore(experiment, core.all_records(), core.TAX)
    assert core.digest(core.experiment(args.experiment_id)) == audit['source_experiment_hash']
    destination = core.ROOT / 'data/reports'
    destination.mkdir(parents=True, exist_ok=True)
    base = destination / (args.experiment_id + '-reference-audit-' + audit['audit_id'])
    json_path, markdown_path = base.with_suffix('.json'), base.with_suffix('.md')
    if json_path.exists():
        saved = json.loads(json_path.read_text(encoding='utf-8'))
        if any(saved[key] != audit[key] for key in ('audit_id', 'source_experiment_hash', 'predictions_hash', 'reference_hash')):
            raise ValueError('Existing audit identity mismatch')
        audit = saved
    else:
        with json_path.open('x', encoding='utf-8') as output:
            output.write(json.dumps(audit, ensure_ascii=False, indent=2))
    if not markdown_path.exists():
        with markdown_path.open('x', encoding='utf-8') as output:
            output.write(markdown(audit))
    print(json.dumps({'audit_id': audit['audit_id'], 'model_calls': 0, 'report': str(markdown_path),
                      'json': str(json_path), 'revised_metrics': audit['revised_metrics']}))


if __name__ == '__main__':
    main()
