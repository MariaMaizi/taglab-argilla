"""Local bridge to the Argilla fork. No production server restart needed."""
from pathlib import Path
import argparse,json,sys
import core
EXT=core.ROOT/'argilla-fork/examples/taglab'
if not EXT.exists():EXT=core.ROOT.parent  # in the public fork's workbench folder
sys.path.insert(0,str(EXT))
import taglab_argilla as bridge

def build_bundle(split='pilot', mode='blind', experiment_id=None, strategy='B'):
 if split not in ('pilot','dev'):raise ValueError('Development bridge excludes holdout test records')
 exp=core.experiment(experiment_id) if experiment_id else None
 if mode=='review' and not exp:raise ValueError('Review requires an experiment')
 if exp and exp['split']!=split:raise ValueError('Experiment split mismatch')
 if strategy not in ('A','B'):raise ValueError('Strategy must be A or B')
 rows=[]
 for r in core.all_records():
  if r['split']!=split:continue
  er=next((x for x in exp['rows'] if x['record_id']==r['record_id']),None) if exp else None
  if mode=='review' and not er:continue
  title=r['episode_title'];text=core.input_text(r)
  if er and er['input_hash']!=core.digest({'title':title,'text':text}):raise ValueError('Current input differs from experiment; create a new run')
  pred=er['predictions'].get(strategy,{}) if er else {}
  rows.append({'record_id':r['record_id'],'title':title,'text':text,'split':split,
   'input_hash':core.digest({'title':title,'text':text}),'annotation_revision':r['revision'],
   'candidate':pred.get('output') if mode=='review' else None,'candidate_error':pred.get('error') if mode=='review' else None})
 bundle=bridge.seal({'schema_version':bridge.SCHEMA_VERSION,'mode':mode,'taxonomy':core.TAX,
  'experiment_id':experiment_id if mode=='review' else None,'strategy':strategy if mode=='review' else None,'records':rows})
 bridge.validate_bundle(bundle)
 return bundle

def stage(result,bundle):
 bridge.validate_bundle(bundle)
 if result['bundle_fingerprint']!=bundle['fingerprint']:raise ValueError('Mismatched export and proposal bundle')
 known={r['record_id']:r for r in bundle['records']}
 with core.db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS argilla_proposals(id TEXT PRIMARY KEY,body TEXT NOT NULL,status TEXT NOT NULL,at TEXT NOT NULL)')
  for p in result['proposals']:
   body={k:v for k,v in p.items() if k not in ('proposal_id','status')}
   if bridge.fingerprint(body)[:24]!=p['proposal_id']:raise ValueError('Proposal integrity check failed')
   r=core.record(p['record_id']);exported=known[p['record_id']]
   if r['split']=='test':raise ValueError('Holdout cannot enter development adjudication')
   if p['input_hash']!=core.digest({'title':r['episode_title'],'text':core.input_text(r)}):raise ValueError('Local input changed')
   if p['annotation_revision']!=r['revision']:raise ValueError('Reference revision changed; re-export')
   if p['taxonomy_hash']!=core.digest(core.TAX):raise ValueError('Taxonomy changed')
   label=p['label'];core.validate_labels(label,r['episode_title']+'\n'+core.input_text(r),True)
   if p['mode']!=bundle['mode'] or p['bundle_fingerprint']!=bundle['fingerprint']:raise ValueError('Proposal provenance mismatch')
   # Revalidate full answer; never trust a file just because its hash is correct.
   values={'topics':label['topics'],'format':label['format'],'review_state':'needs_review' if label['needs_review'] else 'confirmed',
    'notes':label['note'],'semantic_support':label.get('semantic_support'),**{'evidence_'+k:v for k,v in label['evidence'].items()}}
   bridge.validate_answer(bundle,exported,values)
   c.execute('INSERT OR IGNORE INTO argilla_proposals VALUES(?,?,?,?)',(p['proposal_id'],json.dumps(p,ensure_ascii=False),'staged',core.now()))
 return {'staged':len(result['proposals']),'gold_updated':False}

