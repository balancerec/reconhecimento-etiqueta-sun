(function(root){
'use strict';
const MAX=12*1024*1024;
function baseUrl(value,location){
 const url=new URL(value||location.origin,location.href);
 if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw Error('Informe um endereço HTTP ou HTTPS válido.');
 if(location.protocol==='https:'&&url.protocol!=='https:')throw Error('Esta página HTTPS precisa de uma API HTTPS. Para a API local, abra http://localhost:8000.');
 if(!value&&location.hostname.endsWith('github.io'))throw Error('Informe o endereço HTTPS do backend. O GitHub Pages não executa a API.');
 url.search='';url.hash='';return url.href.replace(/\/$/,'');
}
async function request(base,path,options={},fetcher=root.fetch.bind(root)){
 let response;
 try{response=await fetcher(base+path,options);}catch(e){if(e.name==='AbortError')throw e;throw Error('Não foi possível conectar à API. Confira endereço, servidor e permissão de origem (CORS).');}
 let data;try{data=await response.json();}catch(e){throw Error('O endereço respondeu sem JSON. Confira se ele aponta para a API.');}
 if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Erro HTTP '+response.status+' na API.');
 return data;
}
if(typeof module!=='undefined')module.exports={baseUrl,request};
if(!root.document)return;
const $=id=>document.getElementById(id);
const state={result:null,index:0,callback:null,controller:null,generation:0,busy:false,base:null};
const names={sku:'SKU',product_description:'Descrição',volume_ml:'Volume (ml)',units_per_case:'Unidades por caixa',manufacturing_date:'Fabricação',expiration_date:'Vencimento',lot:'Lote',auxiliary_code:'Código auxiliar',gtin14:'GTIN-14',quantity_boxes:'Quantidade de caixas',lastro:'LASTRO',shelf_life:'Prazo de validade',entry_document:'Documento de entrada',sscc:'SSCC'};
const numeric=new Set(['volume_ml','units_per_case','quantity_boxes','lastro']);
const message=t=>{$('backendConnection').textContent=t;};
const storage={get(k){try{return localStorage.getItem(k);}catch{return null;}},set(k,v){try{localStorage.setItem(k,v);}catch{}}};
function selected(){return state.result?.labels[state.index]||null;}
function controls(busy){state.busy=busy;for(const id of ['backendSave','backendExport','backendLabel','sunAuto','sunOCR','sunScan','dunRetry']){const el=$(id);if(el)el.disabled=busy;}if(!busy){const photo=$('sunPreview');if(photo&&!photo.getAttribute('src'))for(const id of ['sunAuto','sunOCR','sunScan'])$(id).disabled=true;}}
function clear(){state.result=null;state.callback=null;state.base=null;$('backendResults').hidden=true;$('backendFields').replaceChildren();}
function cancel(){state.generation++;state.controller?.abort();state.controller=null;clear();controls(false);}
function render(){
 const label=selected();$('backendFields').replaceChildren();$('backendResults').hidden=!state.result;
 if(!label){$('backendValidation').textContent='Nenhuma etiqueta detectada.';state.callback?.(null);return;}
 for(const [key,name] of Object.entries(names)){
  const wrap=document.createElement('div');wrap.className='sun-field';
  const text=document.createElement('label');text.htmlFor='backend_'+key;text.textContent=name;
  const input=document.createElement('input');input.id='backend_'+key;input.value=label.fields[key]??'';input.dataset.field=key;
  if(numeric.has(key)){input.type='number';input.min='1';input.step='1';}
  wrap.append(text,input);$('backendFields').append(wrap);
 }
 const v=label.validation;
 $('backendValidation').textContent='Inspeção '+state.result.id+' · '+label.label_type+' · '+v.status+' · Barras: '+(label.barcode.decoded_value||'não decodificadas')+' · Erros: '+(v.errors.join(', ')||'nenhum')+' · Avisos: '+v.warnings.join(', ')+'. Revisão humana obrigatória.';
 const evidence=$('backendEvidence');
 if(evidence){evidence.replaceChildren();for(const item of label.field_evidence||[]){
  const row=document.createElement('p');row.className='sun-muted';
  row.textContent=(names[item.field_name]||item.field_name)+': '+(item.normalized_value??'ausente')+' · '+item.source+' · '+(item.engine||'operador')+(item.confidence!=null?' · índice do motor '+Math.round(item.confidence*100)+'%':'');evidence.append(row);
 }}
 state.callback?.(label);
}
function options(preferred){
 const select=$('backendLabel');select.replaceChildren();
 state.result.labels.forEach((label,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent='Etiqueta '+(i+1)+' · '+label.label_type;select.append(o);});
 state.index=Math.max(0,state.result.labels.findIndex(l=>l.label_type===preferred.toUpperCase()));select.value=String(state.index);render();
}
async function recognize(kind,file,callback){
 cancel();const generation=state.generation;
 if(!file||!file.type.startsWith('image/'))throw Error('Selecione uma imagem.');
 if(file.size>MAX)throw Error('Limite de 12 MB por foto.');
 const base=baseUrl($('backendUrl').value.trim(),root.location);
 state.controller=new AbortController();const controller=state.controller;
 controls(true);message('Processando imagem no backend. Aguarde...');
 const timeout=setTimeout(()=>controller.abort(),600000);
 try{
  const body=new FormData();body.append('image',file);
  const job=await request(base,'/v2/jobs',{method:'POST',body,signal:controller.signal});
  if(!job.id)throw Error('Servidor incompatível. Atualize a instalação local.');
  let result;
  while(generation===state.generation){
   const status=await request(base,'/v2/jobs/'+encodeURIComponent(job.id),{signal:controller.signal});
   if(generation!==state.generation)return;
   message((status.progress||0)+'% ? '+(status.message||'Processando no servidor'));
   for(const id of [kind==='dun'?'dunStatus':'sunAutoProgress']){const el=$(id);if(el)el.textContent=(status.progress||0)+'% ? '+(status.message||'Processando');}
   if(status.status==='COMPLETED'){result=status.result;break;}
   if(status.status==='FAILED')throw Error(status.message||'Falha no reconhecimento');
   await new Promise((resolve,reject)=>{
    const done=()=>{clearTimeout(timer);controller.signal.removeEventListener('abort',abort);};
    const abort=()=>{done();reject(new DOMException('Cancelado','AbortError'));};
    const timer=setTimeout(()=>{done();resolve();},800);
    controller.signal.addEventListener('abort',abort,{once:true});
    if(controller.signal.aborted)abort();
   });
  }
  if(!result)return;
  if(generation!==state.generation)return;
  if(!result.id||!Array.isArray(result.labels))throw Error('Resposta incompatível com a API de etiquetas.');
  state.result=result;state.base=base;state.callback=callback;options(kind);message('Leitura armazenada no backend. Selecione uma etiqueta e revise os campos.');
 }catch(e){
  if(generation!==state.generation)return;
  const error=e.name==='AbortError'?Error('Tempo limite atingido. Tente uma foto menor ou consulte a disponibilidade do servidor.'):e;
  message(error.message);throw error;
 }finally{clearTimeout(timeout);if(generation===state.generation)controls(false);}
}
async function save(){
 const label=selected();if(!label||state.busy)return;
 const operator=$('backendOperator').value.trim(),reason=$('backendReason').value.trim();
 if(!operator||!reason)return message('Informe operador e motivo para registrar as correções.');
 const changes=[];
 for(const input of $('backendFields').querySelectorAll('input')){
  const key=input.dataset.field,s=input.value.trim();let value=s||null;
  if(s&&numeric.has(key)){if(!/^\d+$/.test(s)||Number(s)<=0)return message('Informe um inteiro positivo em '+names[key]);value=Number(s);}
  if(value!==label.fields[key])changes.push({label_index:state.index,field_name:key,value,operator,reason});
 }
 if(!changes.length)return message('Nenhuma alteração para salvar.');
 const generation=state.generation,base=state.base,id=state.result.id;
 controls(true);
 try{
  for(const change of changes){
   const result=await request(base,'/v1/inspections/'+encodeURIComponent(id)+'/corrections',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(change),signal:AbortSignal.timeout(30000)});
   if(generation!==state.generation)return;state.result=result;
  }
  render();message('Correções registradas com operador, motivo e valores anteriores.');
 }catch(e){
  if(generation!==state.generation)return;
  render();message('Falha ao salvar todas as correções; confira os campos já registrados. '+e.message);
 }finally{if(generation===state.generation)controls(false);}
}
root.LabelBackend={enabled:()=>!$('recognitionMode')||$('recognitionMode').value==='api',recognize,cancel,selected,snapshot:()=>state.result?JSON.parse(JSON.stringify(state.result)):null};
root.addEventListener('DOMContentLoaded',()=>{
 const local=new URL(root.location.href).searchParams.get('local')==='1';$('recognitionMode').value=local?'api':(storage.get('labelRecognitionMode')||'api');$('backendUrl').value=local?'':(storage.get('labelBackendUrl')||'');
 for(const [id,key] of [['recognitionMode','labelRecognitionMode'],['backendUrl','labelBackendUrl']])$(id).addEventListener('change',()=>{cancel();storage.set(key,$(id).value);message('Configuração alterada. Execute o reconhecimento novamente.');});
 $('backendLabel').onchange=()=>{state.index=Number($('backendLabel').value);render();};
 $('backendHealth').onclick=async()=>{
  try{const base=baseUrl($('backendUrl').value.trim(),root.location);await request(base,'/health',{signal:AbortSignal.timeout(10000)});message('API conectada; OCR disponível.');}catch(e){message(e.name==='TimeoutError'?'A API não respondeu em 10 segundos.':e.message);}
 };
 $('backendSave').onclick=save;
 $('backendExport').onclick=()=>{
  if(!state.result)return;const blob=new Blob([JSON.stringify(state.result,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='etiquetas_'+state.result.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
});
})(typeof window!=='undefined'?window:globalThis);
