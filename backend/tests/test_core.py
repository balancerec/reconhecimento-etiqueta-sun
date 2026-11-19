import unittest
from core import parse, validate, gs1
class Rules(unittest.TestCase):
    def sun(self,q=60,l=15,sku='375825'):
        return {'sku':sku,'quantity_boxes':q,'lastro':l}
    def test_complete(self):
        v,p=validate('SUN',self.sun()); self.assertEqual(p['complete_layers'],4); self.assertEqual(p['nominal_capacity_boxes'],60)
    def test_partial(self):
        v,p=validate('SUN',self.sun(22)); self.assertEqual(p['boxes_in_partial_layer'],7); self.assertEqual(p['status'],'PALLET_PARTIAL_VALID')
    def test_glade(self):
        v,p=validate('SUN',self.sun(294,49,'387279')); self.assertEqual(p['complete_layers'],6)
    def test_wrong_lastro(self):
        v,p=validate('SUN',self.sun(60,49)); self.assertIn('LASTRO_MISMATCH',v['errors'])
    def test_over_capacity(self):
        v,p=validate('SUN',self.sun(75)); self.assertIn('CAPACITY_EXCEEDED',v['errors'])
    def test_conflict(self):
        f=self.sun(); f['sscc']='178946503144002000'; v,p=validate('SUN',f,'178946503144002001'); self.assertIn('OCR_BARCODE_MISMATCH',v['errors'])
    def test_gs1(self):
        self.assertTrue(gs1('17894650013578')); self.assertFalse(gs1('17894650013579'))
    def test_extract(self):
        k,f=parse('ITEM: 375825 QTDE: 22 LASTRO: 15 LT: 001234'); self.assertEqual(k,'SUN'); self.assertEqual(f['lot'],'001234'); self.assertEqual(f['quantity_boxes'],22)
    def test_absent(self):
        k,f=parse('ilegivel'); self.assertEqual(k,'UNKNOWN'); self.assertTrue(all(v is None for v in f.values()))
    def test_dates(self):
        v,p=validate('DUN',{'manufacturing_date':'13/2026'}); self.assertIn('INVALID_MANUFACTURING_DATE',v['errors'])
if __name__=='__main__':unittest.main()
