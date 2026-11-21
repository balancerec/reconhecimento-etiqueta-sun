from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts'/'restoration_worker.py';a=p.read_text().splitlines();
for i in range(8,19):
 if a[i].startswith(' '):a[i]=a[i][1:]
p.write_text('\n'.join(a)+'\n')

