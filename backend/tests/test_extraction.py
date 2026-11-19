import unittest
from core import extract,consensus,validate,FIELDS
class Extraction(unittest.TestCase):
 def test_real_dun_layout(self):
  text='375825\nPR PATO GERM LIMP SANIT MARINE\n750mL 12\nFABR:11/2026\nVENC:11/2028\nLOTE:8428857\nD344924\n17894650013578'
  kind,f,e=extract(text)
  self.assertEqual(kind,'DUN');self.assertEqual(f['sku'],'375825');self.assertEqual(f['units_per_case'],12)
  self.assertEqual(f['product_description'],'PR PATO GERM LIMP SANIT MARINE');self.assertEqual(f['gtin14'],'17894650013578')
  self.assertEqual(f['manufacturing_date'],'11/2026');self.assertEqual(f['lot'],'8428857')
 def test_sun_description_and_leading_zero(self):
  kind,f,e=extract('ITEM: 387279 GLADE ODORIZANTE CONCEN LAVANDA 120ML 12\nQTDE: 294\nLASTRO:49 VALIDADE: 2 ANO LT: 001234\nDOC ENTRADA:5083530012\n(00) 1 00 78946 503144002 2')
  self.assertEqual(kind,'SUN');self.assertEqual(f['sscc'],'100789465031440022');self.assertEqual(f['lot'],'001234')
  self.assertEqual(f['product_description'],'GLADE ODORIZANTE CONCEN LAVANDA 120ML 12');self.assertEqual(f['quantity_boxes'],294)
 def test_no_digit_substitution(self):
  kind,f,e=extract('ITEM:37582S\nQTDE:22\nLASTRO:15');self.assertIsNone(f['sku'])
 def test_no_cross_line_lot(self):
  kind,f,e=extract('LT:\nDOC ENTRADA:5083530012\nQTDE:22\nLASTRO:15');self.assertIsNone(f['lot'])
 def test_partial_date_precision(self):
  kind,f,e=extract('FAB:1.2026\nVENC:01/2028');self.assertEqual(f['manufacturing_date'],'01/2026')
 def read(self,value,engine):
  f=dict.fromkeys(FIELDS);f['sku']=value
  return dict(fields=f,engine=engine,variant='test',field_evidence=[])
 def test_conflict_not_silently_resolved(self):
  f,e,c=consensus([self.read('375825','a'),self.read('375827','b')]);self.assertIsNone(f['sku']);self.assertEqual(len(c),1)
 def test_majority_preserves_conflict(self):
  f,e,c=consensus([self.read('375825','a'),self.read('375825','b'),self.read('375827','c')]);self.assertEqual(f['sku'],'375825');self.assertEqual(len(c),1)
 def test_sscc_not_accepted_as_gtin(self):
  validation,_=validate('DUN',{'gtin14':'100789465031440022'});self.assertIn('INVALID_GTIN14',validation['errors'])
if __name__=='__main__':unittest.main()
