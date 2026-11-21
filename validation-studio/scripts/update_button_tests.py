import json
from pathlib import Path
r=Path(__file__).resolve().parents[1];p=r/'V272-BUTTON-TEST-RESULTS.json';d=json.loads(p.read_text());d['results'].insert(6,{'button':'Retificar perspectiva','result':'PASS_API_ONLY','evidence':{'post_http':200,'png_http':200,'content_type':'image/png','browser_preview':'not tested'}});d['results'].append({'button':'Blocos OCR toggle','result':'NOT_BROWSER_TESTED','evidence':'DOM interaction required'});d['results'].append({'button':'Próxima fotografia','result':'NOT_BROWSER_TESTED','evidence':'browser navigation interaction required'});p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')

