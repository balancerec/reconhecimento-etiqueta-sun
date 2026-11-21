"""Independent industrial-style barcode search using measured pixels only.
Not an implementation of any vendor's proprietary decoder. No expected payload input.
"""
import time,hashlib,collections
from pathlib import Path
import cv2,numpy as np,zxingcpp
from sunvision.geometry import ImageLoader,LabelDetector,PerspectiveCorrector,transform_points
from sun_validator import sscc_from_gs1,validate_sscc

def local_normalize(gray):
    background=cv2.GaussianBlur(gray,(0,0),max(5,min(gray.shape)/25))
    return np.clip(gray.astype(np.float32)*180/np.maximum(background,15),0,255).astype(np.uint8)
def quality(image):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if image.ndim==3 else image; hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV) if image.ndim==3 else None
    return {'laplacian_variance':float(cv2.Laplacian(gray,cv2.CV_64F).var()),'saturated_fraction':float((gray>=250).mean()),'dynamic_range_p98_p02':float(np.percentile(gray,98)-np.percentile(gray,2)),'low_saturation_high_value_fraction':float(((hsv[:,:,1]<35)&(hsv[:,:,2]>245)).mean()) if hsv is not None else None,'calibrated_acceptance_thresholds':False}

def transforms(image):
    yield 'gray',cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    yield 'blue_channel',image[:,:,0]
    g=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    yield 'local_normalization',local_normalize(g)
    yield 'blue_local_normalization',local_normalize(image[:,:,0])
    yield 'clahe',cv2.createCLAHE(2,(8,8)).apply(g)
    for gamma in [.65,1.5]: yield 'gamma_'+str(gamma),cv2.LUT(g,np.uint8(np.clip((np.arange(256)/255)**gamma*255,0,255)))

def barcode_regions(image):
    """Gradient morphology locates parallel line texture, without reading payload."""
    h,w=image.shape[:2]; scale=min(1,1400/max(h,w)); small=cv2.resize(image,(max(2,round(w*scale)),max(2,round(h*scale)))); g=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    boxes=[]
    for axis in [0,1]:
        dx=cv2.Sobel(g,cv2.CV_32F,1,0,ksize=-1);dy=cv2.Sobel(g,cv2.CV_32F,0,1,ksize=-1); gradient=cv2.convertScaleAbs(dx-dy if axis==0 else dy-dx); gradient=cv2.GaussianBlur(gradient,(7,7),0); _,mask=cv2.threshold(gradient,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        kernel=cv2.getStructuringElement(cv2.MORPH_RECT,(31,9) if axis==0 else (9,31)); mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kernel); mask=cv2.erode(mask,None,iterations=2); mask=cv2.dilate(mask,None,iterations=3)
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            rect=cv2.minAreaRect(contour); a,b=rect[1]
            if a*b<.002*g.size or min(a,b)<12 or max(a,b)/max(1,min(a,b))<1.5: continue
            center,size,angle=rect; expanded=(center,(size[0]*1.18,size[1]*1.3),angle); boxes.append((cv2.contourArea(contour),cv2.boxPoints(expanded)/scale))
    return [q.tolist() for _,q in sorted(boxes,key=lambda x:x[0],reverse=True)[:8]]

