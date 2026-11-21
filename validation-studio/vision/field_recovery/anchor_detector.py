"""Context-specific caption recognition. Payload characters are never replaced."""
import re

def box(block):
 p=block['polygon_local'];return min(x for x,y in p),min(y for x,y in p),max(x for x,y in p),max(y for x,y in p)

def detect_anchors(blocks,width,height):
 anchors=[]
 for b in blocks:
  text=b['text'];head=text.split(':',1)[0].strip();letters=re.sub('[^A-Z]','',head.upper());x,y,xx,yy=box(b);field=None;rule=None
  if re.search(r'\bITEM\b',text,re.I):field='sku';rule='literal_ITEM'
  elif letters in ['IITM','IIEM','IITEM','1TEM','TEM'] and x<width*.35 and y<height*.3 and re.search('[:.]',text):
   near=[n for n in blocks if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./_-]{1,31}',n['text'].strip()) and box(n)[0]>=xx-width*.02 and box(n)[0]-xx<width*.3 and abs((box(n)[1]+box(n)[3]-y-yy)/2)<max(1,yy-y)*.85]
   if near:field='sku';rule='degraded_ITEM_caption_with_nearby_identifier'
  elif re.fullmatch(r'\s*(?:QTDE|QTD|OTDE|0TDE)\s*[:.]?\s*',text,re.I):field='qtde';rule='QTDE_caption_only_alias' if 'QT' not in text.upper() else 'literal_QTDE'
  elif re.search(r'\bLASTRO\b',text,re.I):field='lastro';rule='literal_LASTRO'
  elif re.fullmatch(r'\s*(?:LOTE|LT|L1|L7)\s*[:.]?\s*',text,re.I) and x>width*.5 and y<height*.4:field='lote';rule='right_header_LOTE_caption'
  elif re.search('ENTRADA',text,re.I):field='documento_entrada';rule='literal_ENTRADA_caption_prefix_only'
  elif re.search('VALIDADE',text,re.I):field='validade_impressa';rule='literal_VALIDADE'
  if field:anchors.append({'field':field,'block_id':b['id'],'raw_anchor_text':text,'normalized_anchor':{'sku':'ITEM','qtde':'QTDE','lastro':'LASTRO','lote':'LOTE','documento_entrada':'DOC. ENTRADA','validade_impressa':'VALIDADE'}[field],'rule':rule,'box':(x,y,xx,yy),'polygon_local':b['polygon_local'],'confidence_raw':b.get('confidence')})
 return anchors

