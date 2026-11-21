from pathlib import Path
import zipfile,json,os
root=Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'AppData/Local')))/'pip'/'Cache'/'http-v2';wanted={'fastapi','starlette','uvicorn','anyio','httpx','pydantic','pydantic-core','typing-extensions','click','h11','sniffio','idna'};found=[];count=0
for p in root.rglob('*.body'):
 count+=1
 try:
  with zipfile.ZipFile(p) as z:
   meta=next((n for n in z.namelist() if n.endswith('.dist-info/METADATA')),None)
   if meta:
    text=z.read(meta).decode('utf-8');name=next((s[6:] for s in text.splitlines() if s.startswith('Name: ')),'').lower().replace('_','-')
    if name in wanted:found.append({'name':name,'version':next((s[9:] for s in text.splitlines() if s.startswith('Version: ')),''),'path':str(p)})
 except (zipfile.BadZipFile,PermissionError,OSError):pass
print(json.dumps({'cache_bodies_scanned':count,'packages':found},indent=2))

