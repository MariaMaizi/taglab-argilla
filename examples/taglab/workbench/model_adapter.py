"""Alibaba compatible adapter. Credentials live only in server memory."""
import json,re,time,urllib.request,urllib.error
from urllib.parse import urlparse
import core
CONTRACT_VERSION='exact-evidence-v1'
CONTRACT='''共同输出协议（两组一致）：topics中的值必须是标签ID；evidence的键必须与各主题ID完全一致。每个被选主题必须提供输入标题或简介中逐字连续出现的2至500字原文，不能改写、拼接或省略。format为interview/discussion/monologue时，evidence.format也必须是输入中逐字连续出现的2至500字原文；找不到直接证明节目形式的原句，format必须为unknown，evidence.format填空字符串。即使选择unknown也可以确定主题。不要把不确定的节目形式猜成独白。needs_review必须是JSON布尔值。仅返回一个JSON对象。'''
class StopExperiment(Exception):pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None

def endpoint_ok(url):
 p=urlparse(url)
 return p.scheme=='https' and not p.username and not p.password and not p.query and not p.fragment and p.path=='/compatible-mode/v1/chat/completions' and (p.hostname=='dashscope.aliyuncs.com' or bool(re.fullmatch(r'[a-zA-Z0-9-]+\.cn-beijing\.maas\.aliyuncs\.com',p.hostname or ''))) and p.port in (None,443)

def messages(row,strategy):
 tax=core.TAX if strategy=='B' else {k:[{'id':x['id'],'name':x['name']} for x in core.TAX[k]] for k in ('topics','formats')}
 return [{'role':'system','content':core.PROMPTS[strategy]['system']+'\n'+CONTRACT+'\n标签规范：'+json.dumps(tax,ensure_ascii=False)}, {'role':'user','content':json.dumps({'title':row['title'],'description':row['text']},ensure_ascii=False)}]

def parse_output(text):
 text=re.sub(r'<think>[\s\S]*?</think>','',text).strip()
 if text.startswith('```'):text=re.sub(r'^```(?:json)?\s*|\s*```$','',text).strip()
 return json.loads(text)

def runner(config):
 if not endpoint_ok(config['endpoint']):raise ValueError('仅支持百炼北京官方HTTPS接口')
 if not config.get('key') or not config.get('model'):raise ValueError('请配置API Key与模型ID')
 opener=urllib.request.build_opener(NoRedirect)
 def run(row,strategy):
  payload={'model':config['model'],'messages':messages(row,strategy),'temperature':0.2,'max_tokens':1200,'enable_thinking':False,'stream':False,'response_format':{'type':'json_object'}}
  req=urllib.request.Request(config['endpoint'],data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+config['key']})
  started=time.monotonic()
  try:
   with opener.open(req,timeout=60) as resp:data=json.loads(resp.read(2000000))
  except urllib.error.HTTPError as e:
   if e.code in (401,403,429):raise StopExperiment('供应商拒绝请求（HTTP '+str(e.code)+'），已停止后续调用；请检查权限、额度或限流。')
   raise StopExperiment('模型接口HTTP '+str(e.code)+'，已停止调用；未自动重试。')
  except (urllib.error.URLError,TimeoutError):raise StopExperiment('模型连接失败或超时，已停止后续调用；未自动重试。')
  usage=data.get('usage',{})
  return {'output':parse_output(data['choices'][0]['message']['content']),'latency_ms':round((time.monotonic()-started)*1000),'usage':{k:usage.get(k) for k in ('prompt_tokens','completion_tokens','total_tokens')}}
 return run
