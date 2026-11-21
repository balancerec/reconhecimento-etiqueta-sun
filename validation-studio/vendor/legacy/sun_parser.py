"""Spatial SUN parser. Every output is a traceable candidate, not ground truth."""
import re,unicodedata
from sun_validator import sscc_from_gs1,printed_validity
FIELDS=('sku','descricao','qtde','lastro','lote','documento_entrada','validade_impressa','sscc')
ANCHOR=re.compile(r'(?<!\w)(?P<sku>ITEM|SKU)\b|(?<!\w)(?P<qtde>QTDE|QTD|QUANTIDADE)\b|(?<!\w)(?P<lastro>LASTRO)\b|(?<!\w)(?P<lote>LOTE|LT)\b|(?<!\w)(?P<documento_entrada>(?:DOC\.?\s*)?ENTRADA)\b|(?<!\w)(?P<validade_impressa>VALIDADE|VAL\.)\b|(?<!\w)(?P<sscc>SSCC(?:\s*[-:]?\s*18)?)\b|(?<!\w)(?P<descricao>DESCRICAO|PRODUTO)\b',re.I)
CAPACITY=re.compile(r'CAIXAS?\s+POR\s+PAL|CAPACIDADE|LASTROS?\s+POR|EMPILHAMENTO|ALTURA|CAMADAS?\s*[:=]',re.I)
def normal(s): return ''.join(c for c in unicodedata.normalize('NFD',s.upper()) if unicodedata.category(c)!='Mn')
def box(block):
    pts=block.get('polygon_local',block.get('polygon',[])); xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    return min(xs),min(ys),max(xs),max(ys)
def typed(field,text):
    text=text.strip(' \t:;.-'); text=re.sub(r'\s+',' ',text)
    if field in ('sku','documento_entrada'): return re.match(r'[0-9]{3,20}(?![0-9])',text).group() if re.match(r'[0-9]{3,20}(?![0-9])',text) else None
    if field in ('qtde','lastro'): return text if re.fullmatch(r'[0-9]{1,7}',text) else None
    if field=='lote': return text if re.fullmatch(r'[A-Z0-9][A-Z0-9./-]{1,30}',text.upper()) and re.search(r'[0-9]',text) else None
    if field=='validade_impressa': return text if printed_validity(text)['valid'] else None
    if field=='sscc':
        explicit=sscc_from_gs1(text)
        if explicit: return explicit[0]
        clean=re.sub(r'\s','',text); return clean if re.fullmatch(r'[0-9]{18}',clean) else None
    if field=='descricao': return text if len(text)>=8 and re.search(r'[A-Za-z]{3}',text) and not CAPACITY.search(normal(text)) else None

def parse_sun(blocks,barcodes=(),label_id='label-0'):
    fields={f:{'candidates':[]} for f in FIELDS}; rejected=[]; anchors=[]; used=set()
    def add(f,value,b,method,anchor=None,distance=None):
        if value is None: return
        item={'value':value,'source':'ocr','block_id':b['id'],'label_id':label_id,'confidence':float(b['confidence']),'method':method,'polygon_original':b.get('polygon_original',b.get('polygon')),'anchor_block_id':anchor,'spatial_distance':distance}
        if not any(c['value']==value and c.get('block_id')==b['id'] for c in fields[f]['candidates']): fields[f]['candidates'].append(item)
    for b in blocks:
        text=normal(b['text'])
        if CAPACITY.search(text): continue
        matches=list(ANCHOR.finditer(text))
        for i,m in enumerate(matches):
            f=m.lastgroup; raw=b['text'][m.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip(' :;.-')
            value=typed(f,raw)
            if value is not None: add(f,value,b,'explicit_same_block'); used.add(b['id'])
            else:
                anchors.append((f,b))
                if raw: rejected.append({'field':f,'text':raw,'block_id':b['id'],'reason':'type_mismatch_not_corrected'})
            if f=='sku' and value is not None:
                desc=raw[len(value):].strip(' :-'); add('descricao',typed('descricao',desc),b,'description_after_item')
    # Associate only within this rectified label, and only with a compatible value type.
    for f,anchor in anchors:
        ax,ay,axx,ayy=box(anchor); ah=max(1,ayy-ay); ranked=[]
        for b in blocks:
            if b['id']==anchor['id'] or ANCHOR.search(normal(b['text'])) or CAPACITY.search(normal(b['text'])): continue
            value=typed(f,b['text'])
            if value is None: continue
            bx,by,bxx,byy=box(b); cy=(by+byy)/2; acy=(ay+ayy)/2
            right=0<=bx-axx<ah*9 and abs(cy-acy)<ah*.75
            below=-ah*.25<=by-ayy<ah*3 and min(axx,bxx)>max(ax,bx)
            if not (right or below): continue
            # A value in another column is not allowed to cross a competing typed anchor.
            competing=False
            for other_f,other in anchors:
                if other['id']==anchor['id'] or other_f==f: continue
                ox,oy,oxx,oyy=box(other)
                if below and min(oxx,bxx)>max(ox,bx) and abs((oy+oyy)/2-acy)<ah and abs((ox+oxx-bx-bxx)/2)<abs((ax+axx-bx-bxx)/2): competing=True
            if competing: continue
            distance=(max(0,bx-axx)/ah+abs(cy-acy)/ah) if right else ((by-ayy)/ah+abs((bx+bxx-ax-axx)/2)/max(1,axx-ax)+.4)
            ranked.append((distance,b,value))
        if ranked:
            best=min(x[0] for x in ranked)
            for distance,b,value in ranked:
                if distance<=best+.35: add(f,value,b,'spatial_candidate',anchor['id'],round(distance,3)); used.add(b['id'])
    # Description without a printed header remains explicitly heuristic.
    if not fields['descricao']['candidates']:
        for b in blocks:
            text=normal(b['text'])
            if b['id'] not in used and not ANCHOR.search(text) and not CAPACITY.search(text) and re.search(r'\d+\s*(?:ML|L|G|KG|UN)\b',text): add('descricao',typed('descricao',b['text']),b,'product_units_heuristic')
    for barcode in barcodes:
        for value in sscc_from_gs1(barcode['text']): fields['sscc']['candidates'].append({'value':value,'source':'barcode','label_id':label_id,'confidence':None,'method':'GS1_AI00','barcode':barcode})
    for data in fields.values():
        values={c['value'] for c in data['candidates']}; data['status']='missing' if not values else ('conflicting' if len(values)>1 else 'candidate_needs_review')
    return {'label_id':label_id,'fields':fields,'rejected_candidates':rejected,'policy':'No fabricated values, no inferred calendar expiry, no capacity substitution; review required.'}

