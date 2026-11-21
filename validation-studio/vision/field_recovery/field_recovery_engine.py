from pathlib import Path
import copy,hashlib,json,math
from .anchor_detector import detect_anchors,box
from .spatial_field_assigner import assign_spatial,dedicated_rois
from .description_reconstructor import normalize
from .candidate_ranker import rank
from .orientation_resolver import resolve_orientation
FIELDS=('sku','descricao','qtde','lastro','lote','documento_entrada','validade_impressa','sscc')

def candidate(field,value,raw,copy_id,polygon,source,recipe,confidence,orientation,evidence_ids=(),**extra):
 return {'field':field,'raw_value':raw,'normalized_value':normalize(str(value),field),'source':source,'recipe':recipe,'polygon_original':polygon or [],'orientation':orientation,'confidence_raw':confidence,'confidence_calibrated':None,'character_confidences':None,'character_confidence_limitation':'not exposed by current OCR interface','status':'candidate','evidence_ids':list(evidence_ids),'copy_id':copy_id,**extra}

class FieldRecoveryEngine:
 version='SUN-V2.6'
 def process_copy(self,base):
  cp=copy.deepcopy(base);q=cp['quad_original'];length=lambda a,b:math.hypot(a[0]-b[0],a[1]-b[1]);bw=max(length(q[0],q[1]),length(q[2],q[3]));bh=max(length(q[1],q[2]),length(q[3],q[0]));angle=cp.get('legacy_orientation',0);w,h=(bh,bw) if angle%180 else (bw,bh);blocks=cp['ocr_blocks'];anchors=detect_anchors(blocks,w,h);observations={f:[] for f in FIELDS};printed14={b['text'] for b in blocks if b['text'].isdigit() and len(b['text'])==14 and box(b)[1]>h*.25}
  for f,data in cp['fields'].items():
   for c in data['candidates']:
    observations[f].append(candidate(f,c['normalized_value'],c.get('raw_value',c['normalized_value']),cp['copy_id'],c.get('polygon_original'),c['source'],'legacy_'+c.get('method','observation'),c.get('confidence'),angle,['legacy:'+cp['copy_id']+':'+str(c.get('block_id',c.get('method')))],matches_large_printed_number=(f=='sku' and c['normalized_value'] in printed14),legacy_observation=c))
  # Prefer preservation of existing qualified fields; fill only unresolved/ambiguous ones.
  prior={f:rank(copy.deepcopy(cs)) for f,cs in observations.items()}
  for match in assign_spatial(blocks,anchors,w,h):
   f=match['field']
   if prior[f]['status']=='accepted_candidate':continue
   b=match['block'];observations[f].append(candidate(f,match['value'],b['text'],cp['copy_id'],b.get('polygon_original'), 'ocr','spatial_context_v26',b.get('confidence'),angle,['block:'+str(b['id']),'anchor:'+str(match['anchor']['block_id'])],spatial_verified=True,anchor_evidence=match['anchor']))
  fields={f:rank(cs) for f,cs in observations.items()}
  orientation=resolve_orientation(cp.get('orientation_trials',[]),bw,bh)
  return {'copy_id':cp['copy_id'],'region_id':cp['region_id'],'quad_original':q,'visibility':cp.get('visibility'),'fields':fields,'raw_OCR_blocks':blocks,'anchors':anchors,'orientation':orientation,'coordinate_orientation_applied':angle,'original_to_rectified':cp['original_to_rectified'],'recovery_rois':dedicated_rois(blocks,anchors,int(w),int(h)),'human_review_required':True}
 def process(self,baseline):
  return {'schema_version':self.version,'image':baseline['image'],'physical_copies':[self.process_copy(c) for c in baseline['physical_copies']],'candidate_regions':baseline.get('candidate_regions',[]),'legacy_logistic_units_unchanged':baseline.get('logistic_units',[]),'integration_enabled':False,'ground_truth_used':False,'catalog_used_for_completion':False,'execution':'spatial reprocessing of immutable OCR; no new neural inference in this stage'}

