"""Measure actual local generation separately from deterministic intake rules."""
import argparse,json,time,statistics
from pathlib import Path
from supplier_case.model import extract,extract_rules
from supplier_case.domain import DomainError

def evaluate(corpus, mode, endpoint=None,no_think=False):
    rows=[]
    for item in corpus:
        start=time.perf_counter()
        try:
            result=extract_rules(item['text']) if mode=='rules' else extract(item['text'],endpoint,no_think=no_think)
            identity={k:result['supplier'][k] for k in ['name','tax_id']}
            rows.append({'id':item['id'],'accepted':True,'correct':identity==item['expected'],'identity':identity,'skills':result['skills']})
        except DomainError as exc:
            rows.append({'id':item['id'],'accepted':False,'correct':item['expected'] is None and exc.code in {'invalid_identity','unsafe_route'},'error':exc.code})
        rows[-1]['latency_ms']=round((time.perf_counter()-start)*1000,2)
    return {'no_think':no_think,'mode':mode,'cases':len(rows),'correct':sum(x['correct'] for x in rows),'accepted':sum(x['accepted'] for x in rows),'median_latency_ms':round(statistics.median(x['latency_ms'] for x in rows),2),'results':rows}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--endpoint',action='append',default=[]);parser.add_argument('--no-think',action='store_true');parser.add_argument('--output',required=True);args=parser.parse_args()
    corpus=json.loads((Path(__file__).resolve().parents[1]/'evaluation/intake.json').read_text())
    results=[evaluate(corpus,'rules')]
    for index,endpoint in enumerate(args.endpoint):results.append(evaluate(corpus,'local-model-'+str(index+1),endpoint,args.no_think))
    output={'scope':'Six frozen synthetic intake cases; quality sample, not a general benchmark. No supplier writes.', 'results':results}
    Path(args.output).write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
