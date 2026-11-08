"""Collect a small, private pilot pool from publisher-provided RSS links.

No audio, transcripts, comments, login, model calls, or automatic retries.
"""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import csv, hashlib, json, re, time
import urllib.request, urllib.parse, urllib.robotparser, urllib.error
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
UA='TagLabResearch/0.1'
SOURCES=[
    ('etw','https://etw.fm/subscribe'),
    ('sv101','https://sv101.fireside.fm/subscribe'),
    ('thatisbiz','https://thatisbiz.fireside.fm/subscribe'),
]
MAX_PER_SOURCE=40
MAX_BYTES=16_000_000

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml,application/xml,text/html;q=0.8'})
    with urllib.request.urlopen(req,timeout=25) as r:
        body=r.read(MAX_BYTES+1)
        if len(body)>MAX_BYTES:raise ValueError('Response exceeds collection limit')
        return body,r.geturl(),dict(r.headers)

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag in ('a','link') and d.get('href'):
            if 'rss' in d.get('type','') or re.search(r'(?:/rss|/feed)(?:[/?.]|$)',d['href']):self.links.append(d['href'])

class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.ignore=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.ignore+=1
        if tag in ('p','br','div','li','h1','h2','h3'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.ignore=max(0,self.ignore-1)
        if tag in ('p','div','li'):self.parts.append('\n')
    def handle_data(self,data):
        if not self.ignore:self.parts.append(data)

def plain(s):
    p=Text();p.feed(s)
    return '\n'.join(x for line in ''.join(p.parts).splitlines() if (x:=re.sub(r'\s+',' ',line).strip()))

def allowed(url,cache):
    u=urllib.parse.urlsplit(url);base=f'{u.scheme}://{u.netloc}'
    if base not in cache:
        robot_url=base+'/robots.txt'
        try:
            raw,_,_=get(robot_url);rp=urllib.robotparser.RobotFileParser();rp.parse(raw.decode('utf-8','replace').splitlines())
            cache[base]=(rp,'fetched')
        except urllib.error.HTTPError as e:
            if e.code==404:cache[base]=(None,'404')
            else:raise RuntimeError(f'robots unavailable HTTP {e.code}; skip source')
    rp,status=cache[base]
    if rp is not None and not rp.can_fetch(UA,url):raise RuntimeError('robots disallows path')
    return status

def main():
    now=datetime.now(timezone.utc);stamp=now.strftime('%Y%m%dT%H%M%SZ')
    out=ROOT/'data'/stamp;rawdir=out/'raw';rawdir.mkdir(parents=True,exist_ok=True)
    rows=[];logs=[];cache={};seen=set()
    for key,page in SOURCES:
        log={'source_key':key,'discovery_url':page,'collected_at_utc':now.isoformat()}
        try:
            log['discovery_robots']=allowed(page,cache)
            html,page_final,_=get(page);links=Links();links.feed(html.decode('utf-8','replace'))
            if not links.links:raise ValueError('No publisher RSS link found')
            feed_url=urllib.parse.urljoin(page_final,links.links[0]);log['feed_url']=feed_url
            log['feed_robots']=allowed(feed_url,cache)
            time.sleep(1)
            body,final,headers=get(feed_url);log['feed_final_url']=final
            log['feed_sha256']=hashlib.sha256(body).hexdigest()
            (rawdir/(key+'.xml')).write_bytes(body)
            doc=ET.fromstring(body);channel=doc.find('channel')
            if channel is None:raise ValueError('RSS channel missing')
            name=channel.findtext('title') or key;items=channel.findall('item');count=0
            log['available_items']=len(items)
            for item in items:
                if count>=MAX_PER_SOURCE:break
                title=plain(item.findtext('title') or '')
                link=(item.findtext('link') or '').strip()
                desc=item.findtext('description') or item.findtext('{http://www.itunes.com/dtds/podcast-1.0.dtd}summary') or ''
                text=plain(desc)
                guid=(item.findtext('guid') or link or title).strip()
                dedup=hashlib.sha256((name+'\n'+guid).encode()).hexdigest()
                if dedup in seen or not title or not text:continue
                pub=item.findtext('pubDate') or ''
                try:
                    dt=parsedate_to_datetime(pub)
                    if dt>now:continue
                except (ValueError,TypeError,OverflowError):pass
                # Keep all plain text privately; model input uses an explicitly limited excerpt.
                excerpt=text[:1200]
                rows.append({'record_id':dedup[:16],'source_key':key,'show_title':name,
                    'episode_title':title,'description_text':text,'model_excerpt':excerpt,
                    'excerpt_truncated':len(text)>len(excerpt),'episode_url':link,
                    'feed_url':final,'published_at_raw':pub,'collected_at_utc':now.isoformat(),
                    'annotation_status':'unlabeled','human_topics':None,'human_format':None,
                    'human_evidence':None,'split':'unassigned',
                    'quality_flags':['needs_editorial_cleanup'] if re.search(r'商务|公众号|广告|时间轴|赞助',text) else []})
                seen.add(dedup);count+=1
            log.update(status='success',show_title=name,selected=count)
        except Exception as e:log.update(status='failed',error=f'{type(e).__name__}: {e}')
        logs.append(log);print(json.dumps({k:v for k,v in log.items() if k not in ('feed_sha256',)},ensure_ascii=True),flush=True)
        time.sleep(1)
    (out/'podcasts.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    fields=list(rows[0]) if rows else ['record_id']
    with (out/'annotation-workbook.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in rows:
            # Escape spreadsheet formulas from untrusted publisher text.
            safe={k:("'"+str(v) if str(v).startswith(('=','+','-','@','\t','\r')) else v) for k,v in r.items()}
            writer.writerow(safe)
    manifest={'collected_at_utc':now.isoformat(),'record_count':len(rows),'sources':logs,
        'labels':'Not annotated; no model-generated labels or evaluation scores',
        'scope':'Local pilot only: publisher RSS titles/descriptions; no audio/transcripts/comments',
        'sampling':'Up to 40 latest eligible nonempty episodes per selected feed; convenience sample, not representative',
        'model_input':'episode_title + model_excerpt only; do not use show/source identity or publisher categories',
        'split':'Unassigned until duplicate/series grouping and pilot taxonomy review',
        'publication':'Publisher text is not covered by project code license; raw data remains private'}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output_dir':str(out),'records':len(rows),'unique_ids':len(seen)}))

if __name__=='__main__':main()
