/* Dependency visualization without a graph-layout/CDN dependency. Data comes only from Relate. */
const $ = s => document.querySelector(s);
const NS = 'http://www.w3.org/2000/svg';
const state = {graph:null, impact:null, selected:'lab.assays.moisture_pct', direction:'downstream', view:'route', chosenOutput:null, scale:1, offsetX:0, offsetY:0, extent:{width:1200,height:600}};
const OUTPUT = new Set(['Dashboard','Metric']);
const TRANSFORM = new Set(['Transformation','Rule']);
const assetMap = () => new Map(state.graph.assets.map(a => [a.id,a]));
function elt(tag, attrs={}, parent){ const n=document.createElementNS(NS,tag); Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v)); if(parent)parent.append(n); return n; }
function textSvg(parent,label,x,y,cls){ const n=elt('text',{x,y,class:cls},parent); n.textContent=label; return n; }
function shortName(s,max=23){return s.length>max?s.slice(0,max-1)+'…':s;}
function kindClass(a){return OUTPUT.has(a.kind)?'output':TRANSFORM.has(a.kind)?'transform':'';}
function showError(err){$('#path-detail').textContent=`Cannot query Relate: ${err.message}`;$('#focus-subtitle').textContent='Query failed; inspect local server logs.';}
async function fetchJson(path){const res=await fetch(path);const obj=await res.json();if(!res.ok)throw new Error(obj.error||res.statusText);return obj;}
async function load(){try{
  state.graph=await fetchJson('/api/graph');
  const imported=state.graph.source==='openlineage';
  $('#stat-assets').textContent=state.graph.assets.length+(state.graph.truncated?'+':'');
  $('#stat-flows').textContent=state.graph.flows.length+(state.graph.truncated?'+':'');
  $('#stat-systems').textContent=new Set(state.graph.assets.map(a=>a.system).filter(Boolean)).size;
  $('#store-path').textContent=state.graph.store;
  if(imported){
    $('#scenario').closest('.rail-block').style.display='none';
    $('.top-time').textContent='OPENLINEAGE · IMPORTED';
    document.querySelector('footer span').textContent='Imported OpenLineage metadata · only explicit, documented flows';
    $('.review-strip p').textContent='Imported lineage is evidence of documented dependencies, not a guarantee that missing paths are safe.';
    const sources=new Set(state.graph.flows.filter(e=>e.mode!=='scope').map(e=>e.source));
    state.selected=state.graph.assets.find(a=>a.kind==='Column'&&sources.has(a.id))?.id
      ||state.graph.assets.find(a=>sources.has(a.id))?.id
      ||state.graph.assets[0]?.id;
  }
  if(!state.selected)throw new Error('No imported assets: load a valid OpenLineage event first.');
  await selectAsset(state.selected);
}catch(e){showError(e);}}
async function selectAsset(id){state.selected=id;state.chosenOutput=null;try{
 state.impact=await fetchJson(`/api/impact?id=${encodeURIComponent(id)}&direction=${state.direction}`);
 // A large overview is bounded. Native Relate traversals may include nodes
 // outside that preview; merge their ACTUAL path evidence before rendering.
 const assets=new Map(state.graph.assets.map(a=>[a.id,a]));
 assets.set(state.impact.source.id,state.impact.source);
 const edges=new Map(state.graph.flows.map(e=>[`${e.source}::${e.target}`,e]));
 for(const asset of state.impact.affected){
   assets.set(asset.id,asset);
   for(const path of asset.paths||[]){
     path.ids.slice(1).forEach((target,i)=>{
       const source=path.ids[i],e=path.edges[i]||{};
       const key=`${source}::${target}`;
       if(!edges.has(key))edges.set(key,{source,target,why:e.why||'',mode:e.mode||'',provenance:e.provenance||''});
     });
   }
 }
 state.graph.assets=Array.from(assets.values());
 state.graph.flows=Array.from(edges.values());
 updateResults();renderGraph();
}catch(e){showError(e);}}
function updateResults(){const d=state.impact;$('#focus-title').textContent=d.source.name;$('#focus-subtitle').textContent=`${d.source.kind} · ${d.source.system} · ${d.source.id}`;$('#affected').textContent=d.affected_count;$('#business-outputs').textContent=state.graph.source==='openlineage'
 ?d.affected.filter(a=>a.kind==='Table'||a.kind==='Column').length:d.output_count;$('#system-count').textContent=d.systems.length;$('#result-count').textContent=d.affected_count;
if(state.graph.source==='openlineage'){
  $('.metrics article:nth-child(2) small').textContent='CONNECTED DATA ASSETS';
  $('.metrics article:nth-child(2) span').textContent='Downstream datasets and fields';
  $('.output-list .eyebrow').textContent='DOWNSTREAM DATASETS / FIELDS';
}$('#signal').textContent=d.truncated?'PATH LIMIT REACHED':'VERIFIED CYPHER PATHS';const list=$('#outputs');list.replaceChildren();const outputs=d.outputs.length?d.outputs:(state.graph.source==='openlineage'
 ? d.affected.filter(a=>a.kind==='Table'||a.kind==='Column').slice(0,24)
 : d.affected.slice(0,8));if(!outputs.length){list.textContent='No connected assets in this direction.';$('#path-detail').textContent='No dependency paths were found.';return;}outputs.forEach((asset,i)=>{const button=document.createElement('button');button.className='output';button.dataset.id=asset.id;const icon=document.createElement('span');icon.className='out-icon';icon.textContent=asset.kind==='Dashboard'?'▤':asset.kind==='Metric'?'◈':'◇';const labels=document.createElement('span');const title=document.createElement('strong');title.textContent=asset.name;const sub=document.createElement('small');sub.textContent=`${asset.kind.toUpperCase()} · ${asset.system}`;labels.append(title,sub);const hops=document.createElement('span');hops.className='hops';hops.textContent=`${asset.hops} HOPS`;button.append(icon,labels,hops);button.onclick=()=>{state.chosenOutput=asset.id;document.querySelectorAll('.output').forEach(b=>b.classList.remove('active'));button.classList.add('active');showPath(asset);if(state.view==='route')renderGraph();else highlightPath();};list.append(button);});const preferred=(state.selected==='lab.assays.moisture_pct'&&state.direction==='downstream'?outputs.find(a=>a.id==='dash.esg'):null)||outputs[0];state.chosenOutput=preferred.id;showPath(preferred);document.querySelectorAll('#outputs .output').forEach(b=>b.classList.toggle('active',b.dataset.id===preferred.id));}
