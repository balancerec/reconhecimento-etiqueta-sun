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
        cls.directory=Path(os.environ.get('TEMP',tempfile.gettempdir()))/('labels-http-test-'+uuid.uuid4().hex);cls.directory.mkdir();os.environ['DATA_DIR']=str(cls.directory)
        vision=types.ModuleType('vision')
        def recognize_labels(rgb,progress=lambda *args:None):
            from core import parse,validate
            kind,fields=parse('ITEM: 375825 QTDE: 22 LASTRO: 15 LT: 001234 DOC ENTRADA: 5083399711')
            validation,pallet=validate(kind,fields)
            return [dict(label_type=kind,fields=fields,validation=validation,pallet=pallet,raw_text='original OCR',field_evidence=[],barcode=dict(decoded_value=None,ocr_value=None,ocr_matches_barcode=None))],dict(elapsed_seconds=0)
        vision.recognize_labels=recognize_labels
        vision.health=lambda:dict(status='ok',version='0.2.0',engines=dict(rapidocr=True,tesseract=True))
        cls.patch=patch.dict(sys.modules,{'vision':vision});cls.patch.start()
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
    def test_jobs(self):
        import time
        im=io.BytesIO();Image.new('RGB',(200,300),'white').save(im,'PNG')
        response=self.client.post('/v2/jobs',files={'image':('label.png',im.getvalue(),'image/png')})
        self.assertEqual(response.status_code,202);job=response.json()
        for _ in range(100):
            status=self.client.get(job['status_url']).json()
            if status['status'] in ('COMPLETED','FAILED'):break
            time.sleep(.01)
        self.assertEqual(status['status'],'COMPLETED');self.assertEqual(status['result']['labels'][0]['fields']['sku'],'375825')
    def test_empty_operator_and_strict_types(self):
        result=self.upload().json();rid=result['id']
        correction={'label_index':0,'field_name':'quantity_boxes','value':True,'operator':'Teste','reason':'Teste'}
        self.assertEqual(self.client.post('/v1/inspections/'+rid+'/corrections',json=correction).status_code,422)
        correction.update(value=22,operator=' ')
        self.assertEqual(self.client.post('/v1/inspections/'+rid+'/corrections',json=correction).status_code,422)
    def test_invalid_upload(self):
        self.assertEqual(self.client.post('/v1/recognize',files={'image':('x.jpg',b'invalid','image/jpeg')}).status_code,422)
        self.assertEqual(self.client.post('/v1/recognize',files={'image':('x.jpg',b'x'*(12*1024*1024+1),'image/jpeg')}).status_code,413)
    def test_origin(self):
        r=self.client.options('/v1/recognize',headers={'Origin':'https://balancerec.github.io','Access-Control-Request-Method':'POST'})
        self.assertEqual(r.headers['access-control-allow-origin'],'https://balancerec.github.io')
        r=self.client.options('/v1/recognize',headers={'Origin':'https://other.test','Access-Control-Request-Method':'POST'})
        self.assertNotIn('access-control-allow-origin',r.headers)
if __name__=='__main__':unittest.main()
