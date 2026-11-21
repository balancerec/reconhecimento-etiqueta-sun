from pathlib import Path
import sys,json
from PIL import Image,ImageOps
config=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'));out=Path(config['output']);out.parent.mkdir(parents=True,exist_ok=True)
with Image.open(config['input']) as im:ImageOps.exif_transpose(im).convert('RGB').save(out,format='PNG')

