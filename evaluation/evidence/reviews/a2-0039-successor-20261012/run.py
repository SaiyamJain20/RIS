import subprocess,json,sys,datetime,hashlib
from pathlib import Path
base=Path(__file__).resolve().parent
label,cwd,*argv=sys.argv[1:]
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
p=subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(base/(label+'.log')).write_bytes(p.stdout)
(base/(label+'.json')).write_text(json.dumps({'argv':argv,'cwd':cwd,'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':p.returncode,'outputSha256':hashlib.sha256(p.stdout).hexdigest()},indent=2)+'\n')
print(p.stdout.decode(errors='replace')); print('Recorded exit:',p.returncode)
sys.exit(p.returncode)
