'use strict';
const $ = s => document.querySelector(s);
let runs = [], events = [], selected = '', tab = 'events', filter = '', position = Infinity, timer = null, memory = null, offline = false;
const demos = {
  recall: 'What presentation style do I prefer? Please check your semantic memory before answering.',
  correct: 'Actually, for this MemoryDock demo I now prefer detailed explanations with one concrete example. Update demo.presentation.style, then retrieve it to confirm the correction.',
  episode: 'Look up the past task demo-rehearsal. What happened, and what lesson did it record?',
  procedure: 'Read repeated_local_identifier_lookup. Which version is active, which is rejected, and what does that tell us about your procedural memory? Do not execute it.',
  miss: 'Search semantic memory for "penguin spacecraft". Are the returned memories actually relevant? Explain any mismatch without inventing a connection.'
};
function el(tag, text, cls) { const n = document.createElement(tag); if(text !== undefined) n.textContent = text; if(cls) n.className = cls; return n; }
async function api(path, options) { const r = await fetch(path, options); const d = await r.json(); if(!r.ok) throw Error(d.error || 'Request failed'); return d; }
function visible() { return events.slice(0, Number.isFinite(position) ? position : events.length); }
function renderConversation() {
  const run = runs.find(r => r.id === selected); if(!run) return;
  const root = $('#conversation'); root.replaceChildren();
  const user = el('div', undefined, 'message user'); user.append(el('span','YOU','who'),el('div',run.prompt)); root.append(user);
  const response = visible().find(e=>e.stage==='response'||(e.stage==='error'&&e.payload.response));
  const message=el('div',undefined,'message'); message.append(el('span','GRACE','who'),el('div',response ? response.payload.response : Number.isFinite(position) ? 'Replay in progress…' : run.status==='running' ? 'Grace is working. Memory operations will appear as they complete…' : run.response));root.append(message);
}
function render() {
  const seen = visible(); const stages = new Set(seen.map(e=>e.stage));
  if(seen.some(e=>e.payload.tool)) stages.add('retrieval');
  document.querySelectorAll('.node').forEach(n=>{ n.classList.toggle('active',stages.has(n.dataset.stage));n.classList.toggle('current',seen.length>0 && seen[seen.length-1].stage===n.dataset.stage && (Number.isFinite(position)||runs.find(r=>r.id===selected)?.status==='running')); });
  $('#event-count').textContent=seen.length+' EVENTS';
  $('#mode').textContent=offline?'OFFLINE REPLAY':Number.isFinite(position)?'RECORDED REPLAY':runs.find(r=>r.id===selected)?.status?.toUpperCase()||'READY';
  $('#scrubber').max=events.length;$('#scrubber').value=seen.length;
  $('#timeline-events').replaceChildren(...events.map((e,i)=>{const n=el('button',e.stage,'tick'+(i<seen.length?' seen':'')); n.onclick=()=>{stop();position=i+1;render();}; return n;}));
  renderConversation();renderInspector();
}
function renderInspector(){
  const root=$('#inspector-body'); root.replaceChildren();
  if(tab==='events'){
    if(filter){const b=el('button','Showing '+filter+' · clear');b.onclick=()=>{filter='';renderInspector();};root.append(b);}
    const list=visible().filter(e=>!filter||e.stage===filter);
    if(!list.length)root.append(el('p','No observed events here yet. Submit a prompt or select a recorded run.'));
    list.forEach(e=>{const d=el('details',undefined,'event '+e.stage);d.append(el('div',new Date(e.created).toLocaleTimeString(),'time'),el('summary',e.title),el('pre',JSON.stringify(e.payload,null,2)));root.append(d);});
  }else if(tab==='memory'){
    root.append(el('p',offline?'Exported memory snapshot; not reconstructed for the selected run.':'Current stored records, not a historical replay snapshot.'));
    if(!memory)return;
    for(const type of ['semantic','episodic','procedural']){
      root.append(el('h3',type[0].toUpperCase()+type.slice(1)+' / '+memory[type].length,'group-title'));
      for(const r of memory[type]){const c=el('div',undefined,'memory-card');c.append(el('h3',r.key||r.title||r.name+' · v'+r.version),el('p',r.claim||r.evidence||r.instructions),el('small',(r.status||r.confidence||'')+' · '+(r.source_ref||'')));root.append(c);}
    }
  }else{
    const box=el('div',undefined,'about');
    const items=[['Semantic','Grace’s bounded lexical retriever ranks word overlap, preferences, and recency. It is fast and inspectable, but can return zero-overlap facts and miss paraphrases. No vector search is claimed.'],['Episodic','The demo reads a saved task using Grace’s work_get implementation. Production also has conversations and archived history; those private stores are not exposed here.'],['Procedural','Versioned methods separate candidate, active, and rejected advice. The displayed procedure is a read-only snapshot from Grace. Review evidence applies to its recorded use case, not every future task.'],['What the trace proves','MCP requests, completed operations, returned records, elapsed operation time, and the final response. Full prompt assembly and causal influence on an answer are unknown.'],['Presentation boundary','Real Grace runtime and installed memory code. Demo facts and rehearsal task are fixtures. Corrections and candidates stay in the isolated demo store; no production memory is modified.']];
    items.forEach(([h,t])=>box.append(el('h3',h),el('p',t)));
    if(memory?.snapshot){box.append(el('h3','Production snapshot provenance'),el('pre',JSON.stringify(memory.snapshot,null,2)));}
    root.append(box);
  }
}
function stop(){if(timer)clearInterval(timer);timer=null;$('#replay').textContent='▶ Replay';}
async function refresh(){
  try{
    const [health,all]=await Promise.all([api('/api/health'),api('/api/runs')]);runs=all;
    offline=!!health.replay_only;
    $('#docked-agents').replaceChildren(...(health.agents||[]).map(agent=>{
      const card=el('div',undefined,'dock-card');
      card.append(el('span','↳','dock-symbol'),el('strong',agent.name+' has docked'),
        el('span',agent.state==='connected'?'Connected via MCP · working now':'MCP connection verified · ready for the next run','dock-detail'));
      card.title='Last MCP connection: '+new Date(agent.last_docked).toLocaleString();
      return card;
    }));
    $('#health').textContent=health.replay_only?'Offline · recorded Grace runs':health.busy?'Grace is running':health.ready?'Grace ready · MCP opens per run':'Setup required';$('#lamp').classList.toggle('ready',health.ready);$('#send').disabled=health.busy||health.replay_only;
    const select=$('#runs');select.replaceChildren(el('option','Choose a recorded run'));select.firstChild.value='';
    runs.forEach(r=>{const o=el('option',r.prompt.slice(0,65)+' · '+r.status);o.value=r.id;select.append(o);});select.value=selected;
    if(selected){events=(await api('/api/runs/'+selected)).events;render();}
  }catch(e){$('#health').textContent='Disconnected';$('#lamp').classList.remove('ready');$('#error').textContent=e.message;}
}
async function loadMemory(){try{memory=await api('/api/memory');if(tab!=='events')renderInspector();}catch(e){$('#error').textContent=e.message;}}
document.querySelectorAll('[data-demo]').forEach(b=>b.onclick=()=>{$('#prompt').value=demos[b.dataset.demo];$('#prompt').focus();});
document.querySelectorAll('[data-stage]').forEach(b=>b.onclick=()=>{tab='events';filter=b.dataset.stage;selectTab();renderInspector();});
function selectTab(){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('selected',b.dataset.tab===tab));}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;selectTab();if(tab==='memory')loadMemory();renderInspector();});
$('#prompt-form').onsubmit=async e=>{e.preventDefault();$('#error').textContent='';stop();try{const d=await api('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:$('#prompt').value})});selected=d.id;position=Infinity;filter='';await refresh();}catch(e){$('#error').textContent=e.message;}};
$('#runs').onchange=async e=>{stop();selected=e.target.value;position=Infinity;filter='';await refresh();};
$('#replay').onclick=()=>{if(timer){stop();return;}if(!events.length)return;position=0;$('#replay').textContent='Ⅱ Pause';render();timer=setInterval(()=>{position=Math.min(position+1,events.length);render();if(position===events.length)stop();},1000);};
$('#step').onclick=()=>{stop();position=Number.isFinite(position)?Math.min(position+1,events.length):1;render();};
$('#live').onclick=()=>{stop();position=Infinity;render();};
$('#scrubber').oninput=e=>{stop();position=Number(e.target.value);render();};
renderInspector();refresh();loadMemory();setInterval(refresh,1500);
