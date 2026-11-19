import io,os,json,uuid,hashlib,threading,time
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI,UploadFile,File,HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse,JSONResponse
from pydantic import BaseModel,Field,ConfigDict
from PIL import Image,ImageOps,UnidentifiedImageError
import numpy as np
from core import validate
from vision import recognize_labels,health as engine_health

app=FastAPI(title='Reconhecimento local DUN / SUN',version='0.2.0')
app.add_middleware(CORSMiddleware,allow_origins=[v.strip() for v in os.getenv('CORS_ORIGINS','https://balancerec.github.io').split(',') if v.strip()],allow_methods=['GET','POST'],allow_headers=['Content-Type'])
DATA=Path(os.getenv('DATA_DIR','data'));DATA.mkdir(parents=True,exist_ok=True)
LOCK=threading.Lock();JOBS_LOCK=threading.Lock();INFERENCE=threading.Lock()
EXECUTOR=ThreadPoolExecutor(max_workers=1,thread_name_prefix='labels-ocr');SLOTS=threading.BoundedSemaphore(2);JOBS={}
Image.MAX_IMAGE_PIXELS=24000000;MAX_BYTES=12*1024*1024
WEB=Path(os.getenv('WEB_DIR',str(Path(__file__).resolve().parent.parent)))

def record_path(rid):
    try:uuid.UUID(rid)
    except ValueError:raise HTTPException(404,'Inspeção inexistente')
    return DATA/(rid+'.json')

def save(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def recognize(raw,rid=None,progress=lambda *args:None):
    try:
        im=Image.open(io.BytesIO(raw))
        if im.width*im.height>24000000:raise HTTPException(422,'Limite de 24 megapixels')
        im.load();im=ImageOps.exif_transpose(im).convert('RGB')
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning):raise HTTPException(422,'Imagem inválida ou grande demais')
    rgb=np.array(im)
    # Bound CPU/memory: never run multiple OCR engines concurrently in this process.
    with INFERENCE:labels,processing=recognize_labels(rgb,progress)
    rid=rid or str(uuid.uuid4());(DATA/(rid+'.original')).write_bytes(raw)
    result=dict(id=rid,schema_version='1.1',created_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest(),processing=processing,labels=labels,corrections=[])
    save(record_path(rid),result);return result

async def read_upload(image):
    try:raw=await image.read(MAX_BYTES+1)
    finally:await image.close()
    if len(raw)>MAX_BYTES:raise HTTPException(413,'Limite de 12 MB')
    if not raw:raise HTTPException(422,'Arquivo vazio')
    return raw

@app.get('/health')
def health():
    try:result=engine_health()
    except Exception:return JSONResponse(status_code=503,content={'status':'error','detail':'Motor OCR indisponível'})
    return JSONResponse(status_code=200 if result['status']=='ok' else 503,content=result)

@app.post('/v1/recognize')
async def upload(image:UploadFile=File(...)):
    raw=await read_upload(image)
    if not SLOTS.acquire(blocking=False):raise HTTPException(429,'Fila cheia. Aguarde a leitura em andamento.')
    try:return await run_in_threadpool(recognize,raw)
    except RuntimeError as e:raise HTTPException(503,'Falha ou tempo limite no motor OCR') from e
    finally:SLOTS.release()

class JobRequest(BaseModel):pass

def job_work(jid,raw):
    def progress(percent,message):
        with JOBS_LOCK:JOBS[jid].update(status='PROCESSING',progress=percent,message=message)
    try:
        result=recognize(raw,jid,progress)
        with JOBS_LOCK:JOBS[jid].update(status='COMPLETED',progress=100,message='Leitura concluída; revisão necessária',result=result)
    except Exception as e:
        message=e.detail if isinstance(e,HTTPException) else 'Não foi possível processar a imagem. Consulte os logs locais.'
        with JOBS_LOCK:JOBS[jid].update(status='FAILED',message=message)
        import logging;logging.exception('Falha no reconhecimento %s',jid)
    finally:SLOTS.release()

