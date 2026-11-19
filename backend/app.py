import io, os, json, uuid, hashlib, threading
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError
import numpy as np
import cv2, pytesseract, zxingcpp
from core import parse, validate, gs1
app=FastAPI(title='Reconhecimento DUN / SUN',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=[v.strip() for v in os.getenv('CORS_ORIGINS','https://balancerec.github.io,http://localhost:8000,http://127.0.0.1:8000').split(',') if v.strip()],allow_methods=['GET','POST'],allow_headers=['Content-Type'])
DATA=Path(os.getenv('DATA_DIR','data')); DATA.mkdir(parents=True,exist_ok=True)
LOCK=threading.Lock()
Image.MAX_IMAGE_PIXELS=24000000
MAX_BYTES=12*1024*1024

def record_path(rid):
    try: uuid.UUID(rid)
    except ValueError: raise HTTPException(404,'Inspecao inexistente')
    return DATA/(rid+'.json')
def save(path,data):
    tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(path)
def recognize(raw):
    try:
        im=Image.open(io.BytesIO(raw)); im.load(); im=ImageOps.exif_transpose(im).convert('RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):raise HTTPException(422,'Imagem invalida ou grande demais')
    rgb=np.array(im); h,w=rgb.shape[:2]
    # Blue SUN regions are isolated before OCR, preventing cross-label field mixing.
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    mask=cv2.inRange(hsv,np.array([75,50,35]),np.array([135,255,255]))
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((15,15),np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    regions=[]
    for contour in sorted(contours,key=cv2.contourArea,reverse=True):
        x,y,rw,rh=cv2.boundingRect(contour)
        if rw*rh>w*h*.07 and min(rw,rh)>100:regions.append((x,y,rw,rh))
    if not regions:regions=[(0,0,w,h)]
    labels=[]
    for x,y,rw,rh in regions[:10]:
        crop=rgb[y:y+rh,x:x+rw]; best=None
        for angle in (0,90,180,270):
            oriented=np.array(Image.fromarray(crop).rotate(angle,expand=True))
            gray=cv2.cvtColor(oriented,cv2.COLOR_RGB2GRAY)
            gray=cv2.createCLAHE(2.0,(8,8)).apply(gray)
            data=pytesseract.image_to_data(gray,lang='por+eng',config='--psm 6',output_type=pytesseract.Output.DICT,timeout=25)
            words=[(s,float(c)) for s,c in zip(data['text'],data['conf']) if s.strip() and float(c)>=0]
            text=' '.join(s for s,c in words)
            kind,fields=parse(text)
            score=sum(v is not None for v in fields.values())*100+sum(c for s,c in words)/max(1,len(words))
            if best is None or score>best[0]:best=(score,angle,oriented,data,text,kind,fields)
        _,angle,oriented,data,text,kind,fields=best
        bars=zxingcpp.read_barcodes(oriented)
        bar_records=[dict(raw_value=b.text,symbology=str(b.format)) for b in bars]
        candidates=[]
        for b in bars:
            value=b.text.removeprefix(']C1')
            if value.startswith('(00)'):value=value[4:]
            elif len(value)==20 and value.startswith('00'):value=value[2:]
            if value.isdigit() and len(value)==(18 if kind=='SUN' else 14):candidates.append(value)
        decoded=candidates[0] if len(set(candidates))==1 else None
        validation,pallet=validate(kind,fields,decoded)
        if len(set(candidates))>1:validation['errors'].append('MULTIPLE_BARCODE_VALUES'); validation['status']='REJECTED'
        if len(regions)==1 and regions[0]==(0,0,w,h):validation['warnings'].append('FULL_IMAGE_FALLBACK_CHECK_LABEL_SEPARATION')
        evidence=[dict(raw_text=s,confidence=float(c)/100,bounding_box=[int(data['left'][i]),int(data['top'][i]),int(data['width'][i]),int(data['height'][i])],source='OCR') for i,(s,c) in enumerate(zip(data['text'],data['conf'])) if s.strip() and float(c)>=0]
        labels.append(dict(schema_version='1.0',label_type=kind,classification=dict(confidence=None,evidence=['HEURISTIC_FIELD_MARKERS']),image=dict(region=[x,y,rw,rh],orientation_degrees=angle,coordinate_system='OCR boxes refer to rotated crop'),fields=fields,raw_text=text,ocr_evidence=evidence,barcode=dict(decoded_value=decoded,check_digit_valid=gs1(decoded) if decoded else None,ocr_matches_barcode=decoded==fields.get('sscc' if kind=='SUN' else 'gtin14') if decoded and fields.get('sscc' if kind=='SUN' else 'gtin14') else None,all_decoded=bar_records),pallet=pallet,validation=validation))
    rid=str(uuid.uuid4()); (DATA/(rid+'.original')).write_bytes(raw)
    result=dict(id=rid,created_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest(),labels=labels,corrections=[])
    save(record_path(rid),result); return result

@app.get('/health')
def health():return {'status':'ok','ocr':str(pytesseract.get_tesseract_version())}
@app.post('/v1/recognize')
async def upload(image:UploadFile=File(...)):
    raw=await image.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise HTTPException(413,'Limite de 12 MB')
    try:return await run_in_threadpool(recognize,raw)
    except RuntimeError as e:raise HTTPException(503,'OCR indisponivel ou tempo limite excedido') from e
@app.get('/v1/inspections/{rid}')
def get(rid:str):
    path=record_path(rid)
    if not path.exists():raise HTTPException(404,'Inspecao inexistente')
    return json.loads(path.read_text(encoding='utf-8'))
class Correction(BaseModel):
    label_index:int=Field(ge=0)
    field_name:str
    value:str|int|None
    operator:str=Field(min_length=1,max_length=120)
    reason:str=Field(min_length=1,max_length=1000)
@app.post('/v1/inspections/{rid}/corrections')
def correct(rid:str,change:Correction):
    with LOCK:
        result=get(rid)
        if change.label_index>=len(result['labels']):raise HTTPException(422,'Etiqueta inexistente')
        label=result['labels'][change.label_index]
        if change.field_name not in label['fields']:raise HTTPException(422,'Campo inexistente')
        numeric={'volume_ml','units_per_case','quantity_boxes','lastro'}
        if change.value is not None and ((change.field_name in numeric and type(change.value) is not int) or (change.field_name not in numeric and type(change.value) is not str)):raise HTTPException(422,'Tipo incorreto para o campo')
        previous=label['fields'][change.field_name]
        label['fields'][change.field_name]=change.value
        result['corrections'].append(dict(**change.model_dump(),previous=previous,timestamp=datetime.now(timezone.utc).isoformat()))
        label['validation'],label['pallet']=validate(label['label_type'],label['fields'],label['barcode']['decoded_value'])
        key='sscc' if label['label_type']=='SUN' else 'gtin14'
        decoded=label['barcode']['decoded_value']; value=label['fields'].get(key)
        label['barcode']['ocr_matches_barcode']=decoded==value if decoded and value else None
        save(record_path(rid),result)
        return result

WEB=Path(os.getenv('WEB_DIR', str(Path(__file__).resolve().parent.parent)))
@app.get('/',include_in_schema=False)
def page():return FileResponse(WEB/'index.html')
@app.get('/backend-client.js',include_in_schema=False)
def client():return FileResponse(WEB/'backend-client.js',media_type='text/javascript')
@app.get('/docs/etiquetas-dun-sun.svg',include_in_schema=False)
def diagram():return FileResponse(WEB/'docs'/'etiquetas-dun-sun.svg',media_type='image/svg+xml')
