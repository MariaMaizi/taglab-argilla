import unittest,tempfile
from pathlib import Path
import core
from tests_support import seed
from model_adapter import StopExperiment
class FailureAuditTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=core.DB;self.oldroot=core.ROOT;core.ROOT=Path(self.tmp.name);core.DB=core.ROOT/'audit.db';seed(core.ROOT);core.prepare()
 def tearDown(self):core.DB=self.old;core.ROOT=self.oldroot;self.tmp.cleanup()
 def test_rejected_output_keeps_usage(self):
  def bad(row,s):return {'output':{'topics':['business'],'format':'unknown','evidence':{'business':'not-in-input'},'needs_review':False},'latency_ms':123,'usage':{'total_tokens':50}}
  e=core.create_experiment('llm','pilot',1,bad)
  self.assertEqual(e['error_count'],2)
  p=e['rows'][0]['predictions']['A'];self.assertEqual(p['usage']['total_tokens'],50);self.assertIn('rejected_output',p);self.assertNotIn('output',p)
 def test_abort_records_partial_failure(self):
  calls=[]
  def stop(row,s):calls.append(s);raise StopExperiment('quota')
  e=core.create_experiment('llm','pilot',2,stop)
  self.assertEqual(calls,['A']);self.assertEqual(e['status'],'failed');self.assertIn('finished_at',e);self.assertEqual(e['error_count'],1)
if __name__=='__main__':unittest.main()
