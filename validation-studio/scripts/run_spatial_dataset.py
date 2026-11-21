from pathlib import Path
import sys,json,os,hashlib
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from vision.field_recovery.field_recovery_engine import FieldRecoveryEngine
engine=FieldRecoveryEngine();photos=json.loads((R/'data/photos.json').read_text(encoding='utf-8'));index=[]
for p in photos:
 src=R/p['baseline_prediction'];data=json.loads(src.read_text(encoding='utf-8'));out=engine.process(data);out['input_prediction_sha256']=hashlib.sha256(src.read_bytes()).hexdigest();target=R/'data/predictions/v26-spatial'/(p['id']+'.json');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');index.append({'photo_id':p['id'],'run_id':'v26-spatial','path':str(target.relative_to(R)).replace('\\','/'),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
(R/'data/derived-prediction-index.json').write_text(json.dumps(index,indent=2),encoding='utf-8');print('Spatial V26 results:',len(index))

