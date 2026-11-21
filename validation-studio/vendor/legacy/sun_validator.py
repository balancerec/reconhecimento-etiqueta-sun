"""Pure validators: no OCR correction, quantity inference, or invented expiry dates."""
import re
from datetime import datetime

def sscc_check_digit(first17):
    if not re.fullmatch(r'[0-9]{17}',first17): raise ValueError('SSCC requires 17 ASCII data digits')
    total=sum(int(c)*(3 if i%2==0 else 1) for i,c in enumerate(reversed(first17)))
    return str((-total)%10)

def validate_sscc(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{18}',value): return {'valid':False,'reason':'requires_exactly_18_ASCII_digits','value':value}
    expected=sscc_check_digit(value[:-1]); return {'valid':value[-1]==expected,'reason':'ok' if value[-1]==expected else 'invalid_check_digit','expected_check_digit':expected,'value':value}

def sscc_from_gs1(text):
    # Restrict to explicit AI00. Never promote a GTIN14 or arbitrary 18-digit string.
    text=text.removeprefix(']C1').removeprefix(']d2')
    values=[]
    for m in re.finditer(r'(?:\(00\)|^00|\x1d00)[ \t]*([0-9][0-9 \t]*)',text):
        value=re.sub(r'\s','',m.group(1))
        if len(value)==18: values.append(value)
    return values

def printed_validity(value):
    if re.fullmatch(r'\d{1,3}\s*(?:ANO[S]?|MES(?:ES)?|MÊS|DIA[S]?)',value.upper()): return {'valid':True,'kind':'printed_duration','printed':value,'calendar_date':None}
    if re.fullmatch(r'\d{2}/\d{4}',value):
        try: datetime.strptime(value,'%m/%Y'); return {'valid':True,'kind':'printed_month_year','printed':value,'calendar_date':None}
        except ValueError: pass
    for fmt in ['%d/%m/%Y','%d/%m/%y','%d-%m-%Y','%d.%m.%Y']:
        try:
            date=datetime.strptime(value,fmt); return {'valid':True,'kind':'printed_calendar_date','printed':value,'calendar_date':date.date().isoformat()}
        except ValueError: pass
    return {'valid':False,'kind':'unparsed_printed_text','printed':value,'calendar_date':None}

def validate_fields(parsed):
    fields=parsed['fields']; issues=[]; checks={}
    for field,data in fields.items():
        candidates=data['candidates']; values=sorted({c['value'] for c in candidates})
        state='missing' if not values else ('conflicting' if len(values)>1 else 'candidate_needs_review')
        if state in ['missing','conflicting']: issues.append({'field':field,'code':state})
        checks[field]={'state':state,'values':values}
    checks['sscc']['validations']=[validate_sscc(c['value']) for c in fields['sscc']['candidates']]
    if any(not v['valid'] for v in checks['sscc']['validations']): issues.append({'field':'sscc','code':'invalid_sscc'})
    ocr={c['value'] for c in fields['sscc']['candidates'] if c['source']=='ocr'}; barcode={c['value'] for c in fields['sscc']['candidates'] if c['source']=='barcode'}
    if ocr and barcode and ocr!=barcode: issues.append({'field':'sscc','code':'ocr_barcode_disagreement','ocr':sorted(ocr),'barcode':sorted(barcode)})
    checks['validade_impressa']['validations']=[printed_validity(c['value']) for c in fields['validade_impressa']['candidates']]
    return {'fields':checks,'issues':issues,'recognition_accuracy':None,'quantity_policy':'Use printed QTDE only; never multiply LASTRO, layer count or pallet capacity.'}

