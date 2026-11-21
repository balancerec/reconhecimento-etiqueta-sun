from pathlib import Path
p=Path(__file__).resolve().parents[1]/'vision/api/restoration_routes.py';s=p.read_text(encoding='utf-8');s=s.replace('import json,uuid,subprocess,hashlib','import json,uuid,subprocess,hashlib,threading,time\nfrom concurrent.futures import ThreadPoolExecutor');s=s.replace(' image_id:str\n brightness:', ' image_id:str\n copy_id:str|None=None\n segmentation_id:str|None=None\n brightness:');s=s.replace("root=Path(root);r=APIRouter(prefix='/api/v270/restoration',tags=['restoration'])", "root=Path(root);r=APIRouter(prefix='/api/v270/restoration',tags=['restoration']);jobs={};pool=ThreadPoolExecutor(max_workers=1);joblock=threading.Lock()")
a=s.index(" @r.post('/process')");b=s.index(" @r.get('/{image_id}/{processing_id}')",a)
new=''' @r.post('/process')
 def process(req:ProcessRequest):
  try:p=svc.photo(req.image_id)
  except KeyError:raise HTTPException(404,'imagem não registrada')
  svc.check_source(p);ident=uuid.uuid4().hex;out=root/'data'/'restoration'/req.image_id/ident;out.mkdir(parents=True);q={'brightness':req.brightness,'contrast':req.contrast,'saturation':req.saturation,'sharpness':req.sharpness,'deblur':req.deblur,'denoise':req.denoise,'clahe':req.clahe};cfg={'root':str(root),'input':p['path'],'out':str(out),'params':q,'id':ident,'image_id':p['id'],'copy_id':req.copy_id,'segmentation_id':req.segmentation_id,'original_sha256':p['sha256']}
  if req.segmentation_id:
   if not req.segmentation_id.isalnum() or not (root/'data/segmentations'/req.image_id/(req.segmentation_id+'.mask.png')).exists():raise HTTPException(422,'segmentação não registrada para esta imagem')
  (out/'config.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8');jid=uuid.uuid4().hex;jobs[jid]={'job_id':jid,'processing_id':ident,'image_id':p['id'],'status':'QUEUED','progress':0}
  def work():
   jobs[jid]['status']='RUNNING';jobs[jid]['pid']=None;started=time.time()
   try:
    proc=subprocess.Popen([str(gpu),str(worker),str(out/'config.json')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=0x08000000);jobs[jid]['pid']=proc.pid
    try:stdout,stderr=proc.communicate(timeout=900)
    except subprocess.TimeoutExpired:proc.kill();stdout,stderr=proc.communicate();jobs[jid].update(status='TIMED_OUT',error='Worker excedeu limite controlado');(out/'stdout.txt').write_text(stdout);(out/'stderr.txt').write_text(stderr);return
    (out/'stdout.txt').write_text(stdout,encoding='utf-8');(out/'stderr.txt').write_text(stderr,encoding='utf-8');jobs[jid]['exit_code']=proc.returncode
    if proc.returncode:jobs[jid].update(status='FAILED',error='Worker falhou; consulte diagnóstico do job')
    else:jobs[jid].update(status='COMPLETED',progress=100)
   except Exception as ex:jobs[jid].update(status='FAILED',error=type(ex).__name__+': '+str(ex)[:300])
   jobs[jid]['elapsed_seconds']=round(time.time()-started,3)
  pool.submit(work);return jobs[jid]
 @r.get('/jobs/{job_id}')
 def job(job_id):
  if job_id not in jobs:raise HTTPException(404,'job inexistente')
  return jobs[job_id]
'''
s=s[:a]+new+s[b:];p.write_text(s,encoding='utf-8')

