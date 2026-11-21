import json,hashlib,datetime

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def event_hash(previous,event):return hashlib.sha256((previous+'\n'+canonical(event)).encode('utf-8')).hexdigest()
def verify_chain(rows):
 previous='0'*64
 for row in rows:
  event=json.loads(row['event_json'])
  if row['previous_hash']!=previous or event_hash(previous,event)!=row['event_hash']:return False
  previous=row['event_hash']
 return True

