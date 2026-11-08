"""Reference changes must not be presented as new model performance."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / 'workbench'))
import core
import reference_audit as audit


def fixture():
    title, text = '企业观察', '这段资料讨论企业经营与市场竞争。'
    input_hash = core.digest({'title': title, 'text': text})
    reference = {'topics': ['business', 'life'], 'format': 'unknown',
                 'evidence': {'business': '企业经营与市场竞争', 'life': '企业经营与市场竞争', 'format': ''},
                 'needs_review': False, 'note': 'synthetic scoring fixture, not real labels',
                 'input_text': text, 'input_hash': input_hash, 'taxonomy_hash': core.digest(core.TAX)}
    prediction = {'topics': ['business'], 'format': 'unknown',
                  'evidence': {'business': '企业经营与市场竞争', 'format': ''}, 'needs_review': False}
    row = {'record_id': 'fixture-1', 'title': title, 'text': text, 'input_hash': input_hash,
           'reference': reference, 'predictions': {'A': {'output': prediction}, 'B': {'error': 'invalid fixture'}}}
    experiment = {'id': 'fixture-run', 'status': 'completed_with_errors', 'kind': 'llm',
                  'taxonomy_snapshot': copy.deepcopy(core.TAX), 'rows': [row],
                  'metrics': {strategy: core.score([row], strategy) for strategy in ('A', 'B')}}
    revised = copy.deepcopy(reference)
    revised['topics'] = ['business']
    revised['evidence'].pop('life')
    record = {'record_id': 'fixture-1', 'episode_title': title, 'clean': {'text': text},
              'revision': 2, 'annotation': revised}
    return experiment, [record]


def test_revision_analysis_reuses_outputs_without_mutating_experiment():
    experiment, records = fixture()
    original = copy.deepcopy(experiment)
    result = audit.rescore(experiment, records, core.TAX)
    assert experiment == original
    assert result['model_calls'] == 0 and not result['source_experiment_modified']
    assert result['original_metrics']['A']['f1'] == pytest.approx(2 / 3)
    assert result['revised_metrics']['A']['f1'] == 1
    assert result['revised_metrics']['B']['f1'] == 0
    assert result['reference_changes'][0]['current_revision'] == 2
    assert result['type'] == 'reference_revision_analysis'


def test_changed_input_cannot_reuse_old_predictions():
    experiment, records = fixture()
    records[0]['annotation']['input_text'] += '修改正文'
    with pytest.raises(ValueError, match='Input changed'):
        audit.rescore(experiment, records, core.TAX)


def test_changed_taxonomy_cannot_reuse_old_predictions():
    experiment, records = fixture()
    taxonomy = copy.deepcopy(core.TAX)
    taxonomy['version'] = 'changed-fixture'
    with pytest.raises(ValueError, match='Taxonomy changed'):
        audit.rescore(experiment, records, taxonomy)


def test_disputed_reference_is_excluded_without_deleting_old_score():
    experiment, records = fixture()
    records[0]['annotation']['needs_review'] = True
    result = audit.rescore(experiment, records, core.TAX)
    assert result['original_metrics']['A']['reference_count'] == 1
    assert result['revised_metrics']['A']['reference_count'] == 0
    assert result['revised_metrics']['A']['f1'] is None