def adjudicate(proposal_id, reviewer, reason):
 if not reason.strip():raise ValueError('Adjudication requires a reason')
 with core.db() as c:
  row=c.execute('select body,status from argilla_proposals where id=?',(proposal_id,)).fetchone()
 if not row or row['status']!='staged':raise ValueError('Proposal missing or already handled')
 p=json.loads(row['body'])
 if p['mode']!='blind':raise ValueError('Model-visible review cannot silently become an independent reference; use blind annotation')
 r=core.record(p['record_id'])
 if r['split']=='test' or r['revision']!=p['annotation_revision'] or p['taxonomy_hash']!=core.digest(core.TAX):raise ValueError('Split/version conflict')
 if p['input_hash']!=core.digest({'title':r['episode_title'],'text':core.input_text(r)}):raise ValueError('Input changed')
 label=p['label'];body={**label,'revision':r['revision'],'input_text':core.input_text(r),'reviewer':reviewer,
  'note':label['note']+'\nArgilla来源 '+p['reviewer']+'；裁决：'+reason}
 if not isinstance(reviewer,str) or not 1<=len(reviewer.strip())<=60:raise ValueError('Reviewer must be 1–60 characters')
 core.validate_labels(body,r['episode_title']+'\n'+body['input_text'],True)
 with core.db() as c:
  c.execute('BEGIN IMMEDIATE')
  current=c.execute('select revision from annotations where id=?',(r['record_id'],)).fetchone()
  revision=current[0] if current else 0
  proposal=c.execute('select status from argilla_proposals where id=?',(proposal_id,)).fetchone()
  if revision!=body['revision'] or not proposal or proposal[0]!='staged':raise ValueError('Concurrent update; reload before adjudication')
  stored={k:body[k] for k in ('topics','format','evidence','needs_review','note','input_text','reviewer')}
  stored.update(at=core.now(),status='reviewed',taxonomy_version=core.TAX['version'],taxonomy_hash=core.digest(core.TAX),input_hash=p['input_hash'])
  c.execute('insert or replace into annotations values(?,?,?)',(r['record_id'],revision+1,json.dumps(stored,ensure_ascii=False)))
  c.execute('update argilla_proposals set status=? where id=?',('accepted',proposal_id))
  c.execute('insert into history values(?,?,?,?)',(core.now(),r['record_id'],'argilla_adjudicated',json.dumps({'proposal_id':proposal_id,'author':p['reviewer'],'reviewer':reviewer,'reason':reason},ensure_ascii=False)))
 return {'record_id':r['record_id'],'revision':revision+1}

def main():
 p=argparse.ArgumentParser(description=__doc__);sp=p.add_subparsers(dest='action',required=True)
 e=sp.add_parser('export');e.add_argument('--split',choices=['pilot','dev'],default='pilot');e.add_argument('--mode',choices=['blind','review'],default='blind');e.add_argument('--experiment');e.add_argument('--strategy',choices=['A','B'],default='B')
 s=sp.add_parser('stage');s.add_argument('bundle',type=Path);s.add_argument('proposals',type=Path)
 a=sp.add_parser('accept');a.add_argument('proposal_id');a.add_argument('--reviewer',required=True);a.add_argument('--reason',required=True)
 args=p.parse_args();core.init()
 if args.action=='export':
  b=build_bundle(args.split,args.mode,args.experiment,args.strategy);out=core.ROOT/'data/argilla';out.mkdir(exist_ok=True)
  f=out/(b['mode']+'-'+b['fingerprint'][:12]+'.json');f.write_text(json.dumps(b,ensure_ascii=False,indent=2),encoding='utf-8');print(str(f))
 elif args.action=='stage':print(json.dumps(stage(json.loads(args.proposals.read_text(encoding='utf-8-sig')),json.loads(args.bundle.read_text(encoding='utf-8-sig')))))
 else:print(json.dumps(adjudicate(args.proposal_id,args.reviewer,args.reason)))
if __name__=='__main__':main()
