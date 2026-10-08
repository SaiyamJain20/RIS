import socket,subprocess,json
from pathlib import Path
r=Path(__file__).resolve().parent
out={}
for name,args in [('listeners',['ss','-ltnp','( sport = :18545 or sport = :28545 )']),('time_wait',['ss','-tan','state','time-wait','( sport = :18545 or sport = :28545 )'])]:
 p=subprocess.run(args,capture_output=True,text=True);out[name]={'argv':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
for port in (18545,28545):
 for reuse in (False,True):
  with socket.socket() as s:
   if reuse:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
   try:s.bind(('127.0.0.1',port));result='bind succeeded'
   except OSError as e:result=dict(errno=e.errno,message=str(e))
  out[str((port,reuse))]=result
(r/'port-diagnosis.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
