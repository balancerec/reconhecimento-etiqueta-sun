import json,sys,hashlib,time,os,traceback
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageOps
cfg=json.loads(Path(sys.argv[1]).read_text());root=Path(cfg['root']);out=Path(cfg['out']);out.mkdir(parents=True,exist_ok=True);events=[];t0=time.perf_counter()
def log(stage,status,**kw):
 e={'stage':stage,'status':status,'elapsed_seconds':round(time.perf_counter()-t0,4),**kw};events.append(e);(out/'worker-events.json').write_text(json.dumps(events,indent=2),encoding='utf-8');print(json.dumps(e),flush=True)
def step(name,fn):
 t=time.perf_counter()
 try:
  val=fn();log(name,'COMPLETED',duration=round(time.perf_counter()-t,3));return val
 except Exception as ex:log(name,'FAILED',error=repr(ex));raise
try:
 log('startup','RUNNING',pid=os.getpid());p=cfg['photo'];src=Path(p['path']);
 def load():
  im=np.array(ImageOps.exif_transpose(Image.open(src)).convert('RGBA'));box=None
  sid=cfg.get('segmentation_id')
  if sid:
   folder=root/'data/segmentations'/p['id'];mask=cv2.imread(str(folder/(sid+'.mask.png')),0)
   if mask is None:raise ValueError('segmentation mask absent')
   ys,xs=np.where(mask>0)
   if not len(xs):raise ValueError('segmentation mask empty')
   box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)];im=im[box[1]:box[3],box[0]:box[2]].copy();im[:,:,3]=mask[box[1]:box[3],box[0]:box[2]]
  return im,box
 im,box=step('load_image',load);h,w=im.shape[:2];q=cfg['params'];alpha=im[:,:,3];rgb=im[:,:,:3].copy();stages={}
 def save(name,a):
  path=out/(name+'.png');b=cv2.cvtColor(a,cv2.COLOR_RGBA2BGRA) if a.ndim==3 and a.shape[2]==4 else cv2.cvtColor(a,cv2.COLOR_RGB2BGR) if a.ndim==3 else a
  if not cv2.imwrite(str(path),b):raise IOError('image write failed '+name)
  stages[name]=str(path);return path
 step('export_original',lambda:save('original',im))
 def denoise():
  v=q['denoise'];return cv2.cvtColor(cv2.fastNlMeansDenoisingColored(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),None,1+v*.11,1+v*.11,7,21),cv2.COLOR_BGR2RGB) if v else rgb
 rgb=step('denoising',denoise);step('save_denoised',lambda:save('denoised',rgb))
 def deblur():
  v=q['deblur'];blur=cv2.GaussianBlur(rgb,(0,0),.6+v*.012);return np.clip(rgb.astype(np.float32)+(v/100*.8)*(rgb.astype(np.float32)-blur.astype(np.float32)),0,255).astype(np.uint8)
 rgb=step('deblur_unsharp',deblur);step('save_deblurred',lambda:save('deblurred',rgb))
 def clahe():
  v=q['clahe'];lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB);l,a,b=cv2.split(lab);c=cv2.createCLAHE(clipLimit=1+v*.07,tileGridSize=(8,8)).apply(l);l=cv2.addWeighted(l,1-v/100,c,v/100,0);return cv2.cvtColor(cv2.merge([l,a,b]),cv2.COLOR_LAB2RGB)
 rgb=step('clahe',clahe);step('save_clahe',lambda:save('clahe',rgb))
 def sharpen():
  sm=cv2.GaussianBlur(rgb,(0,0),1.1);v=q['sharpness'];return np.clip(rgb.astype(np.float32)+(v/100*1.3)*(rgb.astype(np.float32)-sm.astype(np.float32)),0,255).astype(np.uint8)
 rgb=step('sharpen',sharpen);step('save_sharpen',lambda:save('sharpened',rgb))
 def tone():
  a=np.clip((rgb.astype(np.float32)-127.5)*q['contrast']+127.5+q['brightness'],0,255).astype(np.uint8);h=cv2.cvtColor(a,cv2.COLOR_RGB2HSV);h[:,:,1]=np.clip(h[:,:,1].astype(np.float32)*q['saturation'],0,255).astype(np.uint8);return cv2.cvtColor(h,cv2.COLOR_HSV2RGB)
 rgb=step('brightness_contrast_saturation',tone);rest=np.dstack((rgb,alpha));path=step('export_restored',lambda:save('restored',rest))
 def barcode():
  import zxingcpp
  return [{'format':str(x.format),'text':x.text,'bytes':bytes(x.bytes).hex() if x.bytes else None,'position':str(x.position)} for x in zxingcpp.read_barcodes(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),try_rotate=True,try_downscale=True)]
 try:bar=step('zxing_cpp',barcode)
 except Exception as ex:bar=[{'error':repr(ex)}]
 gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY);quality={'variance_laplacian':float(cv2.Laplacian(gray,cv2.CV_64F).var()),'mean_luminance':float(gray.mean()),'edge_density':float(np.mean(cv2.Canny(gray,80,160)>0))};log('quality_metrics','COMPLETED',dimensions=[w,h]);result={'schema_version':'SUN-V2.7.1','processing_id':cfg['id'],'image_id':p['id'],'copy_id':cfg.get('copy_id'),'segmentation_id':cfg.get('segmentation_id'),'crop_box_original':box,'original_sha256':cfg['original_sha256'],'derivative_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'parameters':q,'stage_paths':stages,'quality':quality,'barcode_restored':bar,'ocr_status':'pending','backend':{'image_processing':'OpenCV CPU','cuda_used':False},'events':events,'warnings':['Deblur is conservative unsharp masking; no PSF/deconvolution.']};tmp=out/'result.json.tmp';tmp.write_text(json.dumps(result,indent=2),encoding='utf-8');json.loads(tmp.read_text());tmp.replace(out/'result.json');log('result_json','COMPLETED')
except Exception as ex:
 log('worker','FAILED',error=repr(ex),traceback=traceback.format_exc());raise

