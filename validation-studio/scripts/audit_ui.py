import re,json
from pathlib import Path
r=Path(__file__).resolve().parents[1];h=(r/'frontend/validation-studio/index.html').read_text(encoding='utf-8-sig');js=(r/'frontend/validation-studio/app.js').read_text(encoding='utf-8-sig');ids=re.findall(r'id="([^"]+)"',h);controls=[]
for i in ids:
 if re.search(r'<(?:button|input|select|a)[^>]*id="'+re.escape(i)+r'"',h):
  m=re.search(r'<(?:button|input|select|a)[^>]*id="'+re.escape(i)+r'"[^>]*>(.*?)</button>',h,re.S);label=re.sub('<.*?>','',m.group(1)).strip() if m else i;event='inline assignment' if re.search(r"\$\(['\"]"+re.escape(i)+r"['\"]\)\.(?:onclick|onchange|oninput)",js) else ('delegated/listener' if re.search(re.escape(i),js) else 'none');controls.append({'control_id':i,'current_label':label,'current_behavior':'handler reference inspected; see audit','event_handler':event,'api_dependency':'see app.js callsite','required_state':'runtime dependent','proposed_location':'contextual toolbar/panel','action':'KEEP/MOVE/CONTEXTUAL'})
(r/'V272-CONTROL-INVENTORY.json').write_text(json.dumps(controls,indent=2),encoding='utf-8')

