import re

def normalize(text,field):
 text=re.sub(r'\s+',' ',text.strip())
 if field=='validade_impressa':text=re.sub(r'(?<=\d)(?=[A-Za-z])',' ',text)
 if field=='descricao':
  text=re.sub(r'(?<=[A-Za-z])(?=\d+\s*(?:ML|KG|UN|L|G)(?:\b|\d))',' ',text,flags=re.I)
  text=re.sub(r'(\d+\s*(?:ML|KG|UN|L|G))(?=\d+\b)',r'\1 ',text,flags=re.I)
 return text

def ambiguous(text,field):
 return field=='descricao' and any(re.search('[A-Za-z]',t) and re.search('[01]',t) and not re.fullmatch(r'\d+(?:ML|KG|UN|L|G)\d*',t,re.I) for t in re.findall(r'[A-Za-z0-9]+',text))

def complete(text):return bool(re.search(r'\d+\s*(?:ML|KG|UN|L|G)\s*\d+\s*$',text,re.I))

def reconstruct(blocks):
 lines=[]
 for b in sorted(blocks,key=lambda b:(sum(y for x,y in b['polygon_local'])/len(b['polygon_local']),min(x for x,y in b['polygon_local']))):
  p=b['polygon_local'];cy=sum(y for x,y in p)/len(p);hh=max(y for x,y in p)-min(y for x,y in p);line=next((l for l in lines if abs(l['cy']-cy)<max(hh,l['height'])*.45),None)
  if line is None:lines.append({'cy':cy,'height':hh,'blocks':[b]})
  else:line['blocks'].append(b)
 for line in lines:line['blocks'].sort(key=lambda b:min(x for x,y in b['polygon_local']));line['text']=' '.join(b['text'] for b in line['blocks'])
 return lines