@app.post('/v2/jobs',status_code=202)
async def submit(image:UploadFile=File(...)):
    raw=await read_upload(image)
    if not SLOTS.acquire(blocking=False):raise HTTPException(429,'Fila cheia. Aguarde a leitura em andamento.')
    jid=str(uuid.uuid4())
    with JOBS_LOCK:
        for old in list(JOBS):
            if len(JOBS)<100:break
            if JOBS[old]['status'] in ('COMPLETED','FAILED'):del JOBS[old]
        JOBS[jid]=dict(id=jid,status='QUEUED',progress=0,message='Aguardando motor local')
    try:EXECUTOR.submit(job_work,jid,raw)
    except Exception:SLOTS.release();raise
    return dict(id=jid,status='QUEUED',status_url='/v2/jobs/'+jid)

@app.get('/v2/jobs/{jid}')
def job_status(jid:str):
    record_path(jid)
    with JOBS_LOCK:
        job=JOBS.get(jid)
        if job:return dict(job)
    path=record_path(jid)
    if path.exists():return dict(id=jid,status='COMPLETED',progress=100,result=json.loads(path.read_text(encoding='utf-8')))
    raise HTTPException(404,'Processamento inexistente')

@app.get('/v1/inspections/{rid}')
def get(rid:str):
    path=record_path(rid)
    if not path.exists():raise HTTPException(404,'Inspeção inexistente')
    return json.loads(path.read_text(encoding='utf-8'))

class Correction(BaseModel):
    model_config=ConfigDict(strict=True)
    label_index:int=Field(ge=0)
    field_name:str
    value:str|int|None
    operator:str=Field(min_length=1,max_length=120)
    reason:str=Field(min_length=1,max_length=1000)

@app.post('/v1/inspections/{rid}/corrections')
def correct(rid:str,change:Correction):
    if not change.operator.strip() or not change.reason.strip():raise HTTPException(422,'Operador e motivo são obrigatórios')
    with LOCK:
        result=get(rid)
        if change.label_index>=len(result['labels']):raise HTTPException(422,'Etiqueta inexistente')
        label=result['labels'][change.label_index]
        if change.field_name not in label['fields']:raise HTTPException(422,'Campo inexistente')
        numeric={'volume_ml','units_per_case','quantity_boxes','lastro'}
        if change.value is not None and ((change.field_name in numeric and type(change.value) is not int) or (change.field_name not in numeric and type(change.value) is not str)):raise HTTPException(422,'Tipo incorreto para o campo')
        previous=label['fields'][change.field_name];label['fields'][change.field_name]=change.value
        entry=dict(**change.model_dump(),previous=previous,timestamp=datetime.now(timezone.utc).isoformat());result['corrections'].append(entry)
        label.setdefault('field_evidence',[]).append(dict(field_name=change.field_name,raw_text=str(change.value) if change.value is not None else None,normalized_value=change.value,source='MANUAL',confidence=None,bounding_box=None,validation_status='PENDING',correction_history=[entry]))
        structural=[e for e in label['validation']['errors'] if e=='MULTIPLE_BARCODE_VALUES']
        existing=[w for w in label['validation']['warnings'] if not w.startswith('MISSING_')]
        label['validation'],label['pallet']=validate(label['label_type'],label['fields'],label['barcode']['decoded_value'])
        label['validation']['errors'].extend(structural)
        if structural:label['validation']['status']='REJECTED'
        label['validation']['warnings']=list(dict.fromkeys(label['validation']['warnings']+existing))
        key='sscc' if label['label_type']=='SUN' else 'gtin14';decoded=label['barcode']['decoded_value'];value=label['fields'].get(key)
        label['barcode']['current_matches_barcode']=decoded==value if decoded and value else None
        # Initial OCR and its comparison remain immutable after manual corrections.
        save(record_path(rid),result)
        with JOBS_LOCK:
            if rid in JOBS:JOBS[rid]['result']=result
        return result

@app.get('/',include_in_schema=False)
def page():return FileResponse(WEB/'index.html',headers={'Cache-Control':'no-cache'})
@app.get('/backend-client.js',include_in_schema=False)
def client():return FileResponse(WEB/'backend-client.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
@app.get('/docs/etiquetas-dun-sun.svg',include_in_schema=False)
def diagram():return FileResponse(WEB/'docs'/'etiquetas-dun-sun.svg',media_type='image/svg+xml')
