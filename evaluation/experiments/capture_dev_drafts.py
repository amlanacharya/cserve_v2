import json,random,sys,os,time
sys.path.insert(0,'.')
import src.orchestrator as orch_mod
from src.orchestrator import SupportOrchestrator
import src.guardrails as G
cap=[]
import importlib
# capture at the call site used by the graph
for modname,mod in list(sys.modules.items()):
    if modname.startswith('src.') and hasattr(mod,'evaluate_guardrails'):
        orig=getattr(mod,'evaluate_guardrails')
        def wrap(draft_response,citations,retrieved_docs,_o=orig,_cap=cap):
            _cap.append({'draft':draft_response,'citations':citations,'ctx':[{'doc_id':d.doc_id,'text':d.text} for d in retrieved_docs]})
            return _o(draft_response,citations,retrieved_docs)
        setattr(mod,'evaluate_guardrails',wrap)
d=json.load(open('05_Datasets/development_tickets.json'))
random.seed(7)
auto=[t for t in d if t['labels']['expected_route']=='auto_respond' and not t['labels']['must_not_auto_respond']]
sample=random.sample(auto,70)
db=os.environ['TEMP']+'/capdev.db'
o=SupportOrchestrator(db_path=db)
out=[]
for t in sample:
    n=len(cap)
    try: r=o.process_ticket(t,run_id='capdev')
    except Exception as e: print('err',e); continue
    if len(cap)>n: out.append({**cap[-1],'ticket':t['ticket_id'],'disp':str(r.final_disposition) if hasattr(r,'final_disposition') else str(r)[:60]})
    time.sleep(0.3)
json.dump(out,open(os.environ['TEMP']+'/capdev.json','w'))
print('captured',len(out))
