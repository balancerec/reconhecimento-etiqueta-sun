from pathlib import Path
import json,uuid,subprocess
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse

def create_router(root,svc,gpu,worker):
 root=Path(root);router=APIRouter(prefix='/api/v261/segmentation',tags=['segmentation'])
 def paths(pid,sid):
  svc.photo(pid)
  if not sid.isalnum():raise HTTPException(404,detail={'code':'invalid_id','message':'Identificador inválido'})
  return root/'data'/'segmentations'/pid/sid
 @router.post('/click')
 def click(body:dict):
  pid=body.get('image_id');
  try:p=svc.photo(pid)
  except KeyError:raise HTTPException(404,detail={'code':'image_not_found','message':'Imagem inexistente'})
  point=body.get('click_original') or {};x=point.get('x');y=point.get('y')
  if not isinstance(x,(int,float)) or not isinstance(y,(int,float)) or not(0<=x<p['width'] and 0<=y<p['height']):raise HTTPException(422,detail={'code':'invalid_click','message':'Coordenada fora da imagem'})
  svc.check_source(p);sid=uuid.uuid4().hex;folder=root/'data'/'segmentations'/pid;folder.mkdir(parents=True,exist_ok=True);base=folder/sid
  cfg={'input':p['path'],'seed':[int(x),int(y)],'mask':str(base.with_suffix('.mask.png')),'rgba':str(base.with_suffix('.rgba.png')),'overlay':str(base.with_suffix('.overlay.png')),'json':str(base.with_suffix('.json'))};cf=base.with_suffix('.request.json');cf.write_text(json.dumps(cfg),encoding='utf-8')
  try:subprocess.run([str(gpu),str(worker),str(cf)],check=True,capture_output=True,text=True,timeout=120,creationflags=0x08000000)
  except subprocess.CalledProcessError as e:raise HTTPException(422,detail={'code':'segmentation_failed','message':e.stderr[-600:] or 'Nenhuma região azul conectada ao clique'})
  out=json.loads(base.with_suffix('.json').read_text());out.update({'segmentation_id':sid,'image_id':pid,'copy_id':body.get('copy_id'),'reviewed':False,'source_sha256':p['sha256']});base.with_suffix('.json').write_text(json.dumps(out),encoding='utf-8');return out
 @router.post('/refine')
 def refine(body:dict):
  base=paths(body.get('image_id'),body.get('segmentation_id'));f=base.with_suffix('.json')
  if not f.exists():raise HTTPException(404,detail={'code':'proposal_not_found','message':'Proposta não encontrada'})
  d=json.loads(f.read_text());poly=body.get('polygon')
  if not isinstance(poly,list) or len(poly)<3:raise HTTPException(422,detail={'code':'invalid_polygon','message':'Polígono requer ao menos três pontos'})
  p=svc.photo(body.get('image_id'));d['contour']=poly;d['polygon']=poly;d['reviewed']=False;d['revision']=int(d.get('revision',0))+1;cfg=base.with_suffix('.refine.json');cfg.write_text(json.dumps({'input':p['path'],'polygon':poly,'mask':str(base.with_suffix('.mask.png')),'rgba':str(base.with_suffix('.rgba.png'))}),encoding='utf-8');subprocess.run([str(gpu),str(root/'scripts/refine_mask.py'),str(cfg)],check=True,capture_output=True,text=True,timeout=90,creationflags=0x08000000);tmp=f.with_suffix('.json.tmp');tmp.write_text(json.dumps(d),encoding='utf-8');tmp.replace(f);return d
 @router.post('/confirm')
 def confirm(body:dict):
  base=paths(body.get('image_id'),body.get('segmentation_id'));f=base.with_suffix('.json')
  if not f.exists():raise HTTPException(404,detail={'code':'proposal_not_found','message':'Proposta não encontrada'})
  d=json.loads(f.read_text());d['reviewed']=True;d['status']='HUMAN_CONFIRMED';d['copy_id']=body.get('copy_id',d.get('copy_id'));tmp=f.with_suffix('.json.tmp');tmp.write_text(json.dumps(d),encoding='utf-8');tmp.replace(f);return {'confirmed':True,'proposal':d,'approval_of_annotation':False}
 @router.get('/{image_id}/{copy_id}/png')
 def png(image_id,copy_id):
  base=paths(image_id,copy_id);f=base.with_suffix('.rgba.png')
  if not f.exists():raise HTTPException(404,detail={'code':'png_not_found','message':'PNG isolado não encontrado'})
  return FileResponse(f,media_type='image/png')
 @router.get('/{image_id}/{copy_id}')
 def get(image_id,copy_id):
  base=paths(image_id,copy_id);f=base.with_suffix('.json')
  if not f.exists():raise HTTPException(404,detail={'code':'proposal_not_found','message':'Proposta não encontrada'})
  return json.loads(f.read_text())
 return router


