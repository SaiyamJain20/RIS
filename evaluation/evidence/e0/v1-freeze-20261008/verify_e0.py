from pathlib import Path
import datetime,hashlib,importlib.metadata,io,json,os,subprocess,sys,tarfile
ROOT=Path('/home/karma/Documents/RIS')
RUN=Path(__file__).resolve().parent
PY=str(ROOT/'.venv/bin/python')
records=[]
def h(data):return hashlib.sha256(data).hexdigest()
def call(name,argv,cwd=ROOT,expected=0,env=None,timeout=180):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(argv,cwd=cwd,capture_output=True,env=env,timeout=timeout)
 for suffix,data in [('stdout',p.stdout),('stderr',p.stderr)]: (RUN/f'{name}.{suffix}').write_bytes(data)
 r=dict(name=name,argv=argv,cwd=str(cwd),startedAt=start,endedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,expectedExit=expected,stdoutSha256=h(p.stdout),stderrSha256=h(p.stderr))
 records.append(r);(RUN/'verification-commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print(name,p.returncode,p.stdout.decode(errors='replace')[-350:].strip(),flush=True)
 assert p.returncode==expected,(name,p.returncode,p.stderr.decode()[-800:])
 return p.stdout
assert call('branch-check',['git','branch','--show-current']).decode().strip()=='agent-3'
assert call('clean-check',['git','status','--porcelain=v1'])==b''
manifest_path='interfaces/proposals/v1/revision6/review-manifest.json'
manifest_bytes=(ROOT/manifest_path).read_bytes()
assert h(manifest_bytes)=='df2a306fd77937572346cf5e91e9354536988af63ed660e14d51e04350161c62'
package=json.loads(manifest_bytes)
pre={p:h((ROOT/p).read_bytes()) for p in package['files']}
assert pre==package['files']
snapshots={};owner_audits={}
for owner,commit,expected in [('ledger','91add8cc6000d1413bad2ed0aa119a5f26e8c776','407c86331072bdad63562541230fdd3078608287eccb373cb2f974e3bde20fc1'),('protocol','f69e25027ff98a611774ad45924615eb2af37d89','b4757c18887956e1da67b7b140c4674a2970d793e6684bcc8e17ec90db442f46')]:
 blob=call(owner+'-manifest',['git','show',commit+':'+owner+'/evidence/source-manifest.sha256'])
 assert h(blob)==expected
 entries={}
 for line in blob.decode().splitlines():
  digest,path=line.split('  ',1);assert path.startswith(owner+'/') and '..' not in Path(path).parts
  assert path not in entries;entries[path]=digest
 archive=call(owner+'-archive',['git','archive',commit,owner])
 snap=RUN/(owner+'-snapshot');snap.mkdir(exist_ok=False)
 with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(snap,filter='data')
 hashes={p:h((snap/p).read_bytes()) for p in entries};assert hashes==entries
 (RUN/(owner+'-source-manifest.sha256')).write_bytes(blob)
 snapshots[owner]=snap
 owner_audits[owner]=dict(commit=commit,manifestSha256=expected,entries=entries,preHashes=hashes)
# Shared ABI payload agreement; metadata labels are an explicit owner-local migration.
for name in ['ACSC','KSSC','LSC','PSC','RSC','TMSC']:
 a=snapshots['ledger']/f'ledger/exports/abi/{name}.json';b=snapshots['protocol']/f'protocol/abi/{name}.json'
 assert a.read_bytes()==b.read_bytes(),name
call('protocol-diff',['git','diff','a4dcade3dc3bf01e172a4a5ba30a40fc7ad97292','f69e25027ff98a611774ad45924615eb2af37d89','--','protocol'])
scan=json.loads((RUN/'peer-communication.json').read_text())
messages={}
for p,r in scan['files'].items():
 if '/outbox/' in p and p.endswith('.md'):
  data=call('message-'+p.split('/')[1]+'-'+Path(p).stem,['git','show',r['commit']+':'+p])
  if '\nTo: all\n' in data.decode() or any('agent-3' in l for l in data.decode().splitlines() if l.startswith('To:')):
   messages[p]={k:r[k] for k in ['commit','changeCommit','sha256']}
assert not scan['missingBranches'] and not any(r['divergentRevisions'] for r in scan['files'].values())
assert 'df2a306fd77937572346cf5e91e9354536988af63ed660e14d51e04350161c62' in (RUN/'a2-0012.md').read_text()
tc=json.loads((ROOT/'evaluation/toolchain.json').read_text())
for item in tc['foundry']['binaryPaths'].values():assert h(Path(item['path']).read_bytes())==item['sha256']
assert h(Path(tc['solc']['path']).read_bytes())==tc['solc']['sha256']
assert h(Path(tc['proverif']['path']).read_bytes())==tc['proverif']['binarySha256']
versions=dict(python=sys.version,packages={x:importlib.metadata.version(x) for x in ['eth-account','jsonschema','pytest','eth-abi']})
call('git-version',['git','--version'])
call('python-version',[PY,'--version'])
call('forge-version',[tc['foundry']['binaryPaths']['forge']['path'],'--version'])
call('solc-version',[tc['solc']['path'],'--version'])
call('owned-tests',[PY,'-m','pytest','evaluation/tests','-q','-p','no:cacheprovider'])
call('peer-nonlive-tests',[PY,'-m','pytest','-c','pytest.ini','--rootdir','.','tests/test_boundary_review_r5.py','tests/test_candidate_schema_review.py','tests/test_exports.py','tests/test_eip712_vs_agent1.py','tests/test_symbolic.py','tests/test_adapter.py','tests/test_adapter_hardening.py','tests/test_messages_keys.py','-q','-p','no:cacheprovider'],cwd=snapshots['protocol']/'protocol')
call('peer-exports',[PY,'-m','hmbc_protocol.export','--check'],cwd=snapshots['protocol']/'protocol')
call('vectors',[PY,'-m','evaluation.vectors','interfaces/vectors/eip712-agent1-candidate.json','--output',str(RUN/'vectors.json')])
call('schema-cases',[PY,'-m','evaluation.check_schema_vectors','interfaces/vectors/schema-candidate.json','interfaces/vectors/boundary-candidate.json','--output',str(RUN/'schema-results.json')],timeout=300)
call('generator',[PY,'interfaces/proposals/build_boundary_vectors.py','--check'])
call('prompts',[PY,'communication/build_prompts.py','--check'])
forge=tc['foundry']['binaryPaths']['forge']['path']
env={k:v for k,v in os.environ.items() if not k.startswith('FOUNDRY_')};env['FOUNDRY_PROFILE']='default';env['PATH']=str(Path(forge).parent)+os.pathsep+env.get('PATH','')
call('ledger-tests',[forge,'test','--offline','--root',str(snapshots['ledger']/'ledger')],env=env)
call('cast-vectors',[PY,'-I',str(snapshots['ledger']/'ledger/tools/crosscheck_cast.py')],env=env)
call('proverif-smoke',[tc['proverif']['path'],str(ROOT/'evaluation/models/e0/smoke.pv')])
pv=(RUN/'proverif-smoke.stdout').read_text();assert 'RESULT not attacker(publicToken[]) is false.' in pv and 'RESULT not attacker(secretToken[]) is true.' in pv
for owner,audit in owner_audits.items():
 audit['postHashes']={p:h((snapshots[owner]/p).read_bytes()) for p in audit['entries']}
 audit['sourceStable']=audit['postHashes']==audit['preHashes'];assert audit['sourceStable']
post={p:h((ROOT/p).read_bytes()) for p in package['files']};assert pre==post
call('post-fetch',['git','fetch','origin'])
call('post-scan',[PY,'-m','evaluation.peers','--output',str(RUN/'post-test-peer-communication.json')])
new=json.loads((RUN/'post-test-peer-communication.json').read_text());delta={p:r for p,r in new['files'].items() if scan['files'].get(p,{}).get('sha256')!=r['sha256']}
result=dict(capturedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),packageManifestSha256=h(manifest_bytes),packagePre=pre,packagePost=post,sourceStable=pre==post,owners=owner_audits,messages=messages,versions=versions,postTestChanges=delta,commands=records,helperSha256=h(Path(__file__).read_bytes()),scope='E0 compatibility, source/ABI/hash review and module checks only; no services, live scenarios, formal correspondence, recovery or RQ gate',fixtures='synthetic only; seed none; E symbolic mode',ok=True)
(RUN/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('VERIFIED',json.dumps(dict(packageFiles=len(pre),ownerEntries={k:len(v['entries']) for k,v in owner_audits.items()},postTestChanged=list(delta))),flush=True)
