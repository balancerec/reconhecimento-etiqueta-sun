import re
from datetime import datetime
from collections import Counter
FIELDS = "sku product_description volume_ml units_per_case manufacturing_date expiration_date lot auxiliary_code gtin14 quantity_boxes lastro shelf_life entry_document sscc".split()
NUMERIC={'volume_ml','units_per_case','quantity_boxes','lastro'}
CATALOG = {"375825": (15,4), "375827": (15,4), "387279": (49,6)}
def gs1(value):
    return bool(isinstance(value,str) and value.isascii() and value.isdigit() and len(value) in (14,18) and (10-sum(int(c)*(3 if i%2==0 else 1) for i,c in enumerate(value[-2::-1]))%10)%10==int(value[-1]))

def extract(text):
    """Keep line breaks, raw capture spans and source text; never replace S by 5."""
    t=text.upper()
    sun=len(re.findall(r"\b(?:LASTRO|QTDE|SSCC|DOC\s*ENTRADA)\b",t))
    dun=len(re.findall(r"\b(?:FABR?|VENC|LOTE)\b",t))
    kind='SUN' if sun>=2 else 'DUN' if dun>=2 or re.search(r'(?<!\d)\d{14}(?!\d)',t) else 'UNKNOWN'
    fields=dict.fromkeys(FIELDS); evidence=[]
    patterns={
      'sku':r'(?:ITEM|\u00cdTEM|SKU)\s*[:.\-]?\s*(\d{6})(?!\d)',
      'volume_ml':r'\b(\d{2,5})[ \t]*ML\b',
      'units_per_case':r'\b(\d{1,3})[ \t]*(?:UN|UND|UNIDADES)\b',
      'manufacturing_date':r'\bFAB(?:R|RICACAO|RICA\u00c7\u00c3O)?[ \t]*[:.\-]?[ \t]*(\d{1,2}[/.]\d{4})',
      'expiration_date':r'\b(?:VENC(?:IMENTO)?|VALIDADE)[ \t]*[:.\-]?[ \t]*(\d{1,2}[/.]\d{4})',
      'lot':r'\b(?:LOTE|LOT|LT)[ \t]*[:.\-]?[ \t]*([A-Z0-9]*\d[A-Z0-9]*)\b',
      'auxiliary_code':r'\b(D\d{5,9})\b',
      'gtin14':r'(?<!\d)(\d{14})(?!\d)',
      'quantity_boxes':r'\b(?:QTDE|QTD)[ \t]*[:.\-]?[ \t]*(\d{1,5})(?!\d)',
      'lastro':r'\bLASTRO[ \t]*[:.\-]?[ \t]*(\d{1,4})(?!\d)',
      'shelf_life':r'\bVALIDADE[ \t]*[:.\-]?[ \t]*(\d+[ \t]*ANOS?)',
      'entry_document':r'\bDOC[ \t]*ENTRADA[ \t]*[:.\-]?[ \t]*(\d{5,16})(?!\d)',
      'sscc':r'\(00\)[ \t]*((?:\d[ \t]*){18})(?!\d)',
    }
    def put(key,match):
        if not match:return
        raw=text[match.start(1):match.end(1)];value=raw.strip()
        if key in NUMERIC:value=int(value)
        elif key in ('sscc','gtin14'):value=re.sub(r'\s','',value)
        elif key.endswith('_date'):
            parts=re.split(r'[/.]',value);value=parts[0].zfill(2)+'/'+parts[1]
        fields[key]=value;evidence.append(dict(field_name=key,raw_text=raw,normalized_value=value,text_span=list(match.span(1)),source='OCR'))
    for key,pattern in patterns.items():put(key,re.search(pattern,t))
    if kind=='DUN' and fields['sku'] is None:
        put('sku',re.search(r'(?m)^[ \t]*(\d{6})[ \t]*$',t))
    if kind=='DUN' and fields['units_per_case'] is None:
        put('units_per_case',re.search(r'\b\d{2,5}[ \t]*ML[ \t]+(\d{1,3})\b',t))
    if fields['gtin14'] is None and kind=='DUN':
        put('gtin14',re.search(r'(?m)^[ \t]*((?:\d[ \t]*){14})[ \t]*$',t))
    if fields['sscc'] is None:
        put('sscc',re.search(r'(?m)^[ \t]*(\d{18})[ \t]*$',t))
    # SUN descriptions share the ITEM line; DUN descriptions are independent lines.
    m=re.search(r'(?m)(?:ITEM|\u00cdTEM|SKU)[ \t]*[:.\-]?[ \t]*\d{6}[ \t]+([^\n]+)',t)
    if m:
        raw=text[m.start(1):m.end(1)];raw=re.split(r'\b(?:QTDE|LASTRO|VALIDADE|LT|LOTE|DOC)\b',raw,flags=re.I)[0].strip()
        if re.search(r'[A-Z\u00c0-\u0178]{3}',raw,re.I):fields['product_description']=raw
    if not fields['product_description']:
        lines=text.splitlines();desc=next((line.strip() for line in lines if re.search(r'\b(?:PATO|GLADE|ROOM[ \t]+MIST)\b',line,re.I)),None)
        fields['product_description']=desc
    if fields['product_description']:
        start=text.find(fields['product_description'])
        evidence.append(dict(field_name='product_description',raw_text=fields['product_description'],normalized_value=fields['product_description'],text_span=[start,start+len(fields['product_description'])],source='OCR'))
    return kind,fields,evidence

def parse(text):
    kind,fields,_=extract(text);return kind,fields

def consensus(reads):
    """Reads are from the same rectified label; no cross-label evidence."""
    fields=dict.fromkeys(FIELDS);conflicts=[];evidence=[]
    for key in FIELDS:
        entries=[(r,r['fields'][key]) for r in reads if r['fields'].get(key) is not None]
        if not entries:continue
        votes=Counter(value for r,value in entries);best,count=votes.most_common(1)[0]
        if len(votes)>1:
            conflicts.append(dict(field_name=key,candidates=[dict(value=v,votes=n) for v,n in votes.items()]))
            if count<=len(entries)/2:continue
        fields[key]=best
        for r,v in entries:
            if v==best:
                evidence.extend(dict(e,engine=r['engine'],variant=r['variant']) for e in r.get('field_evidence',[]) if e['field_name']==key)
    return fields,evidence,conflicts

def validate(kind,f,decoded=None):
    errors=[]; warnings=[]; pallet={}
    if kind=='UNKNOWN':warnings.append('UNKNOWN_LABEL')
    if f.get('sku') and not re.fullmatch(r'[0-9]{6}',str(f['sku'])):errors.append('INVALID_SKU')
    required={'SUN':['sku','quantity_boxes','lastro','sscc','lot','entry_document'], 'DUN':['sku','gtin14','lot','manufacturing_date','expiration_date','units_per_case']}.get(kind,[])
    for k in required:
        if f.get(k) is None:warnings.append('MISSING_'+k.upper())
    for k in ('gtin14','sscc'):
        if f.get(k) is not None and (not gs1(f[k]) or len(f[k])!=(14 if k=='gtin14' else 18)):errors.append('INVALID_'+k.upper())
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
