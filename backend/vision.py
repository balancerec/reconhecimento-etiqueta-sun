"""Local, bounded OCR pipeline. Geometry and OCR never merge distinct regions."""
import time
from collections import defaultdict
import numpy as np
import cv2
import pytesseract
import zxingcpp
from core import extract, consensus, validate, gs1

_ENGINE=None
_ENGINE_ERROR=None

def rapid_engine():
    global _ENGINE,_ENGINE_ERROR
    if _ENGINE is None and _ENGINE_ERROR is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ENGINE=RapidOCR(det_use_cuda=False,cls_use_cuda=False,rec_use_cuda=False,intra_op_num_threads=2,inter_op_num_threads=1)
        except Exception as e:_ENGINE_ERROR=str(e)
    return _ENGINE

def health():
    version=str(pytesseract.get_tesseract_version());engine=rapid_engine()
    return dict(status='ok' if engine else 'degraded',version='0.2.0',ocr=version,engines={'tesseract':True,'rapidocr':engine is not None},warnings=[] if engine else ['RAPIDOCR_UNAVAILABLE'])

def ordered(points):
    pts=np.asarray(points,dtype=np.float32).reshape(4,2)
    # Angle sort around center also works for diamond-shaped quadrilaterals.
    center=pts.mean(axis=0);idx=np.argsort(np.arctan2(pts[:,1]-center[1],pts[:,0]-center[0]));pts=pts[idx]
    return np.roll(pts,-int(np.argmin(pts.sum(axis=1))),axis=0)

def rectify(rgb,points):
    tl,tr,br,bl=ordered(points)
    w=max(np.linalg.norm(tr-tl),np.linalg.norm(br-bl));h=max(np.linalg.norm(bl-tl),np.linalg.norm(br-tr))
    w,h=max(32,round(float(w))),max(32,round(float(h)))
    matrix=cv2.getPerspectiveTransform(np.array([tl,tr,br,bl]),np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]]))
    return cv2.warpPerspective(rgb,matrix,(w,h),borderValue=(255,255,255))

def detect(rgb):
    h,w=rgb.shape[:2];scale=min(1,1500/max(w,h));small=cv2.resize(rgb,None,fx=scale,fy=scale) if scale<1 else rgb
    hsv=cv2.cvtColor(small,cv2.COLOR_RGB2HSV)
    masks=[('BLUE',cv2.inRange(hsv,np.array([75,55,35]),np.array([135,255,255]))),('WHITE',cv2.inRange(hsv,np.array([0,0,145]),np.array([179,85,255])))]
    regions=[];total=small.shape[0]*small.shape[1]
    for color,mask in masks:
        # Small closing fills printing gaps without joining neighboring labels.
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in sorted(contours,key=cv2.contourArea,reverse=True):
            area=cv2.contourArea(contour)
            if not total*.025<area<total*.97:continue
            rect=cv2.minAreaRect(contour);rw,rh=rect[1]
            if min(rw,rh)<65 or max(rw,rh)/max(1,min(rw,rh))>2.6:continue
            if area/max(1,rw*rh)<.58:continue
            approx=cv2.approxPolyDP(contour,.025*cv2.arcLength(contour,True),True)
            points=approx.reshape(4,2) if len(approx)==4 and cv2.isContourConvex(approx) else cv2.boxPoints(rect)
            pts=ordered(points)/scale
            x0,y0=pts.min(axis=0);x1,y1=pts.max(axis=0)
            box=[float(x0),float(y0),float(x1-x0),float(y1-y0)]
            # Suppress a white paper margin around an already detected blue label.
            duplicate=False
            for region in regions:
                x,y,bw,bh=region['region'];inter=max(0,min(x+bw,x1)-max(x,x0))*max(0,min(y+bh,y1)-max(y,y0))
                if inter/max(1,min(bw*bh,(x1-x0)*(y1-y0)))>.65:duplicate=True;break
            if not duplicate:regions.append(dict(region=box,corners=pts.tolist(),color=color,fallback=False))
    if not regions:regions=[dict(region=[0,0,w,h],corners=[[0,0],[w-1,0],[w-1,h-1],[0,h-1]],color='UNKNOWN',fallback=True)]
    return sorted(regions,key=lambda r:(r['region'][1],r['region'][0]))[:6]

def variants(rgb):
    # Red channel removes the cyan background more effectively than grayscale.
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    enhanced=cv2.createCLAHE(2.0,(8,8)).apply(gray)
    yield 'contrast',enhanced
    red=cv2.createCLAHE(2.0,(8,8)).apply(rgb[:,:,0])
    yield 'cyan_removed',red
    yield 'adaptive',cv2.adaptiveThreshold(enhanced,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,35,13)

