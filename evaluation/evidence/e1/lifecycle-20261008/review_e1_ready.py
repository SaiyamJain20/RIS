import hashlib,io,json,os,subprocess,tarfile
from pathlib import Path
from evaluation.manifests import now,record_command,sha256
ROOT=Path('/home/karma/Documents/RIS')
OUT=Path(__file__).resolve().parent
A1='ff3cb743cd31fdd7745d2d4a8ecd81af9d04584e'
A2='34de384f0af12b52f4de4559a5639388df824861'
LEDGER='91add8cc6000d1413bad2ed0aa119a5f26e8c776'
OLD='e30d00d840e76526d8f12845054bfbf92fc0621b'
commands=[]
def git(*args):
 log=OUT/'ready-command-logs'/f'{len(commands):04}.log'
 row=record_command(['git',*args],ROOT,log,timeout=30);commands.append(row)
 (OUT/'e1-ready-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 assert row['exitCode']==0,(args,row)
 return log.read_bytes()
def blob(pin,path):return git('show',pin+':'+path)
def digest(data):return hashlib.sha256(data).hexdigest()
def manifest(pin,path,expected,count):
 raw=blob(pin,path);assert digest(raw)==expected
 entries={}
 for line in raw.decode().splitlines():
  h,p=line.split(maxsplit=1);p=p.lstrip('*');assert len(h)==64 and p not in entries
  entries[p]=h;assert digest(blob(pin,p))==h,p
 assert len(entries)==count
 return entries
a=manifest(LEDGER,'ledger/evidence/source-manifest.sha256','407c86331072bdad63562541230fdd3078608287eccb373cb2f974e3bde20fc1',101)
b=manifest(A2,'protocol/evidence/source-manifest.sha256','30f76ddac08bd1a720c4b4c9479103c2663eb61b806945c0d66fe44d48e9f41a',98)
assert git('diff',OLD,A2,'--','protocol/hmbc_protocol','protocol/testtools','protocol/tools','protocol/exports')==b''
assert blob(A2,'protocol/abi/manifest.json')==blob(LEDGER,'ledger/exports/abi/manifest.json')
for role in ('RSC','TMSC','PSC','LSC','ACSC','KSSC'):
 assert blob(A2,'protocol/abi/'+role+'.json')==blob(LEDGER,'ledger/exports/abi/'+role+'.json')
assert digest(blob(A2,'protocol/exports/adapter.json'))=='7146495b4dfbe351d73299223efdb853c41895ac880f9a6c13e2a525656a9220'
messages={}
for pin,path,id in [(A1,'communication/agent-1/outbox/0028-ready-a-e1-frozen-controls.md','A1-0028'),(A2,'communication/agent-2/outbox/0014-ready-owner-service-for-e1-integration.md','A2-0014')]:
 raw=blob(pin,path);assert ('Message-ID: '+id) in raw.decode();assert 'Type: READY' in raw.decode()
 messages[id]={'commit':pin,'path':path,'sha256':digest(raw),'changeCommit':git('log','-1','--format=%H',pin,'--',path).decode().strip()}
snapshot=OUT/'e1-ready-protocol-snapshot';snapshot.mkdir()
raw=git('archive',A2,'protocol')
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:archive.extractall(snapshot,filter='data')
assert all(sha256(snapshot/p)==h for p,h in b.items())
env=dict(os.environ);env['PYTHONPATH']='.'
row=record_command([str(ROOT/'.venv/bin/python'),'-m','hmbc_protocol.export','--check'],snapshot/'protocol',OUT/'e1-ready-export-check.log',timeout=45,env=env);commands.append(row)
assert row['exitCode']==0
assert all(sha256(snapshot/p)==h for p,h in b.items())
assert sha256(ROOT/'interfaces/v1/FREEZE.json')=='f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2'
freeze=json.loads((ROOT/'interfaces/v1/FREEZE.json').read_text())
for copy in freeze['frozenCopies']:
 pass
result={'capturedAt':now(),'messages':messages,'ledger':{'commit':LEDGER,'manifestSha256':'407c86331072bdad63562541230fdd3078608287eccb373cb2f974e3bde20fc1','entries':a},'protocol':{'commit':A2,'manifestSha256':'30f76ddac08bd1a720c4b4c9479103c2663eb61b806945c0d66fe44d48e9f41a','entries':b},'productionUnchangedFrom':OLD,'abiPayloadsEqual':6,'abiInventoryEqual':True,'exportCheck':row,'sourceStable':True,'integrationFreezeAck':False,'limits':['Owner full suite1318/201 and live flow are not independently rerun here','No actual service or contract integration','No crash/fault hook reachable through process; E2/E3 remains later unproved work','Fixture bootstrap key custody needs an owner public producer'] }
(OUT/'e1-ready-review.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'e1-ready-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
print(json.dumps({'commands':len(commands),'messages':messages,'sourceStable':True}))
