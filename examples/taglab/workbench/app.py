from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
import json, os, threading, uuid
import core, model_adapter
CONFIG={};JOBS={};MUTEX=threading.Lock()
def experiment_job(i,kind,split,limit,config):
 try:
  safe_config={k:v for k,v in config.items() if k!='key'}
  safe_config.update(contract_version=model_adapter.CONTRACT_VERSION,output_contract=model_adapter.CONTRACT,temperature=0.2,max_tokens=1200,enable_thinking=False,response_format='json_object')
  result=core.create_experiment(kind,split,limit,model_adapter.runner(config) if kind=='llm' else None,safe_config)
  JOBS[i]={'status':'done','experiment_id':result['id']}
 except Exception as e:JOBS[i]={'status':'failed','error':str(e)[:300]}
 finally:MUTEX.release()
ROOT=Path(__file__).parent
class Handler(BaseHTTPRequestHandler):
 def reply(self,value,status=200,ctype='application/json; charset=utf-8'):
  data=value.encode('utf-8') if isinstance(value,str) else json.dumps(value,ensure_ascii=False).encode('utf-8')
  self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
 def safe(self):
  host=self.headers.get('Host','');origin=self.headers.get('Origin')
  return host in ('127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port)) and (not origin or origin in ('http://'+host,))
 def do_GET(self):
  if not self.safe():return self.reply({'error':'不允许的来源'},403)
  p=urlparse(self.path).path
  try:
   if p=='/':return self.reply((ROOT/'index.html').read_text(encoding='utf-8'),ctype='text/html; charset=utf-8')
   if p=='/api/state':return self.reply({'stats':core.stats(),'records':core.all_records(),'taxonomy':core.TAX})
   if p=='/api/config':return self.reply({'configured':bool(CONFIG),'model':CONFIG.get('model',''),'endpoint':CONFIG.get('endpoint','https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions')})
   if p.startswith('/api/job/'):return self.reply(JOBS.get(p.rsplit('/',1)[-1],{'status':'missing'}))
   if p.startswith('/api/experiment/'):return self.reply(core.experiment(p.rsplit('/',1)[-1]))
   self.reply({'error':'不存在'},404)
  except (KeyError,ValueError) as e:self.reply({'error':str(e)},400)
 def do_POST(self):
  if not self.safe():return self.reply({'error':'不允许的来源'},403)
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n>100000:raise ValueError('请求过大')
   b=json.loads(self.rfile.read(n));p=urlparse(self.path).path
   if p=='/api/config':
    if not model_adapter.endpoint_ok(b.get('endpoint','')):raise ValueError('接口地址须为百炼北京官方HTTPS接口')
    if not isinstance(b.get('key'),str) or not 10<=len(b['key'])<=500:raise ValueError('请填写有效密钥')
    if not isinstance(b.get('model'),str) or not 1<=len(b['model'])<=100:raise ValueError('请填写模型ID')
    CONFIG.clear();CONFIG.update({k:b[k].strip() for k in ('key','model','endpoint')});return self.reply({'configured':True})
   if p=='/api/model-experiment':
    if not CONFIG:raise ValueError('模型尚未配置')
    limit=b.get('limit',2)
    if type(limit) is not int or not 1<=limit<=20:raise ValueError('每次1–20条')
    if not MUTEX.acquire(blocking=False):raise ValueError('已有模型实验运行中')
    i=uuid.uuid4().hex[:12];JOBS[i]={'status':'running'}
    threading.Thread(target=experiment_job,args=(i,'llm',b.get('split','pilot'),limit,dict(CONFIG)),daemon=True).start();return self.reply({'job_id':i})
   if p=='/api/annotation':return self.reply(core.save_annotation(b['id'],b))
   if p=='/api/experiment':return self.reply(core.create_experiment('rules',b.get('split','pilot'),100))
   if p=='/api/lock':return self.reply(core.lock_test())
   self.reply({'error':'不存在'},404)
  except (ValueError,KeyError,TypeError) as e:self.reply({'error':str(e)},400)
 def log_message(self,*args):pass
if __name__=='__main__':
 core.init()
 if not core.all_records():core.prepare()
 port=int(os.environ.get('TAGLAB_PORT','8877'))
 print('TagLab http://127.0.0.1:'+str(port),flush=True)
 ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
