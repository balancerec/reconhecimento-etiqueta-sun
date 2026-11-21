import math

def area(p):return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))/2) if len(p)>2 else 0

def convex(p):
 if len(p)<3 or area(p)<4:return False
 cross=[(p[(i+1)%len(p)][0]-p[i][0])*(p[(i+2)%len(p)][1]-p[(i+1)%len(p)][1])-(p[(i+1)%len(p)][1]-p[i][1])*(p[(i+2)%len(p)][0]-p[(i+1)%len(p)][0]) for i in range(len(p))];return all(c>=0 for c in cross) or all(c<=0 for c in cross)

def iou(subject,clip):
 def signed(p):return sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))
 if not subject or not clip:return 0
 orientation=1 if signed(clip)>=0 else -1;out=[list(p) for p in subject]
 def side(a,b,p):return orientation*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
 for i,a in enumerate(clip):
  b=clip[(i+1)%len(clip)];old=out;out=[]
  if not old:break
  prev=old[-1];sp=side(a,b,prev)
  for curr in old:
   sc=side(a,b,curr)
   if (sc>=0)!=(sp>=0):
    t=sp/(sp-sc);out.append([prev[0]+t*(curr[0]-prev[0]),prev[1]+t*(curr[1]-prev[1])])
   if sc>=0:out.append(curr)
   prev=curr;sp=sc
 intersection=area(out);return intersection/max(1e-9,area(subject)+area(clip)-intersection)

def match_copies(predicted,human,threshold=.5):
 edges={i:sorted([(j,iou(p['quad_original'],h['polygon_original'])) for j,h in enumerate(human) if iou(p['quad_original'],h['polygon_original'])>=threshold],key=lambda v:(-v[1],v[0])) for i,p in enumerate(predicted)};assigned={}
 def augment(i,visited):
  for j,score in edges[i]:
   if j in visited:continue
   visited.add(j)
   if j not in assigned or augment(assigned[j],visited):assigned[j]=i;return True
  return False
 for i in range(len(predicted)):augment(i,set())
 return [(i,j,iou(predicted[i]['quad_original'],human[j]['polygon_original'])) for j,i in sorted(assigned.items())]

def score_prediction(prediction,annotation,photo_role='development'):
 human=[c for c in annotation['copies'] if c['is_label']];pred=prediction['physical_copies'];matches=match_copies(pred,human);fields=[]
 for i,j,overlap in matches:
  for f,truth in human[j]['fields'].items():
   observed=pred[i]['fields'].get(f,{});values=observed.get('qualified_values')
   if values is None:values=sorted({c.get('normalized_value',c.get('value')) for c in observed.get('candidates',[])})
   if truth['visibility']!='visible_legible':fields.append({'field':f,'status':'excluded_'+truth['visibility'],'denominator':0});continue
   state='missing' if not values else ('conflicting' if len(values)>1 else ('exact' if values[0]==truth['value'] else 'incorrect'));fields.append({'field':f,'status':state,'denominator':1,'expected':truth['value'],'values':values,'copy_id':human[j]['copy_id'],'IoU':overlap})
 # A missed human copy contributes missing visible fields, rather than disappearing from the denominator.
 matched_h={j for i,j,s in matches}
 for j,c in enumerate(human):
  if j not in matched_h:
   fields +=[{'field':f,'status':'missing_copy_detection','denominator':1,'copy_id':c['copy_id']} for f,d in c['fields'].items() if d['visibility']=='visible_legible']
 tp=len(matches);precision=tp/len(pred) if pred else None;recall=tp/len(human) if human else None
 return {'detection':{'TP':tp,'FP':len(pred)-tp,'FN':len(human)-tp,'precision':precision,'recall':recall,'F1':2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else None,'human_exhaustive':annotation['exhaustive_instance_review']},'fields':fields,'field_denominator':sum(f['denominator'] for f in fields),'exact_fields':sum(f['status']=='exact' for f in fields),'independent':photo_role=='holdout' and annotation['review_mode']=='blind' and not annotation['used_suggestions'],'dataset_role':photo_role,'integration_enabled':False}

