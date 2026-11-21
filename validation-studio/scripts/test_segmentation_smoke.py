import sys
from fastapi.testclient import TestClient
from vision.api.app import create_app
c=TestClient(create_app());s=c.get('/api/session').json();items=c.get('/api/photos').json();p=next(p for p in items if p['name']=='20250929_075640.jpg');d=c.get('/api/photos/'+p['id']).json();q=d['template']['copies'][0]['polygon_original'];x=int(sum(v[0] for v in q)/4);y=int(sum(v[1] for v in q)/4);r=c.post('/api/v261/segmentation/click',headers={'X-Studio-Token':s['token']},json={'image_id':p['id'],'click_original':{'x':x,'y':y}});print('POST',r.status_code,r.text[:350]);
if r.status_code==200:
 z=r.json();print('contour',len(z['contour']),'area',z['area_pixels'],'poly',len(z.get('polygon',z['contour'])),'transparency');g=c.get('/api/v261/segmentation/'+p['id']+'/'+z['segmentation_id']+'/png');print('PNG',g.status_code,g.headers.get('content-type'),len(g.content));from PIL import Image;import io;im=Image.open(io.BytesIO(g.content));print('RGBA',im.mode,im.size,'alpha_extrema',im.getchannel('A').getextrema())

