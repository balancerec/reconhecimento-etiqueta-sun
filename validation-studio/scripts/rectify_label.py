import sys,json
from pathlib import Path
import cv2,numpy as np
cfg=json.loads(Path(sys.argv[1]).read_text());im=cv2.imread(cfg['input']);p=np.array(cfg['points'],np.float32);center=p.mean(axis=0);angles=np.arctan2(p[:,1]-center[1],p[:,0]-center[0]);p=p[np.argsort(angles)];start=np.argmin(p.sum(axis=1));p=np.roll(p,-start,axis=0);d=[np.linalg.norm(p[i]-p[(i+1)%4]) for i in range(4)];w=max(64,int(max(d[0],d[2])));h=max(64,int(max(d[1],d[3])));dst=np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]],np.float32);M=cv2.getPerspectiveTransform(p,dst);out=cv2.warpPerspective(im,M,(w,h),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE);b=float(cfg.get('brightness',0));c=float(cfg.get('contrast',1));sat=float(cfg.get('saturation',1));out=cv2.convertScaleAbs(out,alpha=c,beta=b);hsv=cv2.cvtColor(out,cv2.COLOR_BGR2HSV);hsv[:,:,1]=np.clip(hsv[:,:,1].astype(np.float32)*sat,0,255).astype(np.uint8);out=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR);cv2.imwrite(cfg['output'],out)