def tesseract_read(image,psm):
    d=pytesseract.image_to_data(image,lang='por+eng',config='--psm '+str(psm),output_type=pytesseract.Output.DICT,timeout=15)
    groups=defaultdict(list)
    for i,word in enumerate(d['text']):
        if not word.strip() or float(d['conf'][i])<0:continue
        key=(d.get('page_num',[1]*len(d['text']))[i],d.get('block_num',[1]*len(d['text']))[i],d.get('par_num',[1]*len(d['text']))[i],d.get('line_num',[1]*len(d['text']))[i])
        groups[key].append(dict(raw_text=word,confidence=float(d['conf'][i])/100,bounding_box=[int(d[k][i]) for k in ('left','top','width','height')],source='OCR',engine='tesseract'))
    words=[];lines=[]
    for group in groups.values():
        group.sort(key=lambda v:v['bounding_box'][0])
        offset=sum(len(line)+1 for line in lines)
        for word in group:
            word['text_span']=[offset,offset+len(word['raw_text'])];offset+=len(word['raw_text'])+1
        lines.append(' '.join(v['raw_text'] for v in group));words.extend(group)
    return '\n'.join(lines),words

def neural_read(rgb):
    engine=rapid_engine()
    if engine is None:return '',[]
    # RapidOCR expects OpenCV BGR, not PIL RGB.
    result,_=engine(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
    words=[];rows=[]
    for box,text,confidence in result or []:
        points=np.asarray(box);x,y=points.min(axis=0);x2,y2=points.max(axis=0)
        words.append(dict(raw_text=text,confidence=float(confidence),bounding_box=[float(x),float(y),float(x2-x),float(y2-y)],source='OCR',engine='rapidocr'))
    # Reconstruct lines from geometric position rather than flattening all text.
    for word in sorted(words,key=lambda d:d['bounding_box'][1]+d['bounding_box'][3]/2):
        x,y,w,h=word['bounding_box'];cy=y+h/2
        row=next((r for r in rows if abs(r['cy']-cy)<max(8,min(r['h'],h)*.55)),None)
        if row is None:rows.append(dict(cy=cy,h=h,words=[word]))
        else:row['words'].append(word)
    lines=[]
    for row in rows:
        ordered_words=sorted(row['words'],key=lambda d:d['bounding_box'][0]);offset=sum(len(line)+1 for line in lines)
        for word in ordered_words:
            word['text_span']=[offset,offset+len(word['raw_text'])];offset+=len(word['raw_text'])+1
        lines.append(' '.join(w['raw_text'] for w in ordered_words))
    return '\n'.join(lines),words

def reading(text,words,engine,variant,angle):
    kind,fields,evidence=extract(text)
    for e in evidence:
        # Geometric evidence belongs to this engine/variant, in the upright crop.
        match=[word for word in words if word.get('text_span') and word['text_span'][0]<e['text_span'][1] and word['text_span'][1]>e['text_span'][0]]
        if match:
            boxes=[v['bounding_box'] for v in match];x=min(v[0] for v in boxes);y=min(v[1] for v in boxes)
            e['bounding_box']=[x,y,max(v[0]+v[2] for v in boxes)-x,max(v[1]+v[3] for v in boxes)-y]
            e['confidence']=min(v['confidence'] for v in match)
        else:e['bounding_box']=None;e['confidence']=None
    anchors=len(__import__('re').findall(r'\b(?:ITEM|LASTRO|QTDE|FABR|VENC|LOTE|SSCC)\b',text.upper()))
    count=sum(v is not None for v in fields.values());conf=sum(w['confidence'] for w in words)/max(1,len(words))
    return dict(kind=kind,fields=fields,field_evidence=evidence,words=words,text=text,engine=engine,variant=variant,angle=angle,score=anchors*4+count*2+conf)

def decode(rgb):
    results=[];seen=set()
    # ZXing rotates internally; contrast/threshold and upscaling are independent retries.
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    candidates=[rgb,gray,cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]]
    if max(rgb.shape[:2])<1800:candidates.append(cv2.resize(gray,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC))
    for image in candidates:
        for bar in zxingcpp.read_barcodes(image,try_rotate=True,try_downscale=True,try_invert=True):
            key=(str(bar.format),bar.text)
            if key in seen:continue
            seen.add(key);value=bar.text.removeprefix(']C1')
            if value.startswith('(00)'):value=value[4:]
            elif len(value)==20 and value.startswith('00'):value=value[2:]
            results.append(dict(raw_value=bar.text,symbology=str(bar.format),decoded_value=value,check_digit_valid=gs1(value)))
    return results

