import re
from .anchor_detector import box

def valid_value(field,text):
 text=text.strip().strip(':')
 if field=='sku':return bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./_-]{1,31}',text))
 if field in ['qtde','lastro']:return bool(re.fullmatch(r'\d{1,9}',text))
 if field in ['lote','documento_entrada']:return bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./_-]{1,31}',text))
 return False

def assign_spatial(blocks,anchors,width,height):
 result=[];anchor_ids={a['block_id'] for a in anchors}
 for a in anchors:
  f=a['field']
  if f not in ['sku','qtde','lastro','lote','documento_entrada']:continue
  ax,ay,axx,ayy=a['box'];hh=max(1,ayy-ay);cy=(ay+ayy)/2;right=width
  competitors=[other['box'][0] for other in anchors if other is not a and other['box'][0]>axx and abs((other['box'][1]+other['box'][3])/2-cy)<hh]
  # BT caption separates quantity from batch/lot columns even when not a field.
  competitors +=[box(b)[0] for b in blocks if re.fullmatch(r'BT\s*[:.]?',b['text'].strip(),re.I) and box(b)[0]>axx and abs((box(b)[1]+box(b)[3])/2-cy)<hh]
  if competitors:right=min(competitors)
  for b in blocks:
   if b['id'] in anchor_ids:continue
   x,y,xx,yy=box(b);text=b['text'].strip()
   if not valid_value(f,text) or x<axx-width*.025 or x>right or abs((y+yy)/2-cy)>hh*.85:continue
   if x-axx>width*(.35 if f=='sku' else .40):continue
   # A bottom-of-label 14-digit print and an 18-digit SSCC cannot be promoted by proximity.
   if f=='sku' and len(re.sub(r'\D','',text)) in [14,18] and y>height*.25:continue
   result.append({'field':f,'value':text,'block':b,'anchor':a,'distance':max(0,x-axx)/max(1,width)+abs((y+yy)/2-cy)/hh})
 return result

def dedicated_rois(blocks,anchors,width,height):
 rois=[]
 for a in anchors:
  ax,ay,axx,ayy=a['box'];hh=max(5,ayy-ay);cy=(ay+ayy)/2;f=a['field'];right=width
  if f=='sku':
   # SKU and description are separate ROIs; use observed same-row identifier to separate them.
   nums=[b for b in blocks if valid_value('sku',b['text']) and re.search(r'\d',b['text']) and box(b)[0]>=axx-width*.02 and box(b)[0]-axx<width*.30 and abs((box(b)[1]+box(b)[3])/2-cy)<hh*.8]
   end=max([box(b)[2] for b in nums]+[axx+width*.16]);rois.append({'field':'sku','box':[int(axx),max(0,int(cy-hh*.8)),min(width,int(end+hh*.2)),min(height,int(cy+hh*.8))],'anchor':a})
   if end<width*.8:rois.append({'field':'descricao','box':[max(0,int(end+hh*.1)),max(0,int(cy-hh*.85)),width,min(height,int(cy+hh*.85))],'anchor':a})
  elif f in ['qtde','lastro','lote','validade_impressa']:
   competitors=[b for b in blocks if box(b)[0]>axx+hh*.1 and abs((box(b)[1]+box(b)[3])/2-cy)<hh*.8 and (re.fullmatch(r'BT\s*[:.]?',b['text'].strip(),re.I) or any(o['block_id']==b['id'] for o in anchors))]
   if competitors:right=min(box(b)[0] for b in competitors)
   if f in ['qtde','lastro']:right=min(right,axx+width*.33)
   rois.append({'field':f,'box':[max(0,int(axx+hh*.08)),max(0,int(cy-hh*.85)),min(width,int(right-hh*.08)),min(height,int(cy+hh*.85))],'anchor':a})
 return [r for r in rois if r['box'][2]-r['box'][0]>5 and r['box'][3]-r['box'][1]>5]

