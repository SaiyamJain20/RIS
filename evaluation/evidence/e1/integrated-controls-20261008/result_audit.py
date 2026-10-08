import json,hashlib,subprocess,sys
from pathlib import Path
sys.path.insert(0,'/home/karma/Documents/RIS')
from evaluation.e1 import verify_plan,_acks,_snapshot_stable
from capture import RUN,ROOT
out=RUN/'real-e1-output'
m=json.loads((out/'manifest.json').read_text());cmd=json.loads((RUN/'real-e1.json').read_text())
planpath=ROOT/'evaluation/evidence/e1/port-recovery-20261008/integration-plan.json'
plan=json.loads(planpath.read_text());verify_plan(plan);acks=_acks(RUN/'acks.json',plan,hashlib.sha256(planpath.read_bytes()).hexdigest())
record={'status':m['status'],'failure':m['failure'],'started_at':m['startedAt'],'ended_at':m['endedAt'],'source_stable':m['sourceStable'],'command_exit':cmd['exit_code'],'seconds':cmd['seconds'],'source_count':len(cmd['source_before']),'source_bracket_stable':cmd['sources_stable'],'acks':acks,'profiles':{},'cleanup':[]}
for profile,row in m['profiles'].items():
 p=out/profile
 record['profiles'][profile]={'status':row['status'],'sources_stable':row['sourcesStable'],'services_stopped':row.get('servicesStopped'),'started_service_count':sum(x['profile']==profile for x in m['servicesStarted'])}
 if (p/'bootstrap-checked.json').exists():record['profiles'][profile]['wrong_admin_code']=json.loads((p/'bootstrap-checked.json').read_text())['wrongAdminCode']
 for name in ('alice','bob'):
  f=p/name/'result.json'
  if f.exists():
   x=json.loads(f.read_text());record['profiles'][profile][name]={'ok':x['ok'],'oracle':x['oracle'],'observed_event_types':[e['type'] for e in x['observed']['events']],'delivery':x['delivery']}
 for owner in plan['owners'].values(): assert _snapshot_stable(owner,p/'snapshots'/('ledger' if 'ledger/foundry.toml' in owner['entries'] else 'protocol'))
 for f in p.glob('*/process.json'):
  x=json.loads(f.read_text());record['cleanup'].append({'path':str(f),'pid':x['pid'],'exit_code':x['exitCode'],'ended_at':x['endedAt'],'pid_currently_exists':Path(f"/proc/{x['pid']}").exists()})
assert m['status']=='E1_CONTROL_PASS' and cmd['exit_code']==0 and m['failure'] is None and m['sourceStable'] is True
assert cmd['sources_stable'] is True
assert set(m['profiles'])==set(plan['profiles']) and len(m['servicesStarted'])==6
for row in record['profiles'].values():
 assert row['status']=='CONTROL_PASS' and row['sources_stable'] is True and row['services_stopped'] is True and row['started_service_count']==2
 assert row['wrong_admin_code']=='16' and row['alice']['ok'] and row['bob']['ok']
assert len(record['cleanup'])==9
assert all(x['ended_at'] and x['exit_code']==0 and not x['pid_currently_exists'] for x in record['cleanup'])
freeze=json.loads((ROOT/'interfaces/v1/FREEZE.json').read_text())
for path,item in freeze['frozenCopies'].items():
 source=subprocess.check_output(['git','show',item['commit']+':'+item['sourcePath']],cwd=ROOT) if 'commit' in item else (ROOT/item['sourcePath']).read_bytes()
 assert (ROOT/path).read_bytes()==source
 assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==item['sha256']
record['frozen_copies_verified']=len(freeze['frozenCopies']);record['owner_snapshot_blobs_verified']=sum(len(owner['entries'])*3 for owner in plan['owners'].values())
record['classification']='tested reconstruction result; actual synthetic local two-chain C-E1 controls only'
record['limits']='All E2 catalog schedules and RQ gates NOT_RUN; symbolic completion and attempted RELEASE_SENT do not prove ABE, delivery, consensus, provider integrity or power-loss recovery.'
(RUN/'live-result-audit.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
