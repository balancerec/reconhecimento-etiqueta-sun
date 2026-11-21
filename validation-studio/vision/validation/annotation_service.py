from pathlib import Path
import json,hashlib,uuid,os,math
from .annotation_models import FIELDS,AnnotationRequest
from .annotation_store import AnnotationStore
from .identity_review import valid_sscc,consolidate_human
from .evaluation_engine import convex,score_prediction
from .audit_log import now,canonical
class ReviewError(Exception):pass
class AnnotationService:
 def __init__(self,root,db_path=None):
  self.root=Path(root);self.photos={p['id']:p for p in json.loads((self.root/'data/photos.json').read_text(encoding='utf-8'))};self.store=AnnotationStore(db_path or self.root/'data/human/annotations.sqlite');self.export_dir=(Path(db_path).parent/'exports') if db_path else self.root/'data/human/exports';self.export_dir.mkdir(parents=True,exist_ok=True)
 def photo(self,photo_id):
  if photo_id not in self.photos:raise KeyError('Fotografia inexistente')
  return self.photos[photo_id]
 def predictions(self,photo_id):
  self.photo(photo_id);result=[{'run_id':'v24','path':self.root/'data/predictions/v24'/(photo_id+'.json')},{'run_id':'v26-spatial','path':self.root/'data/predictions/v26-spatial'/(photo_id+'.json')}]
  for p in sorted((self.root/'data/predictions/v26-gpu').glob(photo_id+'--*.json')) if (self.root/'data/predictions/v26-gpu').exists() else []:result.append({'run_id':p.stem.split('--',1)[1],'path':p})
  return result
 def prediction(self,photo_id,run_id='latest'):
  runs=self.predictions(photo_id);run=runs[-1] if run_id=='latest' else next((r for r in runs if r['run_id']==run_id),None)
  if run is None:raise KeyError('Execucao inexistente')
  raw=run['path'].read_bytes();return {'run_id':run['run_id'],'sha256':hashlib.sha256(raw).hexdigest(),'data':json.loads(raw)}
 def listing(self):
  latest={a['annotation']['photo_id']:a for a in self.store.all_latest()}
  return [{**p,'review_status':latest[p['id']]['status'] if p['id'] in latest else 'unreviewed','revision':latest[p['id']]['revision'] if p['id'] in latest else 0} for p in self.photos.values()]
 def template(self,photo_id,run_id='latest'):
  photo=self.photo(photo_id);pred=self.prediction(photo_id,run_id);copies=[]
  from .annotation_models import CopyAnnotation
  for cp in pred['data']['physical_copies']:copies.append(CopyAnnotation(copy_id=cp['copy_id'],polygon_original=cp['quad_original']).model_dump())
  return AnnotationRequest(photo_id=photo_id,image_sha256=photo['sha256'],prediction_run_id=pred['run_id'],copies=copies).model_dump()
 def check_source(self,photo):
  p=Path(photo['path'])
  if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=photo['sha256']:raise ReviewError('A fotografia original mudou ou desapareceu. Reimporte de forma versionada; revisao bloqueada para evitar gabarito sem evidencia.')
 def validate(self,payload,approve=False):
  photo=self.photo(payload['photo_id']);self.check_source(photo)
  if payload['image_sha256']!=photo['sha256']:raise ReviewError('Hash da fotografia diverge')
  pred=self.prediction(photo['id'],payload['prediction_run_id']);ids=[c['copy_id'] for c in payload['copies']]
  if len(ids)!=len(set(ids)):raise ReviewError('IDs de via duplicados')
  for c in payload['copies']:
   if set(c['fields'])!=set(FIELDS):raise ReviewError('Os oito campos devem ser preservados')
   for x,y in c['polygon_original']:
    if not (math.isfinite(x) and math.isfinite(y) and 0<=x<=photo['width'] and 0<=y<=photo['height']):raise ReviewError('Ponto fora das coordenadas normalizadas da fotografia')
  if not approve:return pred
  errors=[]
  if not payload['reviewer'].strip():errors.append('Informe o revisor humano')
  if not payload['exhaustive_instance_review']:errors.append('Confirme que todas as vias da fotografia foram revisadas, inclusive as perdidas pelo detector')
  if payload['review_mode']=='blind' and payload['used_suggestions']:errors.append('Revisao com sugestoes nao pode ser declarada cega')
  missing={c['copy_id'] for c in pred['data']['physical_copies']}-set(ids)
  if missing:errors.append('Decida explicitamente sobre todas as candidatas: '+', '.join(sorted(missing)))
  true_copies=[c for c in payload['copies'] if c['is_label']]
  if not true_copies and not payload['no_labels_confirmed']:errors.append('Confirme explicitamente fotografia sem etiqueta')
  for c in payload['copies']:
   cid=c['copy_id']
   if not c['copy_reviewed']:errors.append(cid+': confirme a decisao sobre a via')
   if not c['is_label']:continue
   if not c['polygon_reviewed'] or not convex(c['polygon_original']):errors.append(cid+': confirme um poligono convexo valido, sem cruzar arestas')
   if c['visibility']=='unreviewed':errors.append(cid+': informe visibilidade da via')
   for f,d in c['fields'].items():
    if not d['reviewed'] or d['visibility']=='unreviewed':errors.append(cid+'/'+f+': revisao de visibilidade pendente');continue
    if d['visibility']=='visible_legible':
     if d['value'] is None or not d['value'].strip():errors.append(cid+'/'+f+': valor visivel precisa de transcricao')
     if d['value_source']!='original_pixels':errors.append(cid+'/'+f+': confirme o texto nos pixels; catalogo/sugestao nao homologa')
     if f=='sscc' and not valid_sscc(d['value']):errors.append(cid+'/sscc: exige 18 digitos e modulo10 valido')
    elif d['value'] not in [None,'']:errors.append(cid+'/'+f+': campo ilegivel/ausente/cortado nao pode carregar valor esperado')
   identity=c.get('confirmed_sscc')
   if identity:
    if not valid_sscc(identity):errors.append(cid+': SSCC de identidade invalido')
    if c['identity_basis']=='direct_read':
     s=c['fields']['sscc']
     if s['visibility']!='visible_legible' or s['value']!=identity:errors.append(cid+': leitura direta de identidade deve coincidir com o SSCC transcrito')
    elif c['identity_basis']=='cross_photo_physical_confirmation':
     if not c['identity_note'].strip() or not c['identity_evidence_photo_ids'] or any(i not in self.photos for i in c['identity_evidence_photo_ids']):errors.append(cid+': vinculo fisico exige motivo e fotografias de evidencia')
    else:errors.append(cid+': escolha a evidencia fisica de identidade; SKU/lote nao criam vinculo')
  if errors:raise ReviewError('\n'.join(errors))
  return pred
 def save(self,request,approve=False):
  payload=request.model_dump();pred=self.validate(payload,approve);payload['prediction_sha256']=pred['sha256'];payload['source_coordinate_space']='EXIF-normalized original pixels';payload['dataset_role']=self.photo(payload['photo_id'])['dataset_role'];payload['integration_enabled']=False;return self.store.append(payload,'approved' if approve else 'draft')
 def export(self,approved_only=True):
  annotations=[r for r in self.store.all_latest() if not approved_only or r['status']=='approved'];photos=[]
  for r in annotations:
   p=self.photo(r['annotation']['photo_id']);photos.append({'photo':p,'review':r,'human_logistic_units':consolidate_human(r['annotation']['copies']) if r['status']=='approved' else []})
  audit=self.store.audit();payload={'schema_version':'SUN-V2.6-human-export','export_id':uuid.uuid4().hex,'exported_at':now(),'approved_only':approved_only,'annotations':photos,'annotation_count':len(photos),'audit_last_hash':audit['events'][-1]['event_hash'] if audit['events'] else '0'*64,'audit_chain_valid':audit['hash_chain_valid'],'algorithm_predictions_unchanged':True,'independent_holdout':False,'integration_enabled':False};text=canonical(payload);p=self.export_dir/(payload['export_id']+'.json')
  with p.open('x',encoding='utf-8') as f:f.write(text)
  digest=hashlib.sha256(text.encode()).hexdigest();self.store.record_event({'type':'ground_truth_export','export_id':payload['export_id'],'sha256':digest,'annotations':len(photos)});return {'path':p,'sha256':digest,'payload':payload}
 def evaluation(self,run_id='latest'):
  out=[]
  for row in self.store.all_latest():
   if row['status']!='approved':continue
   annotation=row['annotation'];photo=self.photo(annotation['photo_id']);pred=self.prediction(photo['id'],run_id);out.append({'photo_id':photo['id'],'run_id':pred['run_id'],'prediction_sha256':pred['sha256'],'annotation_revision':row['revision'],'annotation_sha256':row['sha256'],**score_prediction(pred['data'],annotation,photo['dataset_role'])})
  return {'evaluated_approved_photos':len(out),'results':out,'formal_metrics_available':bool(out),'independent_metrics_available':False,'all_current_images_are_development':True,'integration_enabled':False}

