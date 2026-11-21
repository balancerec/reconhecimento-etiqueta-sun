import os,sys
from fastapi.testclient import TestClient
from vision.api.app import create_app
c=TestClient(create_app());t=c.get('/api/session').json()['token'];p=next(x for x in c.get('/api/photos').json() if x['name']=='20250929_075640.jpg');d=c.get('/api/photos/'+p['id']).json();q=d['template']['copies'][0]['polygon_original'];x=int(sum(v[0] for v in q)/4);y=int(sum(v[1] for v in q)/4);z=c.post('/api/v261/segmentation/click',headers={'X-Studio-Token':t},json={'image_id':p['id'],'click_original':{'x':x,'y':y}});print(z.status_code,len(z.json().get('contour',[])),len(z.json().get('quadrilateral',[])))