def recognize_labels(rgb,progress=lambda *args:None):
    start=time.monotonic();deadline=start+210;labels=[]
    regions=detect(rgb);progress(10,'Localizando e corrigindo '+str(len(regions))+' região(ões)')
    for index,region in enumerate(regions):
        if time.monotonic()>deadline:break
        crop=rectify(rgb,region['corners']);scale=min(2,max(1,1500/max(crop.shape[:2])))
        if scale!=1:crop=cv2.resize(crop,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
        if max(crop.shape[:2])>2400:crop=cv2.resize(crop,None,fx=2400/max(crop.shape[:2]),fy=2400/max(crop.shape[:2]))
        reads=[];failures=[]
        # First identify orientation with a sparse-text OCR layout.
        for angle in (0,90,180,270):
            if time.monotonic()>deadline:break
            oriented=np.rot90(crop,angle//90).copy()
            try:
                text,words=tesseract_read(next(variants(oriented))[1],11);reads.append(reading(text,words,'tesseract','orientation_psm11',angle))
            except RuntimeError:failures.append('TESSERACT_TIMEOUT')
            progress(15+int(65*(index+angle/360)/len(regions)),'Etiqueta '+str(index+1)+': orientação '+str(angle)+'°')
        if not reads:raise RuntimeError('Nenhum motor OCR respondeu')
        best=max(reads,key=lambda r:r['score']);angle=best['angle'];upright=np.rot90(crop,angle//90).copy()
        same=[best]
        for name,image in variants(upright):
            if time.monotonic()>deadline:break
            try:
                text,words=tesseract_read(image,6 if name!='adaptive' else 11);same.append(reading(text,words,'tesseract',name,angle))
            except RuntimeError:failures.append('TESSERACT_TIMEOUT')
        if time.monotonic()<deadline:
            try:
                text,words=neural_read(upright)
                if text:same.append(reading(text,words,'rapidocr','neural',angle))
            except Exception:failures.append('RAPIDOCR_FAILED')
        if rapid_engine() is None:failures.append('RAPIDOCR_UNAVAILABLE')
        best=max(same,key=lambda r:r['score']);kind=best['kind']
        # An engine proposing the wrong label class cannot contaminate the chosen class.
        eligible=[r for r in same if r['kind']==kind]
        fields,evidence,conflicts=consensus(eligible)
        bars=decode(upright);length=18 if kind=='SUN' else 14
        identifiers={b['decoded_value'] for b in bars if b['decoded_value'].isdigit() and len(b['decoded_value'])==length}
        decoded=next(iter(identifiers)) if len(identifiers)==1 else None
        key='sscc' if kind=='SUN' else 'gtin14';ocr_value=fields[key]
        # Never call a decoded barcode an OCR reading; record the separate source.
        if decoded and gs1(decoded) and fields[key] is None and not any(c['field_name']==key for c in conflicts):
            fields[key]=decoded;evidence.append(dict(field_name=key,raw_text=decoded,normalized_value=decoded,confidence=None,bounding_box=None,source='BARCODE',engine='zxing'))
        validation,pallet=validate(kind,fields,decoded)
        validation['warnings'].extend(sorted(set(failures)))
        if region['fallback']:validation['warnings'].append('FULL_IMAGE_FALLBACK_CHECK_LABEL_SEPARATION')
        if conflicts:validation['warnings'].append('OCR_READINGS_DISAGREE')
        if len(identifiers)>1:validation['errors'].append('MULTIPLE_BARCODE_VALUES');validation['status']='REJECTED'
        if time.monotonic()>deadline:validation['warnings'].append('PROCESSING_BUDGET_REACHED')
        for e in evidence:e['validation_status']='PENDING';e['correction_history']=[]
        labels.append(dict(schema_version='1.1',label_type=kind,classification=dict(confidence=None,evidence=['TEXT_ANCHORS',region['color']]),image=dict(**region,orientation_degrees=angle,rectified_width_px=int(upright.shape[1]),rectified_height_px=int(upright.shape[0]),coordinate_system='field/word boxes in upright rectified crop; corners in EXIF-oriented original'),fields=fields,raw_text=best['text'],ocr_evidence=best['words'],field_evidence=evidence,ocr_conflicts=conflicts,ocr_passes=[dict(engine=r['engine'],variant=r['variant'],raw_text=r['text']) for r in eligible],barcode=dict(decoded_value=decoded,ocr_value=ocr_value,check_digit_valid=gs1(decoded) if decoded else None,ocr_matches_barcode=decoded==ocr_value if decoded and ocr_value else None,all_decoded=bars),pallet=pallet,validation=validation))
    progress(95,'Salvando resultado e evidências')
    return labels,dict(elapsed_seconds=round(time.monotonic()-start,2),regions_detected=len(regions),regions_processed=len(labels),budget_reached=time.monotonic()>deadline)