class IndustrialBarcodeReader:
    def __init__(self,max_attempts=320,max_seconds=90): self.max_attempts=max_attempts; self.max_seconds=max_seconds
    def read(self,path):
        image,meta=ImageLoader()(path); start=time.perf_counter(); observations=[]; attempts=[]; errors=[]; budget=False
        def attempt(gray,name,H,source_quad=None):
            nonlocal budget
            if len(attempts)>=self.max_attempts or time.perf_counter()-start>self.max_seconds: budget=True; return
            attempt_record={'method':name,'shape':list(gray.shape),'view_sha256':hashlib.sha256(gray.tobytes()).hexdigest()}; attempts.append(attempt_record)
            # Padding establishes quiet-zone pixels; it never supplies missing bar/module data.
            m=max(20,round(gray.shape[1]*.06)); padded=cv2.copyMakeBorder(gray,20,20,m,m,cv2.BORDER_CONSTANT,value=255)
            try:
                for barcode in zxingcpp.read_barcodes(padded,formats=zxingcpp.BarcodeFormat.Code128,try_rotate=True,try_downscale=True):
                    values=[v for v in sscc_from_gs1(barcode.text) if validate_sscc(v)['valid']]
                    p=barcode.position; points=[[p.top_left.x-m,p.top_left.y-20],[p.top_right.x-m,p.top_right.y-20],[p.bottom_right.x-m,p.bottom_right.y-20],[p.bottom_left.x-m,p.bottom_left.y-20]]
                    observations.append({'text':barcode.text,'bytes_hex':barcode.bytes.hex(),'format':str(barcode.format),'valid_sscc':values,'method':name,'polygon_original':transform_points(points,H) if source_quad is None else None,'source_evidence_quad':source_quad,'coordinate_mapping':'exact_homography' if source_quad is None else 'profile_aggregation_noninvertible_source_band_recorded','source_is_single_image':True})
            except Exception as e: errors.append({'method':name,'error':str(e)})
        h,w=image.shape[:2]; views=[('global',image,np.eye(3))]
        proposals,_=LabelDetector()(image)
        for p in proposals:
            if not p['method'].startswith('blue_label'): continue
            try: view,H=PerspectiveCorrector()(image,p['quad']); views.append(('label_'+p['id'],view,np.linalg.inv(H)))
            except ValueError: pass
        for i,quad in enumerate(barcode_regions(image)):
            try: view,H=PerspectiveCorrector()(image,quad); views.append(('parallel_bars_'+str(i),view,np.linalg.inv(H)))
            except ValueError: pass
        # Direct paths first, so exhaustive profile paths cannot mask raw successful reads.
        for name,view,H in views:
            for method,gray in transforms(view):
                attempt(gray,name+'/'+method,H)
                if budget: break
            if budget: break
        direct_payloads={v for o in observations for v in o['valid_sscc']}
        if not direct_payloads and not budget:
            for name,view,H0 in views[1:]:
                for k in [0,1]:
                    from sunvision.geometry import OrientationNormalizer
                    rotated,R=OrientationNormalizer.rotate(view,k); H=H0@np.linalg.inv(R); gray=rotated[:,:,0]
                    # Multi-height profiles are measured aggregates of rows in this same view.
                    for frac in [.12,.25,.5]:
                        bh=max(4,round(gray.shape[0]*frac))
                        for y in np.linspace(0,max(0,gray.shape[0]-bh),5).astype(int):
                            band=gray[y:y+bh]; q=transform_points([[0,y],[gray.shape[1]-1,y],[gray.shape[1]-1,y+bh-1],[0,y+bh-1]],H)
                            for quantile in [25,50]:
                                signal=np.percentile(band,quantile,axis=0).astype(np.uint8); stripe=np.tile(signal,(80,1)); stripe=local_normalize(stripe); attempt(stripe,f'{name}/row_profile_r{k}_y{y}_h{bh}_q{quantile}',H,source_quad=q)
                                if budget: break
                            if budget: break
                        if budget: break
                    if budget: break
                if budget: break
        payloads=sorted({v for o in observations for v in o['valid_sscc']}); state='no_read' if not payloads else ('conflict' if len(payloads)>1 else 'candidate_needs_review')
        return {'image':meta,'quality_metrics':quality(image),'state':state,'sscc_candidates':payloads,'observations':observations,'attempts':attempts,'errors':errors,'budget_exhausted':budget,'seconds':time.perf_counter()-start,'uses_expected_payload':False,'uses_other_photographs':False,'technology_scope':'Independent implementation using public principles, OpenCV and ZXing-C++; not vendor proprietary code','acceptance':'No result is certified correct without reviewed ground truth; checksum and agreement are validity checks, not proof of accuracy.'}

