import cv2,glob,json,os
from pathlib import Path
from PIL import Image,ImageOps
# runs in the GPU OCR venv, which contains Pillow/OpenCV
root=Path(os.environ['TEMP'])/'sun-v26-studio-20261120-01';out=[]
for f in glob.glob(str(root/'data/segmentations'/'*'/'*.rgba.png')):
 q=Path(f);sid=q.name.split('.')[0];pid=q.parent.name;meta=json.loads((q.parent/(sid+'.json')).read_text());orig=ImageOps.exif_transpose(Image.open(meta.get('source_path',meta.get('input_path','')))).convert('RGBA') if meta.get('source_path') else None
 rgba=cv2.imread(f,cv2.IMREAD_UNCHANGED);a=rgba[:,:,3];out.append({'file':str(q.relative_to(root)),'size':[rgba.shape[1],rgba.shape[0]],'alpha_minmax':[int(a.min()),int(a.max())],'transparent_pixels':int((a==0).sum()),'opaque_pixels':int((a>0).sum())})
print(json.dumps(out[-5:]))

