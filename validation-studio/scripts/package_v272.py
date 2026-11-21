from pathlib import Path
import hashlib,json,zipfile
r=Path(__file__).resolve().parents[1];files=['frontend/validation-studio/index.html','frontend/validation-studio/styles.css','frontend/validation-studio/app.js','vision/api/app.py','vision/api/segmentation_routes.py','vision/api/restoration_routes.py','scripts/segment_label.py','scripts/restoration_worker.py']
manifest={f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in files};(r/'V272-MANIFEST-SHA256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');zipf=r/'V272-unified-workspace.zip';reports=['V272-UI-AUDIT.md','V272-CONTROL-INVENTORY.json','V272-UX-ARCHITECTURE.md','V272-STATE-MACHINE.md','V272-COMPONENT-MAPPING.md','V272-RESPONSIVE-VALIDATION.md','V272-BROWSER-VALIDATION.md','V272-REGRESSION-RESULTS.json','V272-PRESERVATION-AUDIT.json','V272-MANIFEST-SHA256.json'];
with zipfile.ZipFile(zipf,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files+reports:
  p=r/f
  if p.exists():z.write(p,f)
with zipfile.ZipFile(zipf) as z:bad=z.testzip()
print(json.dumps({'zip':str(zipf),'crc_ok':bad is None,'bytes':zipf.stat().st_size,'manifest_files':len(manifest)}))

