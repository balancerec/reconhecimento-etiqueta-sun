import re

def valid_sscc(value):
 if not isinstance(value,str) or not re.fullmatch('[0-9]{18}',value):return False
 return value[-1]==str((-sum(int(c)*(3 if i%2==0 else 1) for i,c in enumerate(reversed(value[:-1]))))%10)

def consolidate_human(copies):
 groups={}
 for c in copies:
  if not c['is_label']:continue
  sscc=c.get('confirmed_sscc')
  if not sscc and c['fields']['sscc']['visibility']=='visible_legible':sscc=c['fields']['sscc']['value']
  if not valid_sscc(sscc):continue
  g=groups.setdefault(sscc,{'sscc':sscc,'copy_ids':[],'field_values':{},'conflicts':[]});g['copy_ids'].append(c['copy_id'])
  for f,d in c['fields'].items():
   if d['visibility']=='visible_legible':g['field_values'].setdefault(f,set()).add(d['value'])
 for g in groups.values():
  g['field_values']={f:sorted(v) for f,v in g['field_values'].items()};g['conflicts']=[{'field':f,'values':v} for f,v in g['field_values'].items() if len(v)>1];q=g['field_values'].get('qtde',[]);g['quantity']=q[0] if len(q)==1 else None;g['quantity_policy']='printed-copy quantity is never summed';g['production_approved']=False
 return list(groups.values())

