import sys,os,json,io,struct,hashlib
from pathlib import Path
from fastapi.testclient import TestClient
from vision.api.app import create_app
root=Path(__file__).resolve().parents[1];app=create_app();c=TestClient(app);sess=c.get('/api/session').json();photos=c.get('/api/photos').json();report={'routes':[getattr(x,'path','') for x in app.routes if 'v261/segmentation' in getattr(x,'path','')],'tests':[],'integration_enabled':False}
def run(name,idx=0):
 p=next(p for p in photos if p['name']==name);d=c.get('/api/photos/'+p['id']).json();q=d['template']['copies'][idx]['polygon_original'];x=int(sum(v[0] for v in q)/len(q));y=int(sum(v[1] for v in q)/len(q));before=hashlib.sha256(Path(p['path']).read_bytes()).hexdigest();r=c.post('/api/v261/segmentation/click',headers={'X-Studio-Token':sess['token']},json={'image_id':p['id'],'click_original':{'x':x,'y':y}});res={'image':name,'http':r.status_code};
 if r.status_code==200:
  z=r.json();g=c.get(f"/api/v261/segmentation/{p['id']}/{z['segmentation_id']}/png");png=g.content;wh=struct.unpack('>II',png[16:24]);res.update(segmentation_id=z['segmentation_id'],vertices=len(z['contour']),polygon=z['contour'],area_pixels=z['area_pixels'],png_status=g.status_code,png_signature=png[:8].hex(),png_size=wh,png_bytes=len(png),original_unchanged=before==hashlib.sha256(Path(p['path']).read_bytes()).hexdigest(),copy_id=d['template']['copies'][idx]['copy_id']);
 report['tests'].append(res);return p,res
run('20250929_075640.jpg')
try:
 p=next(p for p in photos if p['name']=='20261120_005329.jpg');d=c.get('/api/photos/'+p['id']).json();report['two_copy_template_count']=len(d['template']['copies']);units=d['prediction']['data'].get('logistic_units',[]);report['two_copy_prediction_units']=len(units);report['two_copy_quantity_values']=[u.get('quantity') for u in units];report['two_copy_ssccs']=[u.get('sscc') for u in units];run('20261120_005329.jpg',0);run('20261120_005329.jpg',1)
except Exception as e:report['two_copy_error']=repr(e)
p=next(p for p in photos if p['name']=='20250929_075640.jpg');bad=c.post('/api/v261/segmentation/click',headers={'X-Studio-Token':sess['token']},json={'image_id':p['id'],'click_original':{'x':-1,'y':0}});report['invalid_click_status']=bad.status_code
out=root/'V261-GEOMETRY-VALIDATION.json';out.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False)[:2500])

