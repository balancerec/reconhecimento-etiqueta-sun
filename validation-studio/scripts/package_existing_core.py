from pathlib import Path
import importlib.metadata as md,zipfile,os,csv,io,hashlib,base64,json
R=Path(os.environ['TEMP'])/'sun-v26-studio-20261120-01';d=md.distribution('pydantic-core');wheel=d.read_text('WHEEL');tag=next(s[5:] for s in wheel.splitlines() if s.startswith('Tag: ') and 'cp312' in s);name='pydantic_core-'+d.version+'-'+tag+'.whl';out=R/'wheelhouse'/name;entries=[];record_name=None
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for f in d.files:
  rel=str(f).replace('\\','/')
  if '..' in Path(rel).parts or '__pycache__' in rel:continue
  if rel.endswith('.dist-info/RECORD'):record_name=rel;continue
  p=Path(d.locate_file(f))
  if not p.is_file():continue
  data=p.read_bytes();z.writestr(rel,data);entries.append((rel,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(),len(data)))
 buf=io.StringIO();writer=csv.writer(buf,lineterminator='\n');writer.writerows(entries);writer.writerow([record_name,'','']);z.writestr(record_name,buf.getvalue())
(R/'data/repacked-core-provenance.json').write_text(json.dumps({'distribution':'pydantic-core','version':d.version,'source':'existing bundled Python distribution, unchanged','wheel':name,'tag':tag,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'network_used':False},indent=2),encoding='utf-8');print(name)

