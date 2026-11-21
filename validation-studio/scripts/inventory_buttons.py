import re,json
from pathlib import Path
r=Path(__file__).resolve().parents[1];h=(r/'frontend/validation-studio/index.html').read_text(encoding='utf-8-sig');j=(r/'frontend/validation-studio/app.js').read_text(encoding='utf-8-sig');controls=[]
for m in re.finditer(r'<button\b([^>]*)>(.*?)</button>',h,re.S):
 a,label=m.groups();id=re.search(r'id="([^"]+)"',a);controls.append({'id':id.group(1) if id else None,'label':re.sub(r'\s+',' ',re.sub('<.*?>','',label)).strip(),'handler_declared_in_js':bool(id and id.group(1) in j)})
(r/'V272-BUTTON-INVENTORY.json').write_text(json.dumps(controls,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(controls,ensure_ascii=False))

