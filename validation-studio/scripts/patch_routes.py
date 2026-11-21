from pathlib import Path
p=Path(__file__).resolve().parents[1]/'vision'/'api'/'app.py';s=p.read_text(encoding='utf-8')
if 'from vision.api.segmentation_routes import create_router' not in s:s=s.replace('from vision.validation.annotation_models import AnnotationRequest','from vision.validation.annotation_models import AnnotationRequest\nfrom vision.api.segmentation_routes import create_router')
needle=" app.mount('/',StaticFiles(directory=root/'frontend/validation-studio',html=True),name='studio')"
line=" app.include_router(create_router(root,svc,GPU,root/'scripts/segment_label.py'))\n"+needle
if "app.include_router(create_router(" not in s:
 if needle not in s:raise SystemExit('mount marker missing')
 s=s.replace(needle,line)
p.write_text(s,encoding='utf-8')

