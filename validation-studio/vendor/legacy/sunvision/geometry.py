from pathlib import Path
import hashlib
import cv2
import numpy as np
from PIL import Image,ImageOps

def transform_points(points,matrix):
    return cv2.perspectiveTransform(np.asarray(points,dtype=np.float32).reshape(1,-1,2),np.asarray(matrix,dtype=np.float64))[0].tolist()
def order_quad(points):
    pts=np.asarray(points,dtype=np.float32).reshape(4,2)
    if not np.isfinite(pts).all() or len(np.unique(pts,axis=0))!=4 or len(cv2.convexHull(pts))!=4: raise ValueError('Degenerate quadrilateral')
    center=pts.mean(axis=0); angles=np.arctan2(pts[:,1]-center[1],pts[:,0]-center[0]); ordered=pts[np.argsort(angles)]
    ordered=np.roll(ordered,-int(np.argmin(ordered.sum(axis=1))),axis=0)
    if abs(cv2.contourArea(ordered))<1: raise ValueError('Degenerate quadrilateral area')
    return ordered
class ImageLoader:
    def __call__(self,path):
        path=Path(path); raw=path.read_bytes()
        with Image.open(path) as im: image=np.asarray(ImageOps.exif_transpose(im).convert('RGB'))
        return cv2.cvtColor(image,cv2.COLOR_RGB2BGR),{'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'coordinate_space':'EXIF-normalized original pixels','width':image.shape[1],'height':image.shape[0]}
class LabelDetector:
    """Heuristic region proposals; not a trained SUN detector. No claim of recall."""
    def __init__(self,min_fraction=.008,max_fraction=.96,max_regions=12): self.min_fraction=min_fraction; self.max_fraction=max_fraction; self.max_regions=max_regions
    def __call__(self,image,manual_quads=None):
        h,w=image.shape[:2]
        if manual_quads is not None:
            return [{'id':f'label-{i}','quad':order_quad(q).tolist(),'method':'manual_roi','detection_confidence':None} for i,q in enumerate(manual_quads)],[]
        small=cv2.resize(image,(max(1,int(w*min(1,1400/max(w,h)))),max(1,int(h*min(1,1400/max(w,h)))))); scale=w/small.shape[1]
        hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
        masks=[('blue_label',cv2.inRange(hsv,(80,70,45),(135,255,255))),('bright_label',cv2.inRange(hsv,(0,0,150),(180,105,255)))]
        proposals=[]
        for kind,mask in masks:
            mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(9,9)))
            contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area=cv2.contourArea(contour)*scale**2
                if not self.min_fraction*w*h<=area<=self.max_fraction*w*h: continue
                perimeter=cv2.arcLength(contour,True); approx=cv2.approxPolyDP(contour,.025*perimeter,True)
                proposal_kind=kind
                if len(approx)==4 and cv2.isContourConvex(approx):
                    quad=order_quad(approx.reshape(4,2)*scale)
                else:
                    rect_approx=cv2.minAreaRect(contour); rw0,rh0=rect_approx[1]
                    if min(rw0,rh0)<=0 or cv2.contourArea(contour)/(rw0*rh0)<.65: continue
                    quad=order_quad(cv2.boxPoints(rect_approx)*scale); proposal_kind=kind+'_rotated_rect_approximation'
                rect=cv2.minAreaRect(quad); rw,rh=rect[1]
                if min(rw,rh)<45 or max(rw,rh)/min(rw,rh)>7: continue
                proposals.append({'quad':quad.tolist(),'method':proposal_kind,'area':area,'detection_confidence':None})
        kept=[]
        for proposal in sorted(proposals,key=lambda x:x['area'],reverse=True):
            p=np.asarray(proposal['quad'],np.float32); area=abs(cv2.contourArea(p)); overlap=False
            for other in kept:
                q=np.asarray(other['quad'],np.float32); intersection,_=cv2.intersectConvexConvex(p,q); union=area+abs(cv2.contourArea(q))-intersection
                if (union>0 and intersection/union>.5) or intersection/max(1,min(area,abs(cv2.contourArea(q))))>.85: overlap=True; break
            if not overlap: kept.append(proposal)
        issues=[]
        if len(kept)>self.max_regions: issues.append({'code':'region_limit','detected':len(kept),'processed':self.max_regions}); kept=kept[:self.max_regions]
        if not kept:
            kept=[{'quad':[[0,0],[w-1,0],[w-1,h-1],[0,h-1]],'method':'whole_image_fallback','detection_confidence':None}]; issues.append({'code':'no_label_proposal_whole_image_fallback'})
        for i,p in enumerate(kept): p['id']=f'label-{i}'
        return kept,issues
class PerspectiveCorrector:
    def __call__(self,image,quad):
        q=order_quad(quad); tl,tr,br,bl=q
        w=max(2,int(round(max(np.linalg.norm(tr-tl),np.linalg.norm(br-bl))))); h=max(2,int(round(max(np.linalg.norm(bl-tl),np.linalg.norm(br-tr)))))
        target=np.asarray([[0,0],[w-1,0],[w-1,h-1],[0,h-1]],np.float32); matrix=cv2.getPerspectiveTransform(q,target)
        if abs(np.linalg.det(matrix))<1e-12: raise ValueError('Singular perspective transform')
        return cv2.warpPerspective(image,matrix,(w,h)),matrix
class OrientationNormalizer:
    @staticmethod
    def rotate(image,k):
        h,w=image.shape[:2]; matrices=[[[1,0,0],[0,1,0],[0,0,1]],[[0,1,0],[-1,0,w-1],[0,0,1]],[[-1,0,w-1],[0,-1,h-1],[0,0,1]],[[0,-1,h-1],[1,0,0],[0,0,1]]]
        return np.ascontiguousarray(np.rot90(image,k)),np.asarray(matrices[k],np.float64)
    def __call__(self,image,ocr):
        import re
        runs=[]
        for k in range(4):
            view,rotation=self.rotate(image,k); blocks=ocr(view)
            anchors=sum(bool(re.search(r'\b(?:ITEM|QTDE|LASTRO|VALIDADE|ENTRADA|SSCC)\b',b['text'].upper())) for b in blocks)
            score=anchors*3+sum(b['confidence']*min(len(b['text']),40)/40 for b in blocks)
            runs.append({'angle_ccw':90*k,'rotation':rotation.tolist(),'score':score,'blocks':blocks,'image':view})
        chosen=max(runs,key=lambda r:r['score'])
        return chosen,runs

