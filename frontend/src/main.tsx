import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

type Case = {id:string; creator:string; state:string; input:{name:string;tax_id:string;description:string}; proposal?:Record<string,string>; proposal_digest?:string; created_at:string};
type CaseEvent = {id:number;actor:string;kind:string;detail:unknown;created_at:string};
const labels:Record<string,string>={'input-required':'Tax certificate needed',review:'Ready for independent review',completed:'Supplier onboarded',failed:'Checks need attention',working:'Checking evidence',submitted:'Queued for checks',canceled:'Case canceled',approved:'Creating supplier record'};
function App(){
 const [key,setKey]=useState('');
 const [draftKey,setDraftKey]=useState('');
 const [cases,setCases]=useState<Case[]>([]);
 const [selected,setSelected]=useState<Case|null>(null);
 const [events,setEvents]=useState<CaseEvent[]>([]);
 const [creating,setCreating]=useState(false);
 const [form,setForm]=useState({name:'',tax_id:'',description:''});
 const [certificate,setCertificate]=useState('');
 const [error,setError]=useState('');
 const [busy,setBusy]=useState(false);
 async function api(path:string,data?:unknown,token=key){
  const response=await fetch('/api'+path,{method:data?'POST':'GET',headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'},...(data?{body:JSON.stringify(data)}:{})});
  const result=await response.json();
  if(!response.ok)throw new Error(result.message||result.error||'Request failed');
  return result;
 }
 async function open(id:string){const result=await api('/cases/'+id);setSelected(result.case);setEvents(result.events);setCreating(false)}
 async function refresh(){setCases((await api('/cases')).cases)}
 async function operation(action:()=>Promise<void>){setBusy(true);setError('');try{await action()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function login(e:React.FormEvent){e.preventDefault();await operation(async()=>{const result=await api('/cases',undefined,draftKey);setCases(result.cases);setKey(draftKey);setDraftKey('')})}
 async function action(name:string,data:unknown={}){if(!selected)return;await operation(async()=>{await api('/cases/'+selected.id+'/'+name,data);await refresh();await open(selected.id);setCertificate('')})}
 async function create(e:React.FormEvent){e.preventDefault();await operation(async()=>{const result=await api('/cases',{request_key:crypto.randomUUID(),supplier:form});await refresh();await open(result.id);setForm({name:'',tax_id:'',description:''})})}
 if(!key)return <main className="entry"><div className="mark">F<span>·</span></div><p className="eyebrow">FOUNDRY / SUPPLIER OPERATIONS</p><h1>Good partnerships<br/>begin with evidence.</h1><p className="lede">One shared case. Independent agents.<br/>A decision that stays yours.</p><form onSubmit={login}><label>Access key<input aria-label="Access key" type="password" value={draftKey} onChange={e=>setDraftKey(e.target.value)} autoComplete="off" required/></label><button disabled={busy}>{busy?'Opening…':'Open supplier desk'}</button>{error&&<p role="alert">{error}</p>}</form><small>Your key stays in this tab. Closing or reloading signs you out.</small></main>;
 return <div className="layout">
  <aside><a className="brand" href="/">F<span>·</span> <strong>FOUNDRY</strong></a><p className="eyebrow">OPERATIONS DESK</p><div className="nav-active">◈ &nbsp; Supplier cases <b>{cases.length}</b></div><div className="aside-note">Evidence first.<br/>Approval stays human.</div><button className="quiet" onClick={()=>{setKey('');setCases([]);setSelected(null);setError('')}}>Sign out</button></aside>
  <main className="workspace">
   <header><p className="eyebrow">PARTNER NETWORK / ONBOARDING</p><span className="live">● Workspace connected</span></header>
   <div className="title"><div><h1>Supplier cases</h1><p>Follow the evidence. Review the exact record. Make the call.</p></div><button onClick={()=>{setCreating(true);setSelected(null)}}>New supplier</button></div>
   {error&&<p className="error" role="alert">{error}</p>}
   <div className="desk">
    <section className="queue" aria-label="Supplier queue"><div className="queue-head"><span>ACTIVE CASEBOOK</span><span>{cases.length.toString().padStart(2,'0')}</span></div>{cases.map(c=><button key={c.id} className={'case-item '+(selected?.id===c.id?'chosen':'')} onClick={()=>operation(()=>open(c.id))}><span className="case-name">{c.input.name}</span><span className="case-meta">{c.input.tax_id}</span><span className={'pill '+c.state}>{labels[c.state]||c.state}</span></button>)}{!cases.length&&<p className="no-cases">Your next partnership starts here.</p>}</section>
    {creating?<section className="surface"><p className="eyebrow">01 / INTAKE</p><h2>A new partnership</h2><p className="muted">Agents check documents and classify goods. A second operator approves the final record.</p><form onSubmit={create}><label>Legal name<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required minLength={2} maxLength={120}/></label><label>Tax identifier<input value={form.tax_id} onChange={e=>setForm({...form,tax_id:e.target.value})} required pattern="[A-Za-z0-9-]{3,40}"/></label><label>Goods or services<textarea value={form.description} onChange={e=>setForm({...form,description:e.target.value})} maxLength={4000} rows={3}/></label><button disabled={busy}>{busy?'Checking…':'Start checks'}</button><button type="button" className="secondary" onClick={()=>setCreating(false)}>Close intake</button></form></section>
    :selected?<section className="surface case-detail"><p className="eyebrow">CASE / {selected.id.slice(0,8).toUpperCase()}</p><h2>{selected.input.name}</h2><div className="identity"><span>{selected.input.tax_id}</span><span>{selected.input.description||'No goods description supplied'}</span></div><p className={'status-banner '+selected.state}>{labels[selected.state]||selected.state}</p><div className="journey"><div><span className="step-number">01</span><strong>Document check</strong><small>Identity & tax evidence</small></div><div><span className="step-number">02</span><strong>Catalog match</strong><small>Category & local risk rules</small></div><div><span className="step-number">03</span><strong>Human decision</strong><small>Exact record approval</small></div></div>{selected.state==='input-required'&&<section className="action-panel"><h3>One document to continue</h3><p className="muted">Provide the tax identifier transcribed from the certificate. The document agent compares it with the intake record.</p><label>Certificate tax identifier<input value={certificate} onChange={e=>setCertificate(e.target.value)} maxLength={40}/></label><button disabled={busy||!certificate} onClick={()=>action('resume',{documents:[{type:'tax_certificate',tax_id:certificate}]})}>Provide tax certificate</button></section>}
    {selected.proposal&&<section className="record"><p className="eyebrow">EXACT RECORD / HUMAN REVIEW</p><h3>Proposed supplier record</h3><dl>{Object.entries(selected.proposal).map(([k,v])=><div key={k}><dt>{k.replace('_',' ')}</dt><dd>{v}</dd></div>)}</dl><p className="digest">Record fingerprint <code>{selected.proposal_digest}</code></p></section>}</section>
    :<section className="surface empty"><p className="eyebrow">THE CASEBOOK</p><h2>Every partner has a story.<br/>Start with the facts.</h2><p className="muted">Choose a case to inspect its evidence, or add a supplier to begin checks.</p></section>}
   </div>
   <footer>FOUNDRY / Independent checks · Clear ownership · Human approval</footer>
  </main>
 </div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
