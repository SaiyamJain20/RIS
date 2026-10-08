"""Review A2-0013 and reproduce only its E0 export tests; no live fixture."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
from jsonschema import ValidationError
from datetime import datetime, timezone
from evaluation.schema import validate, validate_response

ROOT=Path('/home/karma/Documents/RIS')
RUN=Path(__file__).resolve().parent
PIN='e30d00d840e76526d8f12845054bfbf92fc0621b'
OLD='f69e25027ff98a611774ad45924615eb2af37d89'
BASE='f7b8f3fd74ae3dd52e385cd013a6429415b519a2'
ACK='communication/agent-2/outbox/0013-ack-frozen-v1-mapping-and-v1-export-successor.md'
commands=[]

def sha(data):return hashlib.sha256(data).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def save(name,value):(RUN/name).write_text(json.dumps(value,indent=2)+'\n')
def call(argv,cwd=ROOT,label=None,env=None):
    label='retry-'+(label or f'successor-read-{len(commands)+1:04}')
    started=now();p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=120)
    (RUN/(label+'.stdout')).write_bytes(p.stdout);(RUN/(label+'.stderr')).write_bytes(p.stderr)
    commands.append({'argv':argv,'cwd':str(cwd),'startedAt':started,'endedAt':now(),'exitCode':p.returncode,
                     'stdoutSha256':sha(p.stdout),'stderrSha256':sha(p.stderr),
                     'stdoutPath':label+'.stdout','stderrPath':label+'.stderr'})
    save('successor-commands.json',commands)
    assert p.returncode==0,(label,p.returncode,p.stderr[-200:])
    return p.stdout
def blob(commit,path):return call(['git','show',commit+':'+path])

def main():
    initial=json.loads((RUN/'review.json').read_text())
    scan=json.loads((RUN/'pre-edit-peer-communication.json').read_text())
    assert scan['branches']['origin/agent-2']==PIN
    assert not any(x['ambiguous'] or x['divergentRevisions'] for x in scan['files'].values())
    raw=blob(PIN,ACK);text=raw.decode();(RUN/Path(ACK).name).write_bytes(raw)
    for token in [initial['freezeSha256'],BASE,'Message-ID: A2-0013','Type: ACK','15 frozenCopies','NOT ACKED / excluded']:
        assert token in text
    freeze=(ROOT/'interfaces/v1/FREEZE.json').read_bytes()
    assert sha(freeze)==initial['freezeSha256']
    manifest=blob(PIN,'protocol/evidence/source-manifest.sha256')
    assert sha(manifest)=='140bb7623bbba5f64c7e3e0a5f08d7c972a94ec50d20cc9e50a0e21aad404063'
    entries={}
    for line in manifest.decode().splitlines():
        expected,path=line.split(None,1);assert path.startswith('protocol/') and path not in entries
        assert sha(blob(PIN,path))==expected
        entries[path]=expected
    assert len(entries)==98
    changed=call(['git','diff','--name-only',OLD,PIN,'--','protocol/']).decode().splitlines()
    production=[p for p in changed if p.startswith(('protocol/hmbc_protocol/','protocol/testtools/','protocol/tools/'))]
    assert production==['protocol/hmbc_protocol/export.py']
    source_diff=call(['git','diff',OLD,PIN,'--','protocol/hmbc_protocol/export.py']).decode()
    adapter_raw=blob(PIN,'protocol/exports/adapter.json');adapter=json.loads(adapter_raw)
    assert sha(adapter_raw)=='7146495b4dfbe351d73299223efdb853c41895ac880f9a6c13e2a525656a9220'
    assert adapter['interfaceVersion']=='v1' and 'no owner service READY' in adapter['serviceStatus']
    assert adapter['freeze']['freezeJsonSha256']==initial['freezeSha256']
    assert adapter['freeze']['publicationCommit']==BASE
    assert blob(PIN,'protocol/tests/fixtures/freeze-a3-f7b8f3f-v1.json')==freeze
    deployment=blob(PIN,'protocol/tests/fixtures/deployment-agent1-91add8c-v1-repaired-e.json')
    assert deployment==blob('91add8cc6000d1413bad2ed0aa119a5f26e8c776','ledger/exports/deployments/sample-repaired-e/deployment.json')
    archive=RUN/'successor-protocol.tar';archive.write_bytes(call(['git','archive',PIN,'protocol/'],label='successor-archive'))
    snapshot=RUN/'protocol-successor-retry';snapshot.mkdir()
    with tarfile.open(archive) as tar:tar.extractall(snapshot,filter='data')
    def hash_snapshot():return {p:sha((snapshot/p).read_bytes()) for p in entries}
    before=hash_snapshot();assert before==entries
    tests=blob(PIN,'protocol/tests/test_exports.py').decode()
    assert 'world' not in tests and 'ledger_world' not in tests
    python=str(ROOT/'.venv/bin/python');env={**os.environ,'PYTHONPATH':str(snapshot/'protocol'),'PYTHONDONTWRITEBYTECODE':'1'}
    output=call([python,'-m','pytest','tests/test_exports.py','-q','-c','pytest.ini','--rootdir','.','-p','no:cacheprovider'],cwd=snapshot/'protocol',label='successor-export-tests',env=env).decode()
    assert '12 passed' in output,output
    export_result=call([python,'-m','hmbc_protocol.export','--check'],cwd=snapshot/'protocol',label='successor-export-regeneration',env=env).decode()
    examples=[]
    for p in sorted((snapshot/'protocol/exports/examples').glob('*.json')):
        example=json.loads(p.read_text())
        for case in example['cases']:
            try:
                validate('AdapterRequest',case['request'])
                request_valid=True
            except (ValueError,ValidationError):
                request_valid=False
            response=case['response']
            expected_valid=not (response['ok'] is False and response['error']['code']=='MALFORMED')
            assert request_valid is expected_valid,(example['operation'],case['case'])
            validate_response(example['operation'],response)
            assert case['request']['deploymentManifest']==json.loads(deployment)
            examples.append({'operation':example['operation'],'case':case['case'],
                             'requestValid':request_valid,'responseValid':True,'verdict':'EXPECTED'})
    assert len(examples)==16
    after=hash_snapshot();assert before==after
    for p,digest in initial['sourceBefore']['copies'].items():assert sha((ROOT/p).read_bytes())==digest
    for p,digest in initial['sourceBefore']['reviewFiles'].items():assert sha((ROOT/p).read_bytes())==digest
    call(['git','fetch','origin'],label='successor-post-test-fetch')
    call([python,'-m','evaluation.peers','--output',str(RUN/'successor-post-test-peer-communication.json')],label='successor-post-test-scan')
    latest=json.loads((RUN/'successor-post-test-peer-communication.json').read_text())
    assert latest['branches']==scan['branches']
    assert {p:v['sha256'] for p,v in latest['files'].items()}=={p:v['sha256'] for p,v in scan['files'].items()}
    save('successor-review.json',{'capturedAt':now(),'ack':{'messageId':'A2-0013','path':ACK,'commit':PIN,'changeCommit':PIN,'sha256':sha(raw)},
         'freezeSha256':initial['freezeSha256'],'publicationCommit':BASE,'protocolPin':PIN,'manifestSha256':sha(manifest),
         'entries':entries,'changedPaths':changed,'productionChangedPaths':production,'productionDiff':source_diff,
         'adapterSha256':sha(adapter_raw),'adapterFreeze':adapter['freeze'],'serviceStatus':adapter['serviceStatus'],
         'snapshotBefore':before,'snapshotAfter':after,'sourceStable':True,'tests':{'file':'tests/test_exports.py','passed':12,'skipped':0},
         'exports':export_result,'exampleVerdicts':examples,'peerFiles':len(latest['files']),'commands':{'count':len(commands),'path':'successor-commands.json','exitCodes':[0]},
         'programSha256':sha(Path(__file__).read_bytes()),'classification':'tested reconstruction result: E0 mapping/export compatibility only',
         'limitations':['No service READY/integration FREEZE ACK inferred.','No live tests/services/unit-suite claim or RQ gate result.',
         'Owner1318/201/7187-input claims remain owner evidence; independently reran only12 export tests/9 exports/16 examples.',
         '98 successor inputs remain stable; original15 frozen copies/35 reviewed files and FREEZE.json unchanged.',
         'Synthetic fixtures, seed none, symbolic E; F/G locked.']})
    print(json.dumps({'ack':'A2-0013','commit':PIN,'protocolInputs':98,'tests':12,'examples':16,'sourceStable':True,'commands':len(commands),'peerFiles':len(latest['files'])},indent=2))

if __name__=='__main__':main()
