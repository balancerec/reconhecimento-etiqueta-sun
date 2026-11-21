from pathlib import Path
import secrets,subprocess,threading,uuid,json
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from vision.validation.annotation_service import AnnotationService,ReviewError
from vision.validation.annotation_store import RevisionConflict
from vision.validation.annotation_models import AnnotationRequest
from vision.api.segmentation_routes import create_router
from vision.api.restoration_routes import create_router as create_restoration_router
ROOT=Path(__file__).resolve().parents[2]
GPU=Path.home()/'Pictures/ETIQUETAS/benchmark-sun/.venv/Scripts/python.exe'
def create_app(root=ROOT,db_path=None):
 root=Path(root);svc=AnnotationService(root,db_path);app=FastAPI(title='PRO-ACT Validation Studio V2.6');token=secrets.token_urlsafe(32);jobs={};lock=threading.Lock();app.state.service=svc
 @app.middleware('http')
 async def guard(req,call_next):
  if req.method not in ('GET','HEAD','OPTIONS') and req.headers.get('x-studio-token')!=token:
   from fastapi.responses import JSONResponse
   return JSONResponse({'detail':'Token local invalido'},status_code=403)
  return await call_next(req)
 @app.exception_handler(ReviewError)
 async def review_error(req,exc):
  from fastapi.responses import JSONResponse
  return JSONResponse({'detail':str(exc)},status_code=422)
 @app.exception_handler(RevisionConflict)
 async def conflict(req,exc):
  from fastapi.responses import JSONResponse
  return JSONResponse({'detail':str(exc)},status_code=409)
 @app.exception_handler(KeyError)
 async def missing(req,exc):
  from fastapi.responses import JSONResponse
  return JSONResponse({'detail':str(exc)},status_code=404)
 @app.get('/api/session')
 def session():return {'token':token,'integration_enabled':False,'photo_count':len(svc.photos)}
 @app.get('/api/photos')
 def photos():return svc.listing()
 @app.get('/api/photos/{pid}')
 def photo(pid):return {'photo':svc.photo(pid),'prediction':svc.prediction(pid),'annotation':svc.store.latest(pid),'template':svc.template(pid),'runs':[r['run_id'] for r in svc.predictions(pid)]}
 @app.get('/api/photos/{pid}/image')
 def image(pid):
  p=svc.photo(pid);svc.check_source(p);cache=root/'data/image-cache';cache.mkdir(exist_ok=True);out=cache/(p['sha256']+'.png')
  if not out.exists():
   cfg=cache/(pid+'.json');cfg.write_text(json.dumps({'input':p['path'],'output':str(out)}),encoding='utf-8');subprocess.run([str(GPU),str(root/'scripts/render_image.py'),str(cfg)],check=True,timeout=90,creationflags=0x08000000)
  return FileResponse(out)
 @app.get('/api/photos/{pid}/original')
 def original(pid):
  p=svc.photo(pid);svc.check_source(p);return FileResponse(p['path'],filename=p['name'])
 @app.get('/api/photos/{pid}/history')
 def history(pid):svc.photo(pid);return svc.store.history(pid)
 @app.post('/api/annotations/{action}')
 def save(action:str,body:AnnotationRequest):
  if action not in ('save','approve'):raise HTTPException(404)
  return svc.save(body,approve=action=='approve')
 @app.get('/api/evaluation')
 def evaluation():return svc.evaluation()
 @app.get('/api/audit')
 def audit():return svc.store.audit()
 @app.post('/api/export')
 def export():
  e=svc.export();return {'download':'/api/exports/'+e['path'].name,'sha256':e['sha256'],'annotation_count':e['payload']['annotation_count']}
 @app.get('/api/exports/{name}')
 def download(name):
  if not name.endswith('.json') or not name[:-5].isalnum():raise HTTPException(404)
  p=svc.export_dir/name
  if not p.exists():raise HTTPException(404)
  return FileResponse(p,filename='sun-v26-human-'+name)
 @app.post('/api/photos/{pid}/rectify')
 def rectify(pid,body:dict):
  p=svc.photo(pid);svc.check_source(p);c=next((x for x in body.get('copies',[]) if x.get('copy_id')==body.get('copy_id')),None)
  if not c or len(c.get('polygon_original',[]))!=4:raise HTTPException(422,'Informe exatamente quatro vértices')
  coords=c['polygon_original']
  if any(not(0<=x<=p['width'] and 0<=y<=p['height']) for x,y in coords):raise HTTPException(422,'Vértices fora da imagem')
  jid=uuid.uuid4().hex;directory=root/'evidence'/'rectified';directory.mkdir(parents=True,exist_ok=True);out=directory/(jid+'.png');cfg=directory/(jid+'.json');cfg.write_text(json.dumps({'input':p['path'],'output':str(out),'points':coords,'brightness':body.get('brightness',0),'contrast':body.get('contrast',1),'saturation':body.get('saturation',1)}),encoding='utf-8')
  subprocess.run([str(GPU),str(root/'scripts/rectify_label.py'),str(cfg)],check=True,timeout=120,creationflags=0x08000000);return {'id':jid,'url':'/api/rectified/'+jid+'.png','source_image_sha256':p['sha256'],'polygon_original':coords,'transform':'OpenCV getPerspectiveTransform + warpPerspective'}
 @app.get('/api/rectified/{name}')
 def rectified(name):
  if not name.endswith('.png') or not name[:-4].isalnum():raise HTTPException(404)
  f=root/'evidence'/'rectified'/name
  if not f.exists():raise HTTPException(404)
  return FileResponse(f)
 @app.post('/api/photos/{pid}/recognize')
 def recognize(pid):
  p=svc.photo(pid);svc.check_source(p)
  if not lock.acquire(blocking=False):raise HTTPException(409,'Inference running')
  jid=uuid.uuid4().hex;directory=root/'evidence'/jid;directory.mkdir(parents=True);dest=root/'data/predictions/v26-gpu'/(pid+'--'+jid+'.json');dest.parent.mkdir(exist_ok=True);cfg={'photo':p,'baseline_path':str(root/'data/predictions/v24'/(pid+'.json')),'job_dir':str(directory),'output_path':str(dest)};config=directory/'job.json';config.write_text(json.dumps(cfg),encoding='utf-8');jobs[jid]={'status':'running','photo_id':pid}
  def work():
   try:
    result=subprocess.run([str(GPU),str(root/'scripts/ocr_worker.py'),str(config)],capture_output=True,text=True,timeout=1800,creationflags=0x08000000);(directory/'stdout.txt').write_text(result.stdout,encoding='utf-8');(directory/'stderr.txt').write_text(result.stderr,encoding='utf-8');jobs[jid].update(status='completed' if result.returncode==0 else 'failed',exit_code=result.returncode,evidence=str(directory));svc.store.record_event({'type':'inference','job_id':jid,**jobs[jid]})
   except Exception as ex:jobs[jid].update(status='failed',error=str(ex))
   finally:lock.release()
  threading.Thread(target=work,daemon=True).start();return {'job_id':jid}
 @app.get('/api/jobs/{jid}')
 def job(jid):
  if jid not in jobs:raise HTTPException(404)
  return jobs[jid]
 app.include_router(create_router(root,svc,GPU,root/'scripts/segment_label.py'))
 app.include_router(create_restoration_router(root,svc,GPU,root/'scripts/restoration_worker.py'))
 app.mount('/',StaticFiles(directory=root/'frontend/validation-studio',html=True),name='studio')
 return app
app=create_app()


