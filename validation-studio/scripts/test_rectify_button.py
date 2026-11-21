import sys,os,json
from fastapi.testclient import TestClient
from vision.api.app import create_app
c=TestClient(create_app());t=c.get('/api/session').json()['token'];p=next(x for x in c.get('/api/photos').json() if x['name']=='20250929_075640.jpg');d=c.get('/api/photos/'+p['id']).json();copy=d['template']['copies'][0];res=c.post('/api/photos/'+p['id']+'/rectify',headers={'X-Studio-Token':t},json={'copy_id':copy['copy_id'],'copies':[copy],'brightness':0,'contrast':1,'saturation':1});print(res.status_code,res.text[:150]);
if res.status_code==200:
 q=res.json();im=c.get(q['url']);print(im.status_code,im.headers.get('content-type'),len(im.content))

