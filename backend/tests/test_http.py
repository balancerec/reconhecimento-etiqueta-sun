"""HTTP tests with fake OCR/decoder; no claim of real image accuracy."""
import os,sys,types,tempfile,unittest,importlib,uuid
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
import io
class HttpContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=Path(os.environ['TEMP'])/('labels-http-test-'+uuid.uuid4().hex);cls.directory.mkdir();os.environ['DATA_DIR']=str(cls.directory)
        cls.stubs={}
        cv=types.ModuleType('cv2');cv.COLOR_RGB2HSV=1;cv.COLOR_RGB2GRAY=2;cv.MORPH_CLOSE=3;cv.RETR_EXTERNAL=4;cv.CHAIN_APPROX_SIMPLE=5
        cv.cvtColor=lambda a,*args:a;cv.inRange=lambda *args:None;cv.morphologyEx=lambda *args:None
        cv.contourArea=lambda c:0;cv.findContours=lambda *args:([],None);cv.createCLAHE=lambda *args:types.SimpleNamespace(apply=lambda a:a)
        ocr=types.ModuleType('pytesseract');ocr.Output=types.SimpleNamespace(DICT='dict');ocr.get_tesseract_version=lambda:'fake-test-engine'
        def recognize(*args,**kwargs):
            words='ITEM: 375825 QTDE: 22 LASTRO: 15 LT: 001234 DOC ENTRADA: 5083399711'.split()
            return dict(text=words,conf=[90]*len(words),left=[0]*len(words),top=[0]*len(words),width=[10]*len(words),height=[10]*len(words))
        ocr.image_to_data=recognize
        zx=types.ModuleType('zxingcpp');zx.read_barcodes=lambda a:[]
        cls.patch=patch.dict(sys.modules,{'cv2':cv,'pytesseract':ocr,'zxingcpp':zx});cls.patch.start()
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]));cls.app=importlib.import_module('app');cls.client=TestClient(cls.app.app)
    @classmethod
    def tearDownClass(cls):cls.patch.stop()
    def upload(self):
        im=io.BytesIO();Image.new('RGB',(200,300),'white').save(im,'PNG')
        return self.client.post('/v1/recognize',files={'image':('label.png',im.getvalue(),'image/png')})
    def test_page_and_health(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertIn('LabelBackend',self.client.get('/backend-client.js').text)
        self.assertEqual(self.client.get('/health').json()['status'],'ok')
    def test_upload_and_correction(self):
        response=self.upload();self.assertEqual(response.status_code,200)
        result=response.json();label=result['labels'][0]
        self.assertEqual(label['fields']['quantity_boxes'],22)
        self.assertEqual(label['pallet']['boxes_in_partial_layer'],7)
        rid=result['id'];self.assertEqual(self.client.get('/v1/inspections/'+rid).status_code,200)
        correction={'label_index':0,'field_name':'quantity_boxes','value':75,'operator':'Teste','reason':'Contrato HTTP'}
        updated=self.client.post('/v1/inspections/'+rid+'/corrections',json=correction).json()
        self.assertEqual(updated['corrections'][0]['previous'],22)
        self.assertIn('CAPACITY_EXCEEDED',updated['labels'][0]['validation']['errors'])
        self.assertEqual(updated['labels'][0]['raw_text'],label['raw_text'])
        correction['value']='texto';self.assertEqual(self.client.post('/v1/inspections/'+rid+'/corrections',json=correction).status_code,422)
    def test_invalid_upload(self):
        self.assertEqual(self.client.post('/v1/recognize',files={'image':('x.jpg',b'invalid','image/jpeg')}).status_code,422)
        self.assertEqual(self.client.post('/v1/recognize',files={'image':('x.jpg',b'x'*(12*1024*1024+1),'image/jpeg')}).status_code,413)
    def test_origin(self):
        r=self.client.options('/v1/recognize',headers={'Origin':'https://balancerec.github.io','Access-Control-Request-Method':'POST'})
        self.assertEqual(r.headers['access-control-allow-origin'],'https://balancerec.github.io')
        r=self.client.options('/v1/recognize',headers={'Origin':'https://other.test','Access-Control-Request-Method':'POST'})
        self.assertNotIn('access-control-allow-origin',r.headers)
if __name__=='__main__':unittest.main()
