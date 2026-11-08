import copy,json,sys
from pathlib import Path
from uuid import uuid4
import pytest
import argilla as rg
sys.path.insert(0,str(Path(__file__).parents[1]))
import taglab_argilla as t

@pytest.fixture
def bundle():
 t.offline_client()
 tax={'version':'fixture-v1','rules':['仅看正文'],'topics':[{'id':'business','name':'商业','definition':'企业经营','exclude':'仅提及价格'}],
  'formats':[{'id':'unknown','name':'无法判断'},{'id':'interview','name':'访谈'}]}
 row={'record_id':'fixture-1','title':'餐饮企业','text':'本文分析企业经营与竞争。','split':'pilot','annotation_revision':0,'candidate':None,'candidate_error':None}
 row['input_hash']=t.input_hash(row['title'],row['text'])
 return t.seal({'schema_version':t.SCHEMA_VERSION,'mode':'blind','taxonomy':tax,'experiment_id':None,'strategy':None,'records':[row]})

def exported(bundle,users=1):
 record=t.records(bundle)[0];responses=[]
 for _ in range(users):
  uid=uuid4()
  for k,v in {'topics':['business'],'format':'unknown','review_state':'confirmed','evidence_business':'企业经营与竞争','notes':'仅依据正文'}.items():
   responses.append(rg.Response(question_name=k,value=v,user_id=uid,status='submitted'))
 record=rg.Record(id=record.id,fields=record.fields.to_dict(),responses=responses)
 return t.export_record(record)

def test_real_sdk_schema_and_record(bundle):
 s=t.settings(bundle);r=t.records(bundle)[0]
 assert len(s.questions)==6 # topics,format,state,one topic evidence,format evidence,notes = 6
 assert not r.responses.to_dict();assert not r.suggestions.to_dict()
 assert r.api_model().model_dump(mode='json')['external_id']==t.external_id(bundle['records'][0])

def test_blind_rejects_candidate(bundle):
 bundle['records'][0]['candidate']={'topics':['business']};bundle=t.seal(bundle)
 with pytest.raises(ValueError,match='Blind'):t.validate_bundle(bundle)

def test_holdout_excluded(bundle):
 bundle['records'][0]['split']='test';bundle=t.seal(bundle)
 with pytest.raises(ValueError,match='Test records'):t.validate_bundle(bundle)

def test_multiple_authors_not_merged(bundle):
 data=exported(bundle,2);result=t.proposals(bundle,[data])
 assert len(result['proposals'])==2;assert not result['rejected']
 assert len({x['reviewer'] for x in result['proposals']})==2

def test_suggestions_never_become_human(bundle):
 data=t.records(bundle)[0].to_dict();data['suggestions']={'topics':{'value':['business']}}
 assert not t.proposals(bundle,[data])['proposals']

def test_reject_remote_input_change(bundle):
 data=exported(bundle);data['fields']['description']='changed'
 assert 'modified' in t.proposals(bundle,[data])['rejected'][0]['error']

def test_reject_paraphrased_evidence(bundle):
 data=exported(bundle);data['responses']['evidence_business'][0]['value']='企业...竞争'
 assert not t.proposals(bundle,[data])['proposals']

def test_pasted_boundary_whitespace_is_removed_with_audit(bundle):
 data=exported(bundle);original=' \n企业经营与竞争\n \n'
 data['responses']['evidence_business'][0]['value']=original
 result=t.proposals(bundle,[data]);assert not result['rejected']
 proposal=result['proposals'][0]
 assert proposal['label']['evidence']['business']=='企业经营与竞争'
 assert proposal['normalizations']==[{'question':'evidence_business','action':'strip_boundary_whitespace',
  'original_value':original,'normalized_value':'企业经营与竞争'}]
 assert data['responses']['evidence_business'][0]['value']==original

def test_boundary_normalization_does_not_repair_internal_changes(bundle):
 data=exported(bundle);data['responses']['evidence_business'][0]['value']=' \n企业经营...竞争\n '
 result=t.proposals(bundle,[data]);assert not result['proposals']
 assert 'Quote' in result['rejected'][0]['error']

def test_verbatim_quotes_do_not_change_proposal_schema(bundle):
 result=t.proposals(bundle,[exported(bundle)])
 assert len(result['proposals'])==1
 assert 'normalizations' not in result['proposals'][0]

def test_draft_not_imported(bundle):
 data=exported(bundle)
 for answers in data['responses'].values():
  for a in answers:a['status']='draft'
 assert not t.proposals(bundle,[data])['proposals']

def test_fingerprint_prevents_changed_text(bundle):
 bundle['records'][0]['text']='tampered'
 with pytest.raises(ValueError,match='fingerprint'):t.validate_bundle(bundle)

def test_review_suggestions_and_support_judgment(bundle):
 b=copy.deepcopy(bundle);b['mode']='review';b['experiment_id']='synthetic-run';b['strategy']='B'
 b['records'][0]['candidate']={'topics':['business'],'format':'unknown'};b=t.seal(b)
 r=t.records(b)[0];assert r.suggestions.to_dict()['topics']['agent']=='taglab:synthetic-run:B'
 assert not r.responses.to_dict()
 data=exported(b);result=t.proposals(b,[data]);assert result['rejected']

def test_url_guard():
 assert t.safe_url('http://127.0.0.1:6900')
 assert not t.safe_url('http://remote.example')
 assert not t.safe_url('https://user:key@example.org')
