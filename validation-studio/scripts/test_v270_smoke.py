import sys,os,json
from fastapi.testclient import TestClient
from vision.api.app import create_app
c=TestClient(create_app());token=c.get('/api/session').json()['token'];p=next(x for x in c.get('/api/photos').json() if x['name']=='20250929_075640.jpg');res=c.post('/api/v270/restoration/process',headers={'X-Studio-Token':token},json={'image_id':p['id'],'brightness':0,'contrast':1,'saturation':1,'sharpness':35,'deblur':20,'denoise':15,'clahe':25});print(res.status_code,res.text[:600]);
if res.status_code==200:
 d=res.json();print('GET',c.get(f"/api/v270/restoration/{p['id']}/{d['processing_id']}").status_code,'IMAGE',c.get(f"/api/v270/restoration/{p['id']}/{d['processing_id']}/image").status_code,'MANIFEST',c.get(f"/api/v270/restoration/{p['id']}/{d['processing_id']}/manifest").status_code)


