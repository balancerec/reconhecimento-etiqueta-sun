import sys
from fastapi.testclient import TestClient
from vision.api.app import create_app
app=create_app();c=TestClient(app);s=c.get('/api/session').json();p=c.get('/api/photos').json()[0];d=c.get('/api/photos/'+p['id']).json();cp=d['template']['copies'][0];r=c.post('/api/photos/'+p['id']+'/rectify',headers={'X-Studio-Token':s['token']},json={'copy_id':cp['copy_id'],'copies':[cp],'brightness':0,'contrast':1,'saturation':1});print(r.status_code,r.text[:300]);
if r.status_code==200:
 q=c.get(r.json()['url']);print('IMAGE',q.status_code,q.headers.get('content-type'),len(q.content))

