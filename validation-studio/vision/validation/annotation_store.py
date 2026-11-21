import sqlite3,json,threading,hashlib
from pathlib import Path
from .audit_log import canonical,event_hash,now,verify_chain
class RevisionConflict(Exception):pass
class AnnotationStore:
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock()
  with self.connect() as db:
   db.executescript('''PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY,photo_id TEXT NOT NULL,revision INTEGER NOT NULL,status TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,reviewer TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(photo_id,revision));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,event_json TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL UNIQUE);
CREATE TRIGGER IF NOT EXISTS immutable_revisions_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'immutable revision'); END;
CREATE TRIGGER IF NOT EXISTS immutable_revisions_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'immutable revision'); END;
CREATE TRIGGER IF NOT EXISTS immutable_audit_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'immutable audit'); END;
CREATE TRIGGER IF NOT EXISTS immutable_audit_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'immutable audit'); END;''')
 def connect(self):
  db=sqlite3.connect(self.path,timeout=20);db.row_factory=sqlite3.Row;return db
 def latest(self,photo_id):
  with self.connect() as db:r=db.execute('SELECT * FROM revisions WHERE photo_id=? ORDER BY revision DESC LIMIT 1',(photo_id,)).fetchone()
  return self.decode(r) if r else None
 def decode(self,r):return {'revision':r['revision'],'status':r['status'],'annotation':json.loads(r['payload_json']),'sha256':r['payload_sha256'],'reviewer':r['reviewer'],'created_at':r['created_at']}
 def history(self,photo_id):
  with self.connect() as db:rows=db.execute('SELECT * FROM revisions WHERE photo_id=? ORDER BY revision DESC',(photo_id,)).fetchall()
  return [self.decode(r) for r in rows]
 def append(self,payload,status):
  with self.lock,self.connect() as db:
   db.execute('BEGIN IMMEDIATE');r=db.execute('SELECT revision FROM revisions WHERE photo_id=? ORDER BY revision DESC LIMIT 1',(payload['photo_id'],)).fetchone();current=r['revision'] if r else 0
   if payload['expected_revision']!=current:raise RevisionConflict('A foto foi alterada em outra aba. Recarregue antes de salvar.')
   revision=current+1;text=canonical(payload);digest=hashlib.sha256(text.encode()).hexdigest();timestamp=now();db.execute('INSERT INTO revisions(photo_id,revision,status,payload_json,payload_sha256,reviewer,created_at) VALUES(?,?,?,?,?,?,?)',(payload['photo_id'],revision,status,text,digest,payload['reviewer'],timestamp));self._event(db,{'type':'annotation_'+status,'photo_id':payload['photo_id'],'revision':revision,'payload_sha256':digest,'reviewer':payload['reviewer'],'timestamp':timestamp})
  return self.latest(payload['photo_id'])
 def _event(self,db,event):
  row=db.execute('SELECT event_hash FROM audit ORDER BY id DESC LIMIT 1').fetchone();previous=row['event_hash'] if row else '0'*64;db.execute('INSERT INTO audit(event_json,previous_hash,event_hash) VALUES(?,?,?)',(canonical(event),previous,event_hash(previous,event)))
 def record_event(self,event):
  with self.lock,self.connect() as db:db.execute('BEGIN IMMEDIATE');self._event(db,{**event,'timestamp':now()})
 def audit(self):
  with self.connect() as db:rows=[dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id')]
  return {'events':rows,'hash_chain_valid':verify_chain(rows),'scope':'tamper-evident sequence, not verified personal identity or digital signature'}
 def all_latest(self):
  with self.connect() as db:rows=db.execute('SELECT r.* FROM revisions r JOIN (SELECT photo_id,MAX(revision) revision FROM revisions GROUP BY photo_id) x ON r.photo_id=x.photo_id AND r.revision=x.revision').fetchall()
  return [self.decode(r) for r in rows]

