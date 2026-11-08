"""Synthetic public test fixtures; never use a private corpus for unit tests."""
import json
from pathlib import Path

def seed(root):
 p=Path(root)/'data/fixture';p.mkdir(parents=True,exist_ok=True)
 rows=[]
 for source in ('fixture-a','fixture-b'):
  for n in range(12):
   rows.append({'record_id':source+'-'+str(n),'source_key':source,'show_title':source,
    'episode_title':f'{source} 企业经营观察 {n}','description_text':'这段简介讨论企业经营与市场竞争，材料不足以判断节目形式。',
    'episode_url':'https://example.org/fixture','published_at_raw':'fixture','collected_at_utc':'fixture'})
 (p/'manifest.json').write_text(json.dumps({'fixture':True}),encoding='utf-8')
 (p/'podcasts.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows),encoding='utf-8')
