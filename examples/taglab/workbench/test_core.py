import unittest,tempfile,json
from pathlib import Path
import core
from tests_support import seed
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=core.DB;self.oldroot=core.ROOT;core.ROOT=Path(self.tmp.name);core.DB=core.ROOT/'test.db';seed(core.ROOT);core.prepare()
 def tearDown(self):core.DB=self.old;core.ROOT=self.oldroot;self.tmp.cleanup()
 def test_no_reference_no_score(self):
  e=core.create_experiment('rules','pilot',20)
  self.assertEqual(e['status'],'completed');self.assertIsNone(e['metrics']['A']['f1']);self.assertEqual(e['count'],20)
 def test_lock_requires_reference(self):
  with self.assertRaises(ValueError):core.lock_test()
 def test_quote_validation(self):
  with self.assertRaises(ValueError):core.validate_labels({'topics':['business'],'format':'unknown','evidence':{'business':'伪造引用'},'needs_review':False},'真实正文')
 def test_revision_and_snapshot(self):
  r=next(x for x in core.all_records() if len(x['clean']['text'])>=20 and x['split']=='pilot')
  e=core.create_experiment('rules','pilot',20)
  b={'input_text':r['clean']['text'],'reviewer':'test-only','topics':[],'format':'unknown','evidence':{},'needs_review':True,'note':'测试争议','revision':0}
  core.save_annotation(r['record_id'],b)
  with self.assertRaises(ValueError):core.save_annotation(r['record_id'],b)
  self.assertEqual(core.experiment(e['id'])['metrics']['A']['reference_count'],0)
 def test_cleaning_audited(self):
  r=core.clean_text('讨论企业经营的变化。\n时间轴\n01:00 广告')
  self.assertIn('企业',r['text']);self.assertNotIn('广告',r['text']);self.assertTrue(r['removed'])
if __name__=='__main__':unittest.main()
