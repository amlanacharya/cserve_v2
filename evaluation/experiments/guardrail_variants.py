import json,os,re,sys,itertools
sys.path.insert(0,'.')
from src.guardrails.hallucination import SENTENCE_SPLIT_REGEX,WORD_REGEX,STOP_WORDS,DOC_ID_TOKEN
d={x['ticket']:x for x in json.load(open(os.environ['TEMP']+'/capdev.json'))}
j={x['ticket']:x for x in json.load(open(os.environ['TEMP']+'/judge.json')) if x.get('supported') is not None}
def stem(w): return w[:5] if len(w)>=6 else w
def ratios(x,use_stem,all_ctx,min_words):
    docs=[c for c in x['ctx'] if all_ctx or c['doc_id'] in x['citations']]
    ctx=" ".join(c['text'] for c in docs).lower()
    f=stem if use_stem else (lambda w:w)
    cu={f(w) for w in WORD_REGEX.findall(ctx) if w not in STOP_WORDS}
    rs=[]
    for s in [s.strip() for s in SENTENCE_SPLIT_REGEX.split(x['draft']) if s.strip()]:
        w=[t.lower() for t in WORD_REGEX.findall(s)];w=[f(t) for t in w if t not in STOP_WORDS and not DOC_ID_TOKEN.match(t)]
        if len(w)>=min_words: rs.append(sum(t in cu for t in w)/len(w))
    return rs
def passes(x,cfg):
    rs=ratios(x,cfg['stem'],cfg['all'],cfg['minw'])
    if not rs: return True
    return min(rs)>=cfg['tmin'] and sum(rs)/len(rs)>=cfg['tmean']
print('judged',len(j),'supported',sum(v['supported'] is True for v in j.values()))
rows=[]
for stem_,all_,minw,tmin,tmean in itertools.product([False,True],[False,True],[1,4],[0.0,0.15,0.25,0.35,0.5],[0.0,0.4,0.5,0.6]):
    cfg=dict(stem=stem_,all=all_,minw=minw,tmin=tmin,tmean=tmean)
    rel=fv=fp=tp=0
    for t,v in j.items():
        p=passes(d[t],cfg);s=v['supported'] is True
        rel+=p; fp+=(p and not s); fv+=((not p) and s); tp+=(p and s)
    rows.append((fp,-rel,cfg,rel,fv))
rows.sort(key=lambda r:(r[0],r[1]))
print('baseline (orig):',[ (sum(passes(d[t],dict(stem=False,all=False,minw=1,tmin=0.5,tmean=0.0)) for t in j), ) ])
for fp,_,cfg,rel,fv in rows[:12]: print('false-pass',fp,'released',rel,'false-veto',fv,cfg)
