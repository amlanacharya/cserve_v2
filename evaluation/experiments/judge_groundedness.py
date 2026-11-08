import json,os,sys,time,re
sys.path.insert(0,'.')
from src.generation.cascade import call_cascade
d=json.load(open(os.environ['TEMP']+'/capdev.json'))
SYS="You are a strict fact-checker. Given SOURCE passages and an ANSWER, decide whether every factual claim in the ANSWER is supported by the SOURCE. Ignore politeness. Reply with JSON only: {\"supported\": true|false, \"unsupported_claims\": [\"...\"]}."
out=[]
for x in d:
    src="\n\n".join(f"[{c['doc_id']}] {c['text']}" for c in x['ctx'])
    try:
        raw,prov=call_cascade(system_prompt=SYS,user_prompt=f"SOURCE:\n{src}\n\nANSWER:\n{x['draft']}",temperature=0.0,task_type="generation")
        m=re.search(r"\{.*\}",raw or '',re.S); j=json.loads(m.group(0)) if m else {}
        out.append({'ticket':x['ticket'],'supported':j.get('supported'),'claims':j.get('unsupported_claims',[])[:3],'prov':prov})
    except Exception as e:
        out.append({'ticket':x['ticket'],'supported':None,'err':str(e)[:80]})
    time.sleep(0.5)
json.dump(out,open(os.environ['TEMP']+'/judge.json','w'))
print('judged',len(out))
