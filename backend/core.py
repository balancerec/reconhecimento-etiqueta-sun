import re
from datetime import datetime
FIELDS = "sku product_description volume_ml units_per_case manufacturing_date expiration_date lot auxiliary_code gtin14 quantity_boxes lastro shelf_life entry_document sscc".split()
CATALOG = {"375825": (15,4), "375827": (15,4), "387279": (49,6)}
def gs1(value):
    return bool(value and value.isascii() and value.isdigit() and len(value) in (14,18) and (10-sum(int(c)*(3 if i%2==0 else 1) for i,c in enumerate(value[-2::-1]))%10)%10==int(value[-1]))
def parse(text):
    t=text.upper()
    kind="SUN" if re.search(r"LASTRO|QTDE|DOC\s*ENTRADA",t) else "DUN" if re.search(r"FABR|VENC|\b\d{14}\b",t) else "UNKNOWN"
    f=dict.fromkeys(FIELDS)
    patterns={"sku":r"(?:ITEM|SKU)\s*[:.-]?\s*(\d{6})\b", "volume_ml":r"\b(\d+)\s*ML\b", "units_per_case":r"\b(\d+)\s*(?:UN|UND|UNIDADES)\b", "manufacturing_date":r"FABR?[^\d\n]*(\d{2}/\d{4})", "expiration_date":r"VENC[^\d\n]*(\d{2}/\d{4})", "lot":r"(?:LOTE|LT)\s*[:.-]?\s*([A-Z0-9]+)", "auxiliary_code":r"\b(D\d{6})\b", "gtin14":r"(?<!\d)(\d{14})(?!\d)", "quantity_boxes":r"QTDE\s*[:.-]?\s*(\d+)", "lastro":r"LASTRO\s*[:.-]?\s*(\d+)", "shelf_life":r"VALIDADE\s*[:.-]?\s*(\d+\s*ANOS?)", "entry_document":r"DOC\s*ENTRADA\s*[:.-]?\s*(\d+)", "sscc":r"\(00\)\s*((?:\d[ ]*){18})(?!\d)"}
    for k,pat in patterns.items():
        m=re.search(pat,t)
        if m: f[k]=m.group(1).strip().replace(' ','') if k=='sscc' else m.group(1).strip()
    if kind=='DUN' and f['sku'] is None:
        m=re.search(r"(?<!\d)(\d{6})(?!\d)",t)
        if m:f['sku']=m.group(1)
    for k in ('volume_ml','units_per_case','quantity_boxes','lastro'):
        if f[k] is not None:f[k]=int(f[k])
    return kind,f

def validate(kind,f,decoded=None):
    errors=[]; warnings=[]; pallet={}
    required={'SUN':['sku','quantity_boxes','lastro','sscc','lot','entry_document'], 'DUN':['sku','gtin14','lot','manufacturing_date','expiration_date','units_per_case']}.get(kind,[])
    for k in required:
        if f.get(k) is None:warnings.append('MISSING_'+k.upper())
    for k in ('gtin14','sscc'):
        if f.get(k) is not None and not gs1(f[k]):errors.append('INVALID_'+k.upper())
    key='sscc' if kind=='SUN' else 'gtin14'
    if decoded and not gs1(decoded):errors.append('INVALID_BARCODE_CHECK_DIGIT')
    if decoded and f.get(key) and decoded!=f[key]:errors.append('OCR_BARCODE_MISMATCH')
    if not decoded:warnings.append('BARCODE_NOT_DECODED')
    dates={}
    for k in ('manufacturing_date','expiration_date'):
        if f.get(k):
            try:dates[k]=datetime.strptime(f[k],'%m/%Y')
            except ValueError:errors.append('INVALID_'+k.upper())
    if len(dates)==2 and dates['manufacturing_date']>dates['expiration_date']:errors.append('DATE_ORDER')
    for k in ('quantity_boxes','lastro','units_per_case','volume_ml'):
        if f.get(k) is not None and (type(f[k]) is not int or f[k]<=0):errors.append('INVALID_'+k.upper())
    rule=CATALOG.get(f.get('sku'))
    if not rule:warnings.append('SKU_NOT_REGISTERED')
    if kind=='SUN' and rule:
        l,c=rule; q=f.get('quantity_boxes'); actual=f.get('lastro')
        if actual is not None and actual!=l:errors.append('LASTRO_MISMATCH')
        if type(q) is int and q>0 and actual==l:
            capacity=l*c
            pallet=dict(nominal_layers=c,nominal_capacity_boxes=capacity,complete_layers=q//l,boxes_in_partial_layer=q%l,boxes_to_capacity=max(0,capacity-q),status='PALLET_OVER_CAPACITY' if q>capacity else 'PALLET_COMPLETE' if q==capacity else 'PALLET_PARTIAL_VALID')
            if q>capacity:errors.append('CAPACITY_EXCEEDED')
    warnings.append('HUMAN_REVIEW_REQUIRED_UNCALIBRATED_OCR')
    return dict(status='REJECTED' if errors else 'NEEDS_REVIEW',errors=errors,warnings=warnings,human_review_required=True),pallet
