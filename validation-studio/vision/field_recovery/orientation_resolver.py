from .anchor_detector import detect_anchors

def resolve_orientation(trials,width,height,min_margin=3.):
 scores=[]
 for t in trials:
  k=t['k'];w,h=(height,width) if k%2 else (width,height);anchors=detect_anchors(t['blocks'],w,h);by={a['field']:a for a in anchors};score=len(by)*2
  for f,g in [('sku','qtde'),('qtde','lastro'),('lastro','documento_entrada')]:
   if f in by and g in by:score+=5 if by[f]['box'][1]<by[g]['box'][1] else -5
  scores.append({'angle':k*90,'score':score,'anchor_fields':sorted(by),'OCR_outputs':t['blocks'],'SSCC_qualification':'global fragments not identity proof'})
 scores.sort(key=lambda x:(-x['score'],x['angle']));plausible=[s['angle'] for s in scores if s['score']>=scores[0]['score']-min_margin] if scores else []
 return {'selected_angle':scores[0]['angle'] if len(plausible)==1 else None,'status':'resolved_by_spatial_anchors' if len(plausible)==1 else 'conflicting_or_insufficient_orientation','plausible_angles':plausible,'trials':scores,'ground_truth_used':False}

