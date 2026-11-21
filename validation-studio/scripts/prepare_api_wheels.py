from pathlib import Path
import zipfile,json,os,shutil,re,hashlib
R=Path(os.environ['TEMP'])/'sun-v26-studio-20261120-01';root=Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'AppData/Local')))/'pip'/'Cache'/'http-v2';names={'fastapi','starlette','uvicorn','anyio','httpx','httpcore','pydantic','pydantic-core','typing-extensions','typing-inspection','annotated-types','annotated-doc','sniffio','idna','click','h11','colorama','certifi','opentelemetry-api','importlib-metadata','zipp'};out=R/'wheelhouse';out.mkdir(exist_ok=True);rows=[]
for p in root.rglob('*.body'):
 try:
  with zipfile.ZipFile(p) as z:
   meta=next((n for n in z.namelist() if n.endswith('.dist-info/METADATA')),None)
   if not meta:continue
   text=z.read(meta).decode('utf-8');name=next((s[6:] for s in text.splitlines() if s.startswith('Name: ')),'').lower().replace('_','-')
   if name not in names:continue
   version=next(s[9:] for s in text.splitlines() if s.startswith('Version: '));wheel=z.read(meta.replace('METADATA','WHEEL')).decode();tags=[s[5:] for s in wheel.splitlines() if s.startswith('Tag: ')];tag=next((t for t in tags if t.startswith('py3-') or ('cp312' in t and t.endswith('win_amd64'))),tags[0]);filename=name.replace('-','_')+'-'+version+'-'+tag+'.whl';dest=out/filename;shutil.copyfile(p,dest);rows.append({'name':name,'version':version,'filename':filename,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'requires_python':next((s[17:] for s in text.splitlines() if s.startswith('Requires-Python: ')),''),'requires_dist':[s[15:] for s in text.splitlines() if s.startswith('Requires-Dist: ')]})
 except (zipfile.BadZipFile,KeyError,OSError):continue
(R/'data/cached-api-wheels.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps([r for r in rows if r['name'] in ['fastapi','uvicorn','starlette','pydantic']],indent=2))