function showPath(asset){const area=$('#path-detail');area.replaceChildren();const name=document.createElement('div');name.className='path-name';name.textContent=asset.name;area.append(name);const desc=document.createElement('p');desc.textContent=asset.detail||'Connected dependency';area.append(desc);for(const [idx,path] of asset.paths.entries()){if(idx>0){const marker=document.createElement('p');marker.className='eyebrow';marker.textContent='ALTERNATIVE PATH';area.append(marker);}path.ids.forEach((id,i)=>{const meta=assetMap().get(id);const step=document.createElement('div');step.className='path-step';const title=document.createElement('b');title.textContent=meta?.name||id;const sub=document.createElement('small');sub.textContent=`${meta?.kind||'Asset'} · ${meta?.system||''}`;step.append(title,sub);if(i<path.edges.length){const why=document.createElement('p');why.textContent=path.edges[i].why;step.append(why);}area.append(step);});}}
function activeRoute(){return state.impact?.affected.find(a=>a.id===state.chosenOutput)?.paths[0]?.ids||[state.selected];}
function currentIds(){
 if(state.view==='all')return new Set(state.graph.assets.map(a=>a.id));
 if(state.view==='route')return new Set(activeRoute());
 const ids=new Set([state.selected]);
 for(const a of state.impact.affected)for(const p of a.paths)p.ids.forEach(id=>ids.add(id));
 return ids;
}
function layerLayout(assets,flows){const ids=new Set(assets.map(a=>a.id));const incoming=new Map(assets.map(a=>[a.id,0]));const forward=new Map(assets.map(a=>[a.id,[]]));for(const edge of flows){if(!ids.has(edge.source)||!ids.has(edge.target))continue;incoming.set(edge.target,incoming.get(edge.target)+1);forward.get(edge.source).push(edge.target);}const level=new Map(assets.map(a=>[a.id,0]));const q=[...assets].filter(a=>incoming.get(a.id)===0).map(a=>a.id);while(q.length){const id=q.shift();for(const next of forward.get(id)){level.set(next,Math.max(level.get(next),level.get(id)+1));incoming.set(next,incoming.get(next)-1);if(incoming.get(next)===0)q.push(next);}}const buckets=new Map();for(const a of assets){const l=level.get(a.id)||0;if(!buckets.has(l))buckets.set(l,[]);buckets.get(l).push(a);}const pos=new Map(),maxCount=Math.max(...[...buckets.values()].map(a=>a.length));const height=Math.max(480,maxCount*98+110);for(const [l,group]of buckets){group.sort((a,b)=>a.system.localeCompare(b.system)||a.name.localeCompare(b.name));const yStart=(height-group.length*98)/2+12;group.forEach((a,i)=>pos.set(a.id,{x:45+l*245,y:yStart+i*98}));}return {pos,width:Math.max(1000,(Math.max(...buckets.keys())+1)*245+60),height};}
function routeLayout(){
 const route=activeRoute(),mobile=window.innerWidth<751,cols=Math.min(mobile?2:4,route.length),spacing=mobile?202:229;
 const pos=new Map();
 route.forEach((id,i)=>{const row=Math.floor(i/cols),col=i%cols;pos.set(id,{x:36+(row%2===0?col:cols-1-col)*spacing,y:46+row*127});});
 return {pos,width:72+cols*spacing,height:Math.max(300,Math.ceil(route.length/cols)*127+95)};
}
function connectionPath(a,b){
 if(state.view==='route'&&Math.abs(a.y-b.y)>20){const x1=a.x+86,y1=a.y+68,x2=b.x+86,y2=b.y,mid=(y1+y2)/2;return 'M '+x1+' '+y1+' C '+x1+' '+mid+', '+x2+' '+mid+', '+x2+' '+y2;}
 const forward=b.x>=a.x,x1=a.x+(forward?172:0),y1=a.y+34,x2=b.x+(forward?0:172),y2=b.y+34,mid=(x1+x2)/2;
 return 'M '+x1+' '+y1+' C '+mid+' '+y1+', '+mid+' '+y2+', '+x2+' '+y2;
}
function renderGraph(){if(!state.graph||!state.impact)return;const ids=currentIds();const assets=state.graph.assets.filter(a=>ids.has(a.id));const route=activeRoute(),routeEdges=new Set(route.slice(1).map((id,i)=>[route[i],id].sort().join('::')));const flows=state.graph.flows.filter(e=>ids.has(e.source)&&ids.has(e.target)&&(state.view!=='route'||routeEdges.has([e.source,e.target].sort().join('::'))));const {pos,width,height}=state.view==='route'?routeLayout():layerLayout(assets,flows);state.extent={width,height};const world=$('#world');world.replaceChildren();for(const edge of flows){const a=pos.get(edge.source),b=pos.get(edge.target);elt('path',{class:'edge',d:connectionPath(a,b), 'data-src':edge.source,'data-dst':edge.target,'marker-end':'url(#arrow)'},world);}for(const a of assets){const p=pos.get(a.id);const group=elt('g',{class:`node ${kindClass(a)}${a.id===state.selected?' selected':''}`,transform:`translate(${p.x} ${p.y})`,'data-id':a.id,tabindex:'0',role:'button','aria-label':`Inspect ${a.name}`},world);elt('rect',{width:172,height:68},group);const fill=OUTPUT.has(a.kind)?'#f2ae75':TRANSFORM.has(a.kind)?'#ad99f4':'#76a6dd';elt('rect',{x:0,y:10,width:3,height:47,fill,rx:1.5,class:'left-strip'},group);textSvg(group,a.kind.toUpperCase(),12,17,'type');textSvg(group,shortName(a.name),12,39,'name');textSvg(group,shortName(a.system,27),12,57,'sys');group.addEventListener('click',e=>{e.stopPropagation();selectAsset(a.id);});group.addEventListener('keydown',e=>{if(e.key==='Enter')selectAsset(a.id);});}$('#canvas-help').textContent=state.view==='route'?'SHORTEST CYPHER PATH · SELECT AN OUTPUT TO CHANGE THE ROUTE · DRAG TO PAN':'DRAG TO PAN · SCROLL TO ZOOM · CLICK AN ASSET';fitGraph();highlightPath();}
function highlightPath(){const paths=state.impact?.affected.find(a=>a.id===state.chosenOutput)?.paths||[];const nodes=new Set(paths.flatMap(p=>p.ids));nodes.add(state.selected);const links=new Set(paths.flatMap(p=>p.ids.slice(1).map((id,i)=>`${p.ids[i]}::${id}`)));for(const n of document.querySelectorAll('#world .node'))n.classList.toggle('dim',nodes.size>1&&!nodes.has(n.dataset.id));for(const e of document.querySelectorAll('#world .edge')){const active=links.has(`${e.dataset.src}::${e.dataset.dst}`)||links.has(`${e.dataset.dst}::${e.dataset.src}`);e.classList.toggle('active',active);e.classList.toggle('dim',links.size>0&&!active);e.setAttribute('marker-end',active?'url(#arrow-hi)':'url(#arrow)');}}
function graphTransform(){const world=$('#world');world.setAttribute('transform',`translate(${state.offsetX} ${state.offsetY}) scale(${state.scale})`);}
function fitGraph(){const svg=$('#graph');const rect=svg.getBoundingClientRect();const w=rect.width||900,h=rect.height||520;state.scale=Math.min((w-50)/state.extent.width,(h-50)/state.extent.height,1.25);state.offsetX=(w-state.extent.width*state.scale)/2;state.offsetY=(h-state.extent.height*state.scale)/2;graphTransform();}
function zoom(m){const r=$('#graph').getBoundingClientRect(),cx=r.width/2,cy=r.height/2,old=state.scale;state.scale=Math.max(.18,Math.min(2.2,old*m));state.offsetX=cx-(cx-state.offsetX)*state.scale/old;state.offsetY=cy-(cy-state.offsetY)*state.scale/old;graphTransform();}
function setupControls(){const input=$('#search');input.addEventListener('input',()=>{const term=input.value.toLowerCase().trim();const suggestions=$('#suggestions');suggestions.replaceChildren();if(!term)return;const matching=state.graph.assets.filter(a=>`${a.id} ${a.name} ${a.system} ${a.detail}`.toLowerCase().includes(term)).slice(0,8);matching.forEach(a=>{const b=document.createElement('button');b.className='suggestion';b.textContent=a.name;const sm=document.createElement('small');sm.textContent=state.graph?.source==='openlineage'?a.detail.replace(' (OpenLineage)',''):`${a.kind} · ${a.system}`;b.append(sm);b.onclick=()=>{input.value='';suggestions.replaceChildren();selectAsset(a.id);};suggestions.append(b);});});window.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement!==input){e.preventDefault();input.focus();}if(e.key==='Escape'){input.blur();$('#suggestions').replaceChildren();}});function scenario(id){state.direction='downstream';$('#downstream').classList.add('active');$('#upstream').classList.remove('active');state.view='route';for(const name of ['route','network','all'])$(`#view-${name}`).classList.toggle('active',name==='route');selectAsset(id);}$('#scenario').onclick=()=>scenario('lab.assays.moisture_pct');$('#scenario-safe').onclick=()=>scenario('field.harvests.field_id');for(const dir of ['downstream','upstream'])$(`#${dir}`).onclick=()=>{state.direction=dir;for(const d of ['downstream','upstream'])$(`#${d}`).classList.toggle('active',dir===d);selectAsset(state.selected);};for(const view of ['route','network','all'])$(`#view-${view}`).onclick=()=>{state.view=view;for(const name of ['route','network','all'])$(`#view-${name}`).classList.toggle('active',name===view);renderGraph();};$('#download-report').onclick=async()=>{const button=$('#download-report'),saved=button.textContent;button.disabled=true;button.textContent='Preparing…';try{const params=new URLSearchParams({id:state.selected,direction:state.direction,change:$('#change-note').value.trim()});const response=await fetch('/api/report?'+params.toString());if(!response.ok){const e=await response.json();throw Error(e.error||'Report unavailable');}const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');link.href=url;link.download='impact-'+state.selected.replace(/[^a-zA-Z0-9._-]/g,'_')+'.md';link.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}catch(e){showError(e);}finally{button.disabled=false;button.textContent=saved;}};$('#zoom-in').onclick=()=>zoom(1.25);$('#zoom-out').onclick=()=>zoom(.8);$('#zoom-fit').onclick=fitGraph;const svg=$('#graph');let prev=null;svg.addEventListener('pointerdown',e=>{if(e.target.closest('.node'))return;prev={x:e.clientX,y:e.clientY};svg.setPointerCapture(e.pointerId);});svg.addEventListener('pointermove',e=>{if(!prev)return;state.offsetX+=e.clientX-prev.x;state.offsetY+=e.clientY-prev.y;prev={x:e.clientX,y:e.clientY};graphTransform();});svg.addEventListener('pointerup',()=>{prev=null;});svg.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY<0?1.12:.89);},{passive:false});window.addEventListener('resize',()=>{if(state.graph)fitGraph();});}
setupControls();load();
