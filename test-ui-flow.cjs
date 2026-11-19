const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class El{
 constructor(){this.value='';this.children=[];this.dataset={};this.disabled=false;this.hidden=false;}
 set value(v){this._value=String(v)}get value(){return this._value}
 append(...items){this.children.push(...items)}replaceChildren(...items){this.children=items}
 getAttribute(name){return this[name]||null}querySelectorAll(){return this.children.flatMap(c=>c.children).filter(c=>c.dataset?.field)}
 addEventListener(){}
}
const ids=new Map(),el=id=>{if(!ids.has(id))ids.set(id,new El());return ids.get(id)};
el('recognitionMode').value='api';el('backendUrl').value='';
let pending=[],boot;
const window={document:{getElementById:el,createElement:()=>new El()},location:{origin:'http://localhost:8000',href:'http://localhost:8000/',protocol:'http:',hostname:'localhost'},fetch:(url,options)=>new Promise(resolve=>pending.push({url,options,resolve})),addEventListener:(name,fn)=>boot=fn};
const context={window,document:window.document,URL,AbortController,AbortSignal,FormData,Blob,setTimeout,clearTimeout,localStorage:{getItem:()=>null,setItem(){}}};
vm.runInNewContext(fs.readFileSync('backend-client.js','utf8'),context);boot();
function result(id,sku='375825'){
 return {id,labels:[{label_type:'SUN',fields:{...Object.fromEntries('sku product_description volume_ml units_per_case manufacturing_date expiration_date lot auxiliary_code gtin14 quantity_boxes lastro shelf_life entry_document sscc'.split(' ').map(k=>[k,null])),sku,quantity_boxes:22,lastro:15},validation:{status:'NEEDS_REVIEW',errors:[],warnings:[]},barcode:{decoded_value:null}}]};
}
(async()=>{
 const api=window.LabelBackend,file=new Blob(['png'],{type:'image/png'});let applied=[];
 const first=api.recognize('sun',file,l=>applied.push(l.fields.sku));
 const second=api.recognize('sun',file,l=>applied.push(l.fields.sku));
 pending[1].resolve({ok:true,json:async()=>result('new')});await second;
 pending[0].resolve({ok:true,json:async()=>result('old','387279')});await first;
 assert.equal(api.snapshot().id,'new');assert.deepEqual(applied,['375825']);
 assert.equal(pending[1].options.body.get('image').type,'image/png');
 el('backendOperator').value='Operador';el('backendReason').value='ConferÃªncia';el('backend_quantity_boxes').value='75';
 // The fake DOM assigns IDs directly through object properties; map them like a browser.
 const input=el('backendFields').querySelectorAll().find(i=>i.dataset.field==='quantity_boxes');input.value='75';
 const save=el('backendSave').onclick();await new Promise(r=>setImmediate(r));
 const sent=JSON.parse(pending[2].options.body);assert.equal(sent.value,75);assert.equal(sent.operator,'Operador');
 const updated=result('new');updated.labels[0].fields.quantity_boxes=75;
 pending[2].resolve({ok:true,json:async()=>updated});await save;
 assert.equal(api.selected().fields.quantity_boxes,75);
 api.cancel();assert.equal(api.snapshot(),null);assert.equal(el('backendResults').hidden,true);
 console.log('OK: multipart, resposta antiga descartada, correÃ§Ãµes auditÃ¡veis e cancelamento.');
})().catch(e=>{console.error(e);process.exitCode=1});
