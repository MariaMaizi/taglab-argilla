"""Export a local factual experiment report, without credentials."""
import core,json,sys
from collections import Counter

def report(e):
 rows=e['rows'];lines=['# TagLab 模型实验结果','',f"实验：{e['id']} · 状态：{e['status']}",f"模型：{e.get('config',{}).get('model','离线规则')} · 分组：{e['split']} · 样本：{e['count']}",'','## 输出与资源记录','', '| 策略 | 合规输出 | 输出错误 | 已记录Token | 已记录调用平均耗时 |','|---|---:|---:|---:|---:|']
 for s in ('A','B'):
  ps=[r['predictions'].get(s,{}) for r in rows];ok=sum(bool(p.get('output')) for p in ps);err=sum(bool(p.get('error')) for p in ps);tokens=sum((p.get('usage') or {}).get('total_tokens',0) or 0 for p in ps);lat=[p['latency_ms'] for p in ps if p.get('latency_ms') is not None]
  lines.append(f"| {s} | {ok}/{e['count']} | {err} | {tokens if any(p.get('usage') for p in ps) else '未记录'} | {str(round(sum(lat)/len(lat)/1000,2))+'秒' if lat else '未记录'} |")
 lines+=['','## 人工参考与指标','']
 for s in ('A','B'):
  m=e.get('metrics',{}).get(s,{})
  lines.append(f"- {s}：有效人工参考 {m.get('reference_count',0)} 条；主题micro F1={m.get('f1')}；形式准确率={m.get('format_accuracy')}；全部标签匹配={m.get('exact_match')}。")
 lines+=['','当前有效参考规模不足以推断整体模型质量。校验失败按端到端未命中计；原文存在不等于语义已经核实。Token来自接口返回，不代表现金账单或免费额度。','','## 逐条输出','']
 for r in rows:
  lines+=['### '+r['title'],'','人工参考：'+json.dumps({k:r['reference'].get(k) for k in ('topics','format','needs_review')} if r['reference'] else None,ensure_ascii=False),'']
  for s in ('A','B'):
   p=r['predictions'].get(s,{});o=p.get('output') or p.get('rejected_output')
   lines+=['- '+s+'：'+json.dumps(o,ensure_ascii=False) + ('；错误：'+p['error'] if p.get('error') else '')]
 if e.get('fatal_error'):lines+=['','中断原因：'+e['fatal_error']]
 return '\n'.join(lines)+'\n'
if __name__=='__main__':
 e=core.experiment(sys.argv[1]);p=core.ROOT/'data'/'reports';p.mkdir(exist_ok=True)
 (p/(e['id']+'.md')).write_text(report(e),encoding='utf-8');(p/(e['id']+'.json')).write_text(json.dumps(e,ensure_ascii=False,indent=2),encoding='utf-8');print(str(p/(e['id']+'.md')))
