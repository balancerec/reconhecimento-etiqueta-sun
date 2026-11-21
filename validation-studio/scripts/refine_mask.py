import json,sys,cv2,numpy as np
from pathlib import Path
from PIL import Image,ImageOps
c=json.loads(Path(sys.argv[1]).read_text());im=np.array(ImageOps.exif_transpose(Image.open(c['input'])).convert('RGB'));h,w=im.shape[:2];mask=np.zeros((h,w),np.uint8);p=np.array(c['polygon'],np.int32);cv2.fillPoly(mask,[p],255);rgba=cv2.cvtColor(im,cv2.COLOR_RGB2RGBA);rgba[:,:,3]=mask;cv2.imwrite(c['mask'],mask);cv2.imwrite(c['rgba'],cv2.cvtColor(rgba,cv2.COLOR_RGBA2BGRA))

