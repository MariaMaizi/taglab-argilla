import json,sys
from pathlib import Path
from uuid import uuid4
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'workbench'))
import core,argilla_bridge as b
from tests_support import seed

@pytest.fixture
def local(tmp_path):
 old,oldroot=core.DB,core.ROOT
 core.DB=tmp_path/'test.sqlite';core.ROOT=tmp_path
 seed(tmp_path);core.prepare()
 yield
 core.DB,core.ROOT=old,oldroot

def make_proposal(bundle,record_index=0):
 b.bridge.offline_client()
 r=b.bridge.records(bundle)[record_index];uid=uuid4()
 import argilla as rg
 values={'topics':['business'],'format':'unknown','review_state':'confirmed','evidence_business':'企业经营与市场竞争','notes':'synthetic fixture'}
 responses=[rg.Response(question_name=k,value=v,user_id=uid,status='submitted') for k,v in values.items()]
 record=rg.Record(id=r.id,fields=r.fields.to_dict(),responses=responses)
 return b.bridge.proposals(bundle,[b.bridge.export_record(record)])

def test_blind_export_hides_existing_labels(local):
 bundle=b.build_bundle('pilot');assert len(bundle['records'])==20
 assert all('reference' not in x and not x['candidate'] for x in bundle['records'])
 with pytest.raises(ValueError):b.build_bundle('test')

def test_stage_then_adjudicate_is_explicit_and_idempotent(local):
 bundle=b.build_bundle('pilot');res=make_proposal(bundle);pid=res['proposals'][0]['proposal_id']
 b.stage(res,bundle);b.stage(res,bundle)
 assert core.stats()['reviewed']==0
 saved=b.adjudicate(pid,'fixture-adjudicator','synthetic test only');assert saved['revision']==1
 assert core.stats()['reviewed']==1
 with pytest.raises(ValueError):b.adjudicate(pid,'fixture-adjudicator','second try')

def test_stale_reference_rejected(local):
 bundle=b.build_bundle('pilot');res=make_proposal(bundle);r=core.record(res['proposals'][0]['record_id'])
 b.stage(res,bundle)
 core.save_annotation(r['record_id'],{'input_text':r['clean']['text'],'reviewer':'fixture','topics':[],'format':'unknown','evidence':{},'needs_review':True,'note':'fixture','revision':0})
 with pytest.raises(ValueError,match='revision'):b.stage(res,bundle)

def test_accepted_replay_is_a_no_op(local):
 bundle=b.build_bundle('pilot');res=make_proposal(bundle)
 b.stage(res,bundle);b.adjudicate(res['proposals'][0]['proposal_id'],'fixture-adjudicator','synthetic test only')
 result=b.stage(res,bundle)
 assert result=={'staged':0,'already_staged':0,'already_accepted':1,'gold_updated':False}
 assert core.stats()['reviewed']==1

def test_replay_accepts_later_answers_from_same_export(local):
 bundle=b.build_bundle('pilot');res=make_proposal(bundle)
 b.stage(res,bundle);b.adjudicate(res['proposals'][0]['proposal_id'],'fixture-adjudicator','synthetic test only')
 later=make_proposal(bundle,1);later['proposals']=res['proposals']+later['proposals']
 result=b.stage(later,bundle)
 assert result=={'staged':1,'already_staged':0,'already_accepted':1,'gold_updated':False}
 with core.db() as c:
  assert c.execute('select count(*) from argilla_proposals').fetchone()[0]==2
 assert core.stats()['reviewed']==1

def test_accepted_replay_still_checks_bundle_provenance(local):
 import copy
 bundle=b.build_bundle('pilot');res=make_proposal(bundle)
 b.stage(res,bundle);b.adjudicate(res['proposals'][0]['proposal_id'],'fixture-adjudicator','synthetic test only')
 other=copy.deepcopy(bundle);other['records']=other['records'][1:];other=b.bridge.seal(other)
 replay=copy.deepcopy(res);replay['bundle_fingerprint']=other['fingerprint']
 with pytest.raises(ValueError,match='provenance'):b.stage(replay,other)

def test_bad_proposal_rolls_back_entire_stage(local):
 bundle=b.build_bundle('pilot');res=make_proposal(bundle)
 import copy
 bad=copy.deepcopy(res['proposals'][0]);bad['proposal_id']='tampered';res['proposals'].append(bad)
 with pytest.raises(ValueError):b.stage(res,bundle)
 with core.db() as c:assert c.execute('select count(*) from argilla_proposals').fetchone()[0]==0

def test_model_visible_feedback_cannot_become_independent_reference(local):
 bundle=b.build_bundle('pilot');bundle['mode']='review';bundle['experiment_id']='synthetic-run';bundle['strategy']='B'
 bundle=b.bridge.seal(bundle)
 b.bridge.offline_client()
 r=b.bridge.records(bundle)[0]
 import argilla as rg
 uid=uuid4()
 values={'topics':['business'],'format':'unknown','review_state':'needs_review',
  'evidence_business':'企业经营与市场竞争','notes':'synthetic disputed feedback','semantic_support':'uncertain'}
 responses=[rg.Response(question_name=k,value=v,user_id=uid,status='submitted') for k,v in values.items()]
 record=rg.Record(id=r.id,fields=r.fields.to_dict(),responses=responses)
 result=b.bridge.proposals(bundle,[b.bridge.export_record(record)])
 b.stage(result,bundle)
 with pytest.raises(ValueError,match='Model-visible'):
  b.adjudicate(result['proposals'][0]['proposal_id'],'fixture','must remain feedback')
 assert core.stats()['reviewed']==0
