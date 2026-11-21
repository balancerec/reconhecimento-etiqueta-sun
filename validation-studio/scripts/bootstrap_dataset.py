from pathlib import Path
import os,json,hashlib,collections
R=Path(__file__).resolve().parents[1];V25=R.parent/'sun-v25-20261120-01';V24=R.parent/'sun-v24-20261120-01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=json.loads((V25/'dataset-manifest.json').read_text(encoding='utf-8'));meta=json.loads((V25/'audit/enriched-records.json').read_text(encoding='utf-8'));byid={r['image_id']:r for r in meta};photos=[];baseline_hashes={}
for row in manifest['images']:
 if row['dataset_kind']!='label_photo' or row['processing_state']!='processed':continue
 p=Path(row['path']);assert sha(p)==row['sha256'];base=byid[row['image_id']]['pipeline'];src=V25/row['artifact_base']/'baseline-current-results.json'
 if not src.exists():src=V24/'baseline-current-results.json'
 trials=json.loads(src.read_text(encoding='utf-8'));trialrow=next(x for x in trials if x['image']['sha256']==row['sha256']);regions={r['proposal']['id']:r for r in trialrow['regions']}
 copies=[]
 for c in base['physical_copies']:
  c={**c,'orientation_trials':regions[c['region_id']]['trials'],'legacy_orientation':regions[c['region_id']]['selected_rotation']};copies.append(c)
 snapshot={'schema_version':'SUN-V24-immutable-studio-input','image':base['image'],'physical_copies':copies,'candidate_regions':base['candidate_regions'],'logistic_units':base['logistic_units'],'integration_enabled':False,'source_prediction':'V25 verified V24 output; not human annotations'}
 target=R/'data/predictions/v24'/(row['image_id']+'.json');save(target,snapshot);baseline_hashes[str(target.relative_to(R)).replace('\\','/')]=sha(target)
 photos.append({'id':row['image_id'],'name':row['name'],'path':row['path'],'sha256':row['sha256'],'width':row['dimensions'][0],'height':row['dimensions'][1],'exif_orientation':row.get('EXIF_orientation'),'qualified_ssccs':row['qualified_sscc_values'],'observed_skus':row['skus_observed'],'copy_candidates':row['physical_copy_candidates'],'quality':row.get('quality',{}),'baseline_prediction':str(target.relative_to(R)).replace('\\','/'),'baseline_prediction_sha256':sha(target),'dataset_role':'development','independent_holdout':False})
assert len(photos)==62
save(R/'data/photos.json',photos);save(R/'data/immutable-input-hashes.json',baseline_hashes)
# Prior references are a separate read-only review channel, never worker inputs.
for source,name in [(V25/'evaluation/ground-truth-human-approved.json','prior-human-reference.json'),(R.parent/'sun-documentary-reference-20261120-01/documentary-sku-reference.json','catalog-reference.json')]:
 if source.exists():save(R/'data'/name,json.loads(source.read_text(encoding='utf-8')))
protected={str(V25/'dataset-manifest.json'):sha(V25/'dataset-manifest.json'),str(V25/'manifest-sha256.json'):sha(V25/'manifest-sha256.json'),str(V24/'results-all.json'):sha(V24/'results-all.json')}
save(R/'data/preservation-before.json',{'photos':{p['path']:p['sha256'] for p in photos},'historical_files':protected,'api_environment':'new isolated venv; original OCR environment unchanged'})
for folder in ['vision','vision/field_recovery','vision/validation','vision/api','vision/tests']:(R/folder/'__init__.py').write_text('',encoding='utf-8')
print(json.dumps({'photos':len(photos),'immutable_prediction_snapshots':len(baseline_hashes),'originals_modified':False},indent=2))

