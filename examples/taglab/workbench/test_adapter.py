import unittest,json
from unittest.mock import patch
import model_adapter as m
class AdapterTests(unittest.TestCase):
 def test_endpoint_boundary(self):
  self.assertTrue(m.endpoint_ok('https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'))
  for url in ['http://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions','https://dashscope.aliyuncs.com.evil.test/compatible-mode/v1/chat/completions','https://user:secret@dashscope.aliyuncs.com/compatible-mode/v1/chat/completions']:
   self.assertFalse(m.endpoint_ok(url))
 def test_blind_input_and_strategy(self):
  row={'title':'标题','text':'内容','reference':{'secret':'human-answer'}}
  a=m.messages(row,'A');b=m.messages(row,'B')
  self.assertNotIn('human-answer',json.dumps(a));self.assertNotIn('exclude',a[0]['content']);self.assertIn('exclude',b[0]['content']);self.assertEqual(a[1],b[1])
 def test_thinking_parser(self):self.assertEqual(m.parse_output('<think>分析</think>```json\n{"topics":[]}\n```'),{'topics':[]})
 def test_quota_stops_no_retry(self):
  import urllib.error
  op=unittest.mock.Mock();op.open.side_effect=urllib.error.HTTPError('https://x',429,'quota',{},None)
  with patch('urllib.request.build_opener',return_value=op):
   run=m.runner({'endpoint':'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions','key':'test-secret','model':'test-model'})
   with self.assertRaises(m.StopExperiment):run({'title':'test','text':'test'},'A')
  self.assertEqual(op.open.call_count,1)
if __name__=='__main__':unittest.main()
