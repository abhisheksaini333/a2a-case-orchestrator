"""Repeat identical case classes through three actual processes in both modes."""
import argparse,json,os,statistics,time,uuid
from pathlib import Path
from tests.test_processes import Processes

def benchmark(mode,repetitions):
    old=os.environ.get('AGENT_TRANSPORT');os.environ['AGENT_TRANSPORT']=mode
    harness=Processes();Processes.setUpClass()
    rows=[]
    try:
        harness.setUp()
        for repeat in range(repetitions):
            for scenario,description,missing in [('technology','laptop server repair',False),('industrial','steel machine bearings',True),('office','paper and pens',False)]:
                tax='BENCH-'+uuid.uuid4().hex[:12]
                supplier={'name':'Benchmark Supplier','tax_id':tax,'description':description}
                if not missing:supplier['documents']=[{'type':'tax_certificate','tax_id':tax}]
                start=time.perf_counter()
                row=harness.call('/api/cases',{'request_key':uuid.uuid4().hex,'supplier':supplier})
                if missing:row=harness.call('/api/cases/'+row['id']+'/resume',{'documents':[{'type':'tax_certificate','tax_id':tax}]})
                assert row['state']=='review',row
                finished=harness.call('/api/cases/'+row['id']+'/approve',{'digest':row['proposal_digest']},'reviewer')
                assert finished['state']=='completed'
                rows.append({'scenario':scenario,'repeat':repeat+1,'completed':True,'latency_ms':round((time.perf_counter()-start)*1000,2)})
        metrics=harness.call('/api/metrics')
        harness.test_three_process_onboarding_requires_exact_independent_approval()
        return {'mode':mode,'cases':len(rows),'completed':sum(x['completed'] for x in rows),'median_latency_ms':round(statistics.median(x['latency_ms'] for x in rows),2),'max_latency_ms':max(x['latency_ms'] for x in rows),'transport':metrics,'coordinator_kill_restart_and_duplicate_approval':'passed','samples':rows}
    finally:
        harness.tearDown();Processes.tearDownClass()
        if old is None:os.environ.pop('AGENT_TRANSPORT',None)
        else:os.environ['AGENT_TRANSPORT']=old

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repetitions',type=int,default=4);parser.add_argument('--output',required=True);args=parser.parse_args()
    report={'scope':'Local three-process comparison; same checks, database effects and case classes. Includes approval. Direct mode removes discovery and JSON-RPC envelope, retains application task receipts. Body bytes exclude HTTP headers. Startup/build time excluded.', 'results':[benchmark(mode,args.repetitions) for mode in ['a2a','direct']]}
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
