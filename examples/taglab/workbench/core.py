from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
from collections import Counter
import json,sqlite3,os,re,hashlib,random,uuid

ROOT=Path(__file__).resolve().parent
DB=Path(os.environ.get('TAGLAB_DB',str(ROOT/'data/taglab.sqlite3')))
TAX=json.loads((ROOT/'taxonomy.json').read_text(encoding='utf-8'))
PROMPTS=json.loads((ROOT/'prompts.json').read_text(encoding='utf-8'))
TOPICS={x['id']:x for x in TAX['topics']};FORMATS={x['id']:x for x in TAX['formats']}
CLEAN_VERSION='intro-v1'

def now():return datetime.now(timezone.utc).isoformat()
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
@contextmanager
def db():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB,timeout=20);c.row_factory=sqlite3.Row
    try:yield c;c.commit()
    except Exception:c.rollback();raise
    finally:c.close()

def init():
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,body TEXT NOT NULL,split TEXT NOT NULL,group_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS annotations(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS history(at TEXT,record_id TEXT,action TEXT,body TEXT);
CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY,created_at TEXT,status TEXT,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
''')

def clean_text(raw):
    kept=[];removed=[];tail=False
    boundary=re.compile(r'^(?:[【\[|｜]\s*(?:主播|嘉宾|时间轴|你将听到|往期相关|延伸资料|后期制作|声音设计|收听方式|认识我们|制作团队|本期音乐|参考资料|相关链接)|(?:时间轴|/Staff/|Support\s+)|\d{1,2}[:：]\d{2}\s)')
    for line in raw.splitlines():
        line=line.strip()
        if not line:continue
        if boundary.search(line):tail=True
        if tail:removed.append({'rule':'section_tail','text':line});continue
        if re.search(r'^(?:[*＊]?感谢.*(?:支持|赞助)|商务合作|联系我们|微信公众号|微信号|新浪微博|广告合作)',line):
            removed.append({'rule':'promotion_or_contact','text':line});continue
        if re.search(r'https?://|\b[\w.+-]+@[\w.-]+\.[a-z]{2,}',line,re.I):
            removed.append({'rule':'external_link_or_contact','text':line});continue
        kept.append(line)
    full='\n'.join(kept).strip()
    text=full[:1800]
    flags=[]
    if len(full)>1800:flags.append('清洗后仍截断')
    if len(text)<80:flags.append('简介较短，需人工确认')
    if not text:flags.append('无可用正文')
    if removed:flags.append('已移除章节或推广，需核对')
    return {'text':text,'pre_truncation_chars':len(full),'removed':removed,'flags':flags,'version':CLEAN_VERSION}

def prepare():
    init();raws={};manifests=[]
    for p in sorted((ROOT/'data').glob('*/manifest.json')):
        m=json.loads(p.read_text(encoding='utf-8'));manifests.append(m)
        f=p.parent/'podcasts.jsonl'
        if f.exists():
            for line in f.read_text(encoding='utf-8').splitlines():
                if line.strip():r=json.loads(line);raws[r['record_id']]=r
    groups={};records=[]
    for r in raws.values():
        title=re.sub(r'^(?:E\d+|Vol\.\d+|商业小样\d+)\s*[｜|：:]*\s*','',r['episode_title'],flags=re.I)
        normalized=re.sub(r'\W+','',title).lower()
        group=hashlib.sha256(normalized.encode()).hexdigest()[:16]
        groups.setdefault(r['source_key'],[]).append(group)
        records.append({**r,'clean':clean_text(r['description_text']),'group_id':group})
    assigned={};rng=random.Random(20261108)
    for source,gs in sorted(groups.items()):
        gs=sorted(set(gs));rng.shuffle(gs)
        for n,g in enumerate(gs):assigned[g]='pilot' if n<10 else ('dev' if (n-10)%2==0 else 'test')
    with db() as c:
        if c.execute('select count(*) from experiments').fetchone()[0] or c.execute('select count(*) from annotations').fetchone()[0]:
            raise ValueError('已有实验或标注；请创建新数据版本，不覆盖当前输入。')
        for r in records:
            c.execute('insert or replace into records values(?,?,?,?)',(r['record_id'],json.dumps(r,ensure_ascii=False),assigned[r['group_id']],r['group_id']))
        c.execute('insert or replace into meta values(?,?)',('sources',json.dumps(manifests,ensure_ascii=False)))
        c.execute('insert or replace into meta values(?,?)',('dataset_version',digest([{'id':r['record_id'],'text':r['clean']['text']} for r in records])[:16]))
    return stats()

def locked():
    with db() as c:r=c.execute('select value from meta where key=?',('test_locked',)).fetchone()
    return bool(r and r[0]=='true')

def all_records():
    with db() as c:
        rr=c.execute('select r.*,a.body annotation,a.revision from records r left join annotations a on r.id=a.id order by r.id').fetchall()
    result=[]
    for x in rr:
        r=json.loads(x['body']);r['split']=x['split'];r['annotation']=json.loads(x['annotation']) if x['annotation'] else None;r['revision']=x['revision'] or 0;result.append(r)
    return result

def record(i):
    r=next((r for r in all_records() if r['record_id']==i),None)
    if not r:raise KeyError('内容不存在')
    return r

def input_text(r):return r['annotation'].get('input_text',r['clean']['text']) if r.get('annotation') else r['clean']['text']
def validate_labels(o,text,reference=False):
    if not isinstance(o,dict):raise ValueError('输出必须为对象')
    topics=o.get('topics');fmt=o.get('format');ev=o.get('evidence',{})
    if not isinstance(topics,list) or len(topics)>3 or len(set(topics))!=len(topics) or any(t not in TOPICS for t in topics):raise ValueError('主题须为0–3个有效标签')
    if fmt not in FORMATS:raise ValueError('请选择节目形式')
    if not isinstance(ev,dict):raise ValueError('依据格式无效')
    for t in topics:
        q=ev.get(t,'')
        if not isinstance(q,str) or len(q)<2 or len(q)>500 or q not in text:raise ValueError('每个主题须附2–500字的输入原文依据')
    if fmt!='unknown':
        q=ev.get('format','')
        if not isinstance(q,str) or len(q)<2 or len(q)>500 or q not in text:raise ValueError('节目形式须附输入中的原文依据')
    if not topics and not str(o.get('note',o.get('reason',''))).strip():raise ValueError('无适用主题时请说明原因')
    if not isinstance(o.get('needs_review'),bool):raise ValueError('复核状态必须为布尔值')
    return True

def save_annotation(i,body):
    r=record(i)
    if locked() and r['split']=='test':raise ValueError('留出集已锁定，不能修改参考或输入。')
    text=body.get('input_text','').strip();reviewer=body.get('reviewer','').strip()
    if not reviewer or len(reviewer)>60:raise ValueError('请填写审核者代号，最多60字')
    if not 20<=len(text)<=5000:raise ValueError('请核对输入文本，长度须为20–5000字')
    o={k:body.get(k) for k in ('topics','format','evidence','needs_review','note')}
    o.update(input_text=text,reviewer=reviewer,at=now(),taxonomy_version=TAX['version'],taxonomy_hash=digest(TAX),input_hash=digest({'title':r['episode_title'],'text':text}),status='reviewed')
    validate_labels(o,r['episode_title']+'\n'+text,True)
    with db() as c:
        row=c.execute('select revision from annotations where id=?',(i,)).fetchone();revision=row[0] if row else 0
        if revision!=body.get('revision',0):raise ValueError('内容已被修改，请刷新后再保存。')
        c.execute('insert or replace into annotations values(?,?,?)',(i,revision+1,json.dumps(o,ensure_ascii=False)))
        c.execute('insert into history values(?,?,?,?)',(now(),i,'reference_saved',json.dumps(o,ensure_ascii=False)))
    return record(i)

def stats():
    rr=all_records();counts=Counter(r['split'] for r in rr)
    with db() as c:
        ex=c.execute('select id,created_at,status,body from experiments order by created_at desc').fetchall()
        source=c.execute('select value from meta where key=?',('sources',)).fetchone()
    return {'records':len(rr),'shows':dict(Counter(r['show_title'] for r in rr)),'splits':dict(counts),
        'reviewed':sum(bool(r['annotation']) for r in rr),'reference_needs_review':sum(bool(r['annotation'] and r['annotation']['needs_review']) for r in rr),
        'clean_removed':sum(bool(r['clean']['removed']) for r in rr),'clean_truncated':sum('清洗后仍截断' in r['clean']['flags'] for r in rr),
        'experiments':len(ex),'test_locked':locked(),'sources':json.loads(source[0]) if source else [],
        'experiment_list':[{'id':x['id'],'created_at':x['created_at'],'status':x['status'],**{k:json.loads(x['body']).get(k) for k in ('name','kind','split','count','metrics','differences','error_count')}} for x in ex]}

def lock_test():
    rr=[r for r in all_records() if r['split']=='test']
    if not rr or any(not r['annotation'] or r['annotation']['needs_review'] for r in rr):raise ValueError('请先完成全部留出集人工参考，并解决待复核项。')
    with db() as c:
        c.execute('insert or replace into meta values(?,?)',('test_locked','true'))
        c.execute('insert or replace into meta values(?,?)',('locked_taxonomy',digest(TAX)))
        c.execute('insert or replace into meta values(?,?)',('locked_prompts',digest(PROMPTS)))
        c.execute('insert into history values(?,?,?,?)',(now(),'','test_locked',json.dumps({'taxonomy_hash':digest(TAX),'prompts_hash':digest(PROMPTS),'references':digest([r['annotation'] for r in rr])})))
    return {'test_locked':True}

KEYWORDS={
 'technology':['AI','人工智能','大模型','芯片','机器人','科技','半导体','制药','科学','算力','软件','技术'],
 'business':['公司','企业','市场','商业','投资','品牌','收入','消费','创业','开店','经济','融资','利润'],
 'career':['职场','求职','离职','转行','职业','招聘','就业','员工','工作环境','职业发展'],
 'culture':['博物馆','展览','电影','艺术','文学','历史','文化','小说','读书','作家'],
 'life':['旅行','徒步','饮食','生活习惯','咖啡','运动','旅游','餐饮','食物'],
 'society':['社会','公共','政策','城市','群体','制度','公益','平等','劳动']}

def rule_predict(title,text,strategy):
    combined=title+'\n'+text;sentences=[s.strip() for s in re.split(r'[。！？\n]',combined) if s.strip()]
    found=[];ev={}
    for k,words in KEYWORDS.items():
        hits=[s for s in sentences if any(w.lower() in s.lower() for w in words)]
        if not hits:continue
        # B is a conservative deterministic heuristic, not an LLM or semantic truth.
        if strategy=='B' and not any(w.lower() in title.lower() for w in words) and len(hits)<2:continue
        score=sum(sum(w.lower() in s.lower() for w in words) for s in hits)+(3 if any(w.lower() in title.lower() for w in words) else 0)
        found.append((score,k));ev[k]=hits[0][:500]
    topics=[k for _,k in sorted(found,reverse=True)[:3]]
    fmt='unknown';fe=''
    for marker,f in [('邀请','interview'),('采访','interview'),('嘉宾','interview'),('独白','monologue'),('独自讲述','monologue'),('两位主播','discussion'),('三位主播','discussion')]:
        s=next((s for s in sentences if marker in s),None)
        if s:fmt=f;fe=s[:500];break
    return {'topics':topics,'format':fmt,'evidence':{**{k:ev[k] for k in topics},'format':fe},'needs_review':True,
        'reason':'关键词规则建议，仅用于检查管线；不能作为人工参考或LLM结果。'}

def score(rows,strategy):
    usable=[x for x in rows if x['reference'] and not x['reference']['needs_review']]
    if not usable:return {'reference_count':0,'precision':None,'recall':None,'f1':None,'format_accuracy':None,'exact_match':None,'per_label':[],'note':'无已裁决人工参考，不计算质量分数'}
    tp=fp=fn=fmt=exact=0;per={k:[0,0,0] for k in TOPICS}
    for x in usable:
        pred=x['predictions'].get(strategy,{}).get('output')
        p=set(pred['topics']) if pred else set();g=set(x['reference']['topics'])
        tp+=len(p&g);fp+=len(p-g);fn+=len(g-p)
        fmt+=int(bool(pred) and pred['format']==x['reference']['format']);exact+=int(bool(pred) and p==g and pred['format']==x['reference']['format'])
        for k in TOPICS:per[k][0]+=k in p&g;per[k][1]+=k in p-g;per[k][2]+=k in g-p
    div=lambda a,b:a/b if b else None
    return {'reference_count':len(usable),'precision':div(tp,tp+fp),'recall':div(tp,tp+fn),'f1':div(2*tp,2*tp+fp+fn),
        'format_accuracy':fmt/len(usable),'exact_match':exact/len(usable),'tp':tp,'fp':fp,'fn':fn,
        'per_label':[{'id':k,'name':TOPICS[k]['name'],'tp':v[0],'fp':v[1],'fn':v[2],'support':v[0]+v[2]} for k,v in per.items()],
        'note':'仅对运行时已裁决参考评分，模型错误/无输出按未命中计；单人参考仍可能有偏差。'}

def create_experiment(kind,split,limit,model_run=None,config=None):
    if kind not in ('rules','llm') or split not in ('pilot','dev','test'):raise ValueError('实验类型或数据集无效')
    if split=='test':
        if not locked():raise ValueError('留出测试集尚未锁定，先在试标集或开发集实验。')
        with db() as c:old=c.execute('select value from meta where key=?',('locked_taxonomy',)).fetchone()
        if old and old[0]!=digest(TAX):raise ValueError('规范与锁定版本不同，请建立新的数据版本。')
        with db() as c:old_prompt=c.execute('select value from meta where key=?',('locked_prompts',)).fetchone()
        if not old_prompt or old_prompt[0]!=digest(PROMPTS):raise ValueError('提示词与锁定版本不同，请建立新版本。')
    if kind=='llm' and locked() and split!='test':raise ValueError('当前版本已锁定；如需继续调整，请创建新版本，避免测试集泄漏。')
    if not 1<=limit<=(20 if kind=='llm' else 100):raise ValueError('本次最多20条模型实验或100条规则实验')
    rr=[r for r in all_records() if r['split']==split][:limit]
    if not rr:raise ValueError('当前数据集没有记录')
    i=uuid.uuid4().hex[:12];snapshot=[]
    for r in rr:
        snapshot.append({'record_id':r['record_id'],'title':r['episode_title'],'text':input_text(r),'reference':r['annotation'],
            'input_hash':digest({'title':r['episode_title'],'text':input_text(r)}),'predictions':{}})
    body={'name':('规则基线' if kind=='rules' else '模型策略')+' A/B 对比','kind':kind,'split':split,'count':len(snapshot),
        'rows':snapshot,'taxonomy_snapshot':TAX,'prompts_snapshot':PROMPTS,'config':config or {},'started_at':now(),
        'warning':'规则结果不是LLM，参考标签来自操作者；无人工参考不计算准确率。','metrics':{},'differences':0,'error_count':0}
    with db() as c:c.execute('insert into experiments values(?,?,?,?)',(i,now(),'running',json.dumps(body,ensure_ascii=False)))
    try:
        for row in snapshot:
            for strategy in ('A','B'):
                pred=None
                try:
                    if kind=='rules':pred={'output':rule_predict(row['title'],row['text'],strategy),'latency_ms':0,'usage':{}}
                    else:pred=model_run(row,strategy)
                    validate_labels(pred['output'],row['title']+'\n'+row['text'])
                    row['predictions'][strategy]=pred
                except Exception as e:
                    row['predictions'][strategy]={**({'rejected_output':pred.get('output'),'latency_ms':pred.get('latency_ms'),'usage':pred.get('usage',{})} if pred else {}),'error':str(e)[:400]};body['error_count']+=1
                    if type(e).__name__=='StopExperiment':raise
            a=row['predictions'].get('A',{}).get('output');b=row['predictions'].get('B',{}).get('output')
            body['differences']+=int(bool(a and b) and (set(a['topics'])!=set(b['topics']) or a['format']!=b['format']))
            with db() as c:c.execute('update experiments set body=? where id=?',(json.dumps(body,ensure_ascii=False),i))
        body['metrics']={s:score(snapshot,s) for s in ('A','B')};body['finished_at']=now()
        status='completed_with_errors' if body['error_count'] else 'completed'
    except Exception as e:
        body['fatal_error']=str(e)[:400];body['finished_at']=now();status='failed'
        body['metrics']={s:score(snapshot,s) for s in ('A','B')}
    with db() as c:c.execute('update experiments set status=?,body=? where id=?',(status,json.dumps(body,ensure_ascii=False),i))
    return experiment(i)

def experiment(i):
    with db() as c:r=c.execute('select * from experiments where id=?',(i,)).fetchone()
    if not r:raise KeyError('实验不存在')
    return {'id':r['id'],'created_at':r['created_at'],'status':r['status'],**json.loads(r['body'])}
