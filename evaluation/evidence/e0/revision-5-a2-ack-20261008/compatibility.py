import ast, hashlib, json, os, subprocess, tarfile, tempfile, time
from pathlib import Path
from datetime import datetime, timezone
root=Path('/home/karma/Documents/RIS')
out=Path(__file__).resolve().parent
pin='5e203d0c0b26235c4618548a797d93201275a14d'
python=str(root/'.venv/bin/python')
commands=[]
def now(): return datetime.now(timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()
def cmd(label, argv, cwd=root, env=None, timeout=180):
    start=now()
    proc=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=timeout)
    for kind,data in [('stdout',proc.stdout),('stderr',proc.stderr)]: (out/(label+'.'+kind)).write_bytes(data)
    commands.append({'name':label,'argv':argv,'cwd':str(cwd),'environmentOverrides':env_overrides if env else {},'startedAt':start,'endedAt':now(),'exitCode':proc.returncode,'stdoutSha256':sha(proc.stdout),'stderrSha256':sha(proc.stderr),'timeoutSeconds':timeout})
    (out/'compatibility-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    if proc.returncode: raise RuntimeError(label+': '+str(proc.returncode))
    return proc.stdout
snap=Path(tempfile.mkdtemp(prefix='hmbc-agent3-a2-e0-5e203d0-'))
archive=cmd('protocol-archive',['git','archive',pin,'protocol'])
(snap/'snapshot.tar').write_bytes(archive)
with tarfile.open(snap/'snapshot.tar') as t: t.extractall(snap,filter='data')
manifest=(snap/'protocol/evidence/source-manifest.sha256').read_bytes()
assert sha(manifest)=='a352f339f3c874cbb5634efffd1478abbc0b098292ec1d7ba97d348d76b4cdac'
entries=[line.split(maxsplit=1) for line in manifest.decode().splitlines()]
def check_snapshot():
    for digest,path in entries: assert sha((snap/path.removeprefix('*')).read_bytes())==digest,path
check_snapshot()
package=json.loads((root/'interfaces/proposals/v1/review-manifest.json').read_text())['files']
for path,digest in package.items(): assert sha((root/path).read_bytes())==digest,path
selected=['test_boundary_review_r5.py','test_candidate_schema_review.py','test_exports.py','test_eip712_vs_agent1.py']
for name in selected:
    tree=ast.parse((snap/'protocol/tests'/name).read_text())
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            assert not ({a.arg for a in node.args.args}&{'ledger_chains','ledger','world'}),name
# Tests selected for E0 wire/vector/export compatibility. No service fixtures selected.
env_overrides={'PYTHONPATH':str(snap/'protocol'),'PYTHONDONTWRITEBYTECODE':'1'}
env={**os.environ,**env_overrides}
cmd('e0-wire-vector-export-tests',[python,'-m','pytest',*[str(Path('tests')/name) for name in selected],'-q','-c','pytest.ini','--rootdir','.','-p','no:cacheprovider'],cwd=snap/'protocol',env=env)
cmd('export-regeneration',[python,'-m','hmbc_protocol.export','--check'],cwd=snap/'protocol',env=env)
from evaluation.schema import validate_json_line,validate_response
from eth_account import Account
from eth_account.messages import encode_typed_data,_hash_eip191_message
rows=[]
for path in sorted((snap/'protocol/exports/examples').glob('*.json')):
    doc=json.loads(path.read_text())
    for case in doc['cases']:
        resp=case['response']; req=case['request']
        try: validate_json_line('AdapterRequest',json.dumps(req)); req_ok=True
        except (ValueError,__import__('jsonschema').ValidationError): req_ok=False
        validate_response(doc['operation'],resp)
        malformed=not resp['ok'] and resp['error']['code']=='MALFORMED'
        assert req_ok != malformed,(path,case['case'])
        rows.append({'operation':doc['operation'],'case':case['case'],'requestValid':req_ok,'responseValid':True,'ownerResponseCode':None if resp['ok'] else resp['error']['code']})
assert len(rows)==16
example=json.loads((snap/'protocol/exports/examples/prepare_request.json').read_text())['cases'][0]
result=example['response']['result']; request=result['request']
signed=json.loads((root/'interfaces/vectors/eip712-agent1-candidate.json').read_text())['vectors']
typed=next(v['typedData'] for v in signed if v['name']=='AccessRequest')
import copy
typed=copy.deepcopy(typed)
typed['domain']={'name':'HMBCRequest','version':'1','chainId':int(request['sourceChainId']),'verifyingContract':request['psc']}
uints={f['name'] for f in typed['types']['AccessRequest'] if f['type'].startswith('uint')}
typed['message']={k:int(v) if k in uints else v for k,v in request.items()}
signable=encode_typed_data(full_message=typed)
assert '0x'+_hash_eip191_message(signable).hex()==result['requestDigest']
assert Account.recover_message(signable,signature=result['signature']).lower()==result['signer']==request['gid']
check_snapshot()
for path,digest in package.items(): assert sha((root/path).read_bytes())==digest,path
report={'endedAt':now(),'peerPin':pin,'peerManifestSha256':sha(manifest),'snapshot':str(snap),'snapshotEntries':len(entries),'sourceStable':True,'packageStable':True,'rootLockSha256':sha((root/'uv.lock').read_bytes()),'pythonVersion':subprocess.check_output([python,'--version'],text=True).strip(),'selectedTests':selected,'examples':rows,'independentPrepareRequestDigestAndRecovery':True,'scope':'E0 non-live wire/vector/export compatibility only; owner candidate services NOT executed. No peer-internal imports by production evaluator; snapshot test imports are isolated verification only.','limits':'No live chains, worker recovery, paper-profile or repaired service scenarios, mutation runner, formal proof or gate result. Owner A2-0009 execution claims remain owner evidence.'}
(out/'compatibility.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'snapshot':str(snap),'sourceStable':True,'examplesValidated':len(rows),'commands':len(commands),'sha256':sha((out/'compatibility.json').read_bytes())},indent=2))
