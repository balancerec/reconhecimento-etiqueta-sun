from pathlib import Path
import sys,os,json,hashlib,subprocess,copy,re,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'vendor/legacy')]
ACCESS=[]
def guard(event,args):
 if event=='open' and args and isinstance(args[0],(str,bytes)):
  p=os.fsdecode(args[0]).lower().replace('\\','/')
  if '/data/human/' in p or '/evaluation/' in p or p.endswith(('catalog-reference.json','prior-human-reference.json')):raise PermissionError('Human/catalog data forbidden during OCR inference')
  if p.endswith(('.json','.onnx','.jpg','.png')):ACCESS.append(p)
sys.addaudithook(guard)
import cv2,numpy as np
from sunvision.geometry import ImageLoader,transform_points
from sunvision.ocr import OCR
from vision.field_recovery.field_recovery_engine import FieldRecoveryEngine,candidate
from vision.field_recovery.description_reconstructor import reconstruct,normalize
from vision.field_recovery.spatial_field_assigner import valid_value
from vision.field_recovery.candidate_ranker import rank

def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def process(config):
 job=Path(config['job_dir']);base=Path(config['baseline_path']);base_data=json.loads(base.read_text(encoding='utf-8'));image,meta=ImageLoader()(config['photo']['path']);assert meta['sha256']==config['photo']['sha256'];engine=FieldRecoveryEngine();output=engine.process(base_data);ocr=OCR('cuda',job/'profiles');native_inputs=[];raw_evidence=[]
 try:
  for bc,cp in zip(base_data['physical_copies'],output['physical_copies']):
   H=np.asarray(cp['original_to_rectified']);inv=np.linalg.inv(H);q=np.asarray(cp['quad_original']);lens=[np.linalg.norm(q[(i+1)%4]-q[i]) for i in range(4)];bw=round(max(lens[0],lens[2]));bh=round(max(lens[1],lens[3]));w,h=(bh,bw) if cp['coordinate_orientation_applied']%180 else (bw,bh);view=cv2.warpPerspective(image,H,(w,h))
   for idx,roi in enumerate(cp['recovery_rois']):
    field=roi['field'];old=bc['fields'][field];old_rank=rank([candidate(field,c['normalized_value'],c.get('raw_value',c['normalized_value']),cp['copy_id'],c.get('polygon_original'),c['source'],'legacy',c.get('confidence'),cp['coordinate_orientation_applied']) for c in old['candidates']])
    if old_rank['status']=='accepted_candidate':continue
    x,y,xx,yy=roi['box'];patch=view[y:yy,x:xx]
    if patch.size==0:continue
    M=inv@np.array([[1,0,x],[0,1,y],[0,0,1]],float);roi_id=cp['copy_id']+'-'+field+'-'+str(idx);path=job/(roi_id+'.png');cv2.imwrite(str(path),patch);native_inputs.append({'roi_id':roi_id,'field':field,'copy_id':cp['copy_id'],'path':str(path),'matrix':M.tolist(),'orientation':cp['coordinate_orientation_applied']})
    blue=patch[:,:,0];gray=cv2.cvtColor(patch,cv2.COLOR_BGR2GRAY);variants=[('native_roi',patch,1),('scale2',cv2.resize(patch,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC),2),('grayscale',cv2.cvtColor(gray,cv2.COLOR_GRAY2BGR),1),('CLAHE',cv2.cvtColor(cv2.createCLAHE(2,(8,8)).apply(blue),cv2.COLOR_GRAY2BGR),1),('adaptive',cv2.cvtColor(cv2.adaptiveThreshold(blue,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,9),cv2.COLOR_GRAY2BGR),1)]
    for recipe,pixels,scale in variants:
     blocks=ocr(pixels)
     for b in blocks:b['polygon_local']=np.asarray(b['polygon_local']).tolist();b['polygon_original']=transform_points(b['polygon_local'],M@np.diag([1/scale,1/scale,1]))
     evidence_id=hashlib.sha256((roi_id+recipe+json.dumps(blocks,ensure_ascii=True)).encode()).hexdigest()[:20];raw_evidence.append({'evidence_id':evidence_id,'roi_id':roi_id,'copy_id':cp['copy_id'],'field':field,'recipe':recipe,'roi_box_rectified':roi['box'],'anchor':roi['anchor'],'blocks':blocks,'input_pixels':str(path),'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
     for line in reconstruct(blocks):
      text=line['text'];confidence=min((b.get('confidence') or 0) for b in line['blocks']);poly=np.asarray([p for b in line['blocks'] for p in b['polygon_original']],np.float32);polygon=cv2.convexHull(poly).reshape(-1,2).tolist()
      if field=='descricao' or field=='validade_impressa' or valid_value(field,text):cp['fields'][field]['candidates'].append(candidate(field,text,text,cp['copy_id'],polygon,'ocr',recipe,confidence,cp['coordinate_orientation_applied'],[evidence_id],spatial_verified=True))
 finally:save(job/'gpu-proof.json',ocr.close())
 save(job/'native-inputs.json',native_inputs);save(job/'neural-evidence.json',raw_evidence)
 # Independent native Windows OCR is a separate source; no catalog or reference lookup.
 if native_inputs:
  env=dict(os.environ);env['SUN_NATIVE_INPUTS']=str(job/'native-inputs.json');env['SUN_NATIVE_OUTPUT']=str(job/'native-output.json')
  ps=(ROOT/'scripts/native_ocr.ps1').read_text(encoding='utf-8-sig');result=subprocess.run(['powershell.exe','-NoProfile','-Command',ps],env=env,capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));save(job/'native-status.json',{'returncode':result.returncode,'stderr':result.stderr,'backend':'Windows OCR, internal provider unknown; no CUDA claim'})
  if result.returncode==0 and (job/'native-output.json').exists():
   items=json.loads((job/'native-output.json').read_text(encoding='utf-8-sig'));rois={r['roi_id']:r for r in native_inputs}
   for item in items:
    r=rois[item['roi_id']];cp=next(c for c in output['physical_copies'] if c['copy_id']==r['copy_id']);field=r['field']
    for b in item['blocks']:b['polygon_original']=transform_points(b['polygon_local'],r['matrix'])
    for line in reconstruct(item['blocks']):
     text=line['text']
     if field!='descricao' and field!='validade_impressa' and not valid_value(field,text):continue
     polygon=cv2.convexHull(np.float32([p for b in line['blocks'] for p in b['polygon_original']])).reshape(-1,2).tolist();cp['fields'][field]['candidates'].append(candidate(field,text,text,cp['copy_id'],polygon,'windows_ocr','native_pt-BR',None,r['orientation'],['native:'+r['roi_id']],spatial_verified=True))
 for cp in output['physical_copies']:
  for field,data in cp['fields'].items():
   recipes={}
   for c in data['candidates']:
    if c['recipe'] not in ['spatial_context_v26'] and not c['recipe'].startswith('legacy'):recipes.setdefault(c['normalized_value'],set()).add(c['recipe'])
   for c in data['candidates']:
    if c['recipe']=='spatial_context_v26' and recipes and c['normalized_value'] not in recipes:c['spatial_verified']=False;c['verification_note']='global token not confirmed by dedicated ROI; retained as insufficient evidence'
    if c['source']=='ocr' and c['recipe'] in ['native_roi','scale2','grayscale','CLAHE','adaptive'] and c['confidence_raw'] is not None and c['confidence_raw']<.80:c['spatial_verified']=False;c['verification_note']='uncalibrated OCR score below documented recipe eligibility threshold 0.80'
   cp['fields'][field]=rank(data['candidates'])
 output.update(execution='fresh CUDA dedicated-ROI inference plus spatial legacy evidence; native Windows auxiliary when available',input_prediction_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),evidence_root=str(job),neural_evidence=raw_evidence,gpu_proof=str(job/'gpu-proof.json'),access_log=sorted(set(ACCESS)),ground_truth_used=False,catalog_used_for_completion=False)
 return output
if __name__=='__main__':
 config=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'));job=Path(config['job_dir']);job.mkdir(parents=True,exist_ok=True)
 try:save(Path(config['output_path']),process(config))
 except Exception as e:save(job/'error.json',{'error':repr(e),'traceback':traceback.format_exc()});raise

