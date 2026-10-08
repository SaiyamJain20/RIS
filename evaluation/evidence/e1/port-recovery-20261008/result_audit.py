import json,hashlib,subprocess
from pathlib import Path
r=Path(__file__).resolve().parent;root=Path('/home/karma/Documents/RIS')
m=json.loads((r/'real-e1-output/manifest.json').read_text());record={'run_status':m['status'],'failure':m['failure'],'source_stable':m['sourceStable'],'profiles':{},'cleanup':[]}
for profile,row in m['profiles'].items():
 p=r/'real-e1-output'/profile
 record['profiles'][profile]={'status':row['status'],'sources_stable':row['sourcesStable'],'services_stopped':row.get('servicesStopped'),'started_service_count':sum(x['profile']==profile for x in m['servicesStarted'])}
 if (p/'bootstrap-checked.json').exists():record['profiles'][profile]['wrong_admin_code']=json.loads((p/'bootstrap-checked.json').read_text())['wrongAdminCode']
 for name in ('alice','bob'):
  f=p/name/'result.json'
  if f.exists():
   x=json.loads(f.read_text());record['profiles'][profile][name]={'ok':x['ok'],'oracle':x['oracle'],'observed_event_types':[e['type'] for e in x['observed']['events']],'delivery':x['delivery']}
 for f in p.glob('*/process.json'):
  x=json.loads(f.read_text());record['cleanup'].append({'path':str(f),'pid':x['pid'],'exit_code':x['exitCode'],'ended_at':x['endedAt'],'pid_currently_exists':Path(f"/proc/{x['pid']}").exists()})
assert m['status']=='FAILED' and m['sourceStable'] is True
assert record['profiles']['paper-strict']['status']=='CONTROL_PASS'
assert record['profiles']['paper-strict']['wrong_admin_code']=='16'
assert record['profiles']['paper-strict']['alice']['ok'] and record['profiles']['paper-strict']['bob']['ok']
assert all(x['ended_at'] and x['exit_code'] is not None and not x['pid_currently_exists'] for x in record['cleanup'])
freeze=json.loads((root/'interfaces/v1/FREEZE.json').read_text())
for path,item in freeze['frozenCopies'].items():
 source=subprocess.check_output(['git','show',item['commit']+':'+item['sourcePath']],cwd=root) if 'commit' in item else (root/item['sourcePath']).read_bytes()
 assert (root/path).read_bytes()==source
 assert hashlib.sha256((root/path).read_bytes()).hexdigest()==item['sha256']
record['frozen_copies_verified']=len(freeze['frozenCopies'])
for name in ('real-e1','full-evaluator'):
 evidence=json.loads((r/(name+'.json')).read_text());assert evidence['sources_stable'] is True
 record[name]={'exit_code':evidence['exit_code'],'seconds':evidence['seconds'],'sources_stable':True,'source_count':len(evidence['source_before'])}
record['scope']='Tested reconstruction result: three real paper-strict E1 controls only; paper-minimal/repaired-e not executed; no E2/RQ gate evidence.'
(r/'live-result-audit.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
