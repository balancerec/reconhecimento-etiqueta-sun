const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
for(const [i,match] of [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].entries())new vm.Script(match[1],{filename:'inline-'+i+'.js'});
const {baseUrl,request}=require('./backend-client.js');
(async()=>{
 const local={origin:'http://localhost:8000',href:'http://localhost:8000/',protocol:'http:',hostname:'localhost'};
 assert.equal(baseUrl('',local),'http://localhost:8000');
 assert.equal(baseUrl('https://api.example.test/',local),'https://api.example.test');
 const pages={origin:'https://balancerec.github.io',href:'https://balancerec.github.io/reconhecimento-etiqueta-sun/',protocol:'https:',hostname:'balancerec.github.io'};
 assert.throws(()=>baseUrl('',pages),/Pages/);assert.throws(()=>baseUrl('http://localhost:8000',pages),/HTTPS/);assert.throws(()=>baseUrl('file:///tmp',local),/HTTP/);
 let received;const payload={id:'test',labels:[]};
 assert.deepEqual(await request('https://api.test','/v1/recognize',{method:'POST'},async(url,options)=>{received={url,options};return {ok:true,json:async()=>payload}}),payload);
 assert.equal(received.url,'https://api.test/v1/recognize');assert.equal(received.options.method,'POST');
 await assert.rejects(request('','',{},async()=>({ok:false,status:413,json:async()=>({detail:'Limite de 12 MB'})})),/12 MB/);
 await assert.rejects(request('','',{},async()=>({ok:true,json:async()=>{throw Error()}})),/sem JSON/);
 await assert.rejects(request('','',{},async()=>{throw TypeError('Failed to fetch')}),/CORS/);
 console.log('OK: sintaxe de todos os scripts e contrato HTTP, URLs, HTTPS, erros e limite de upload.');
})().catch(e=>{console.error(e);process.exitCode=1});
