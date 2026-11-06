"""Independent bounded recipient/startup/ABI/output probes; no chain service."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'evaluation/runs/a2-cli-20261107'
PROTO = RUN / 'snapshot/protocol'
sys.path[:0] = [str(PROTO), str(ROOT)]
from hmbc_protocol import adapter_v2 as adapter
from hmbc_protocol import adapter_v2_main as cli
from hmbc_protocol import rpc_binding_view as rv
from hmbc_protocol import worker

spec = importlib.util.spec_from_file_location('hmbc_protocol.review_baseline_worker', RUN / 'baseline_worker.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
FX = PROTO / 'tests/fixtures'
MANIFEST = json.loads((FX / 'agent1-85c59f5-f-base-deployment.json').read_text())
SCHEMA_PATH = ROOT / 'interfaces/v2.1/hmbc.schema.json'
SCHEMA = json.loads(SCHEMA_PATH.read_text())
ABI = FX / 'agent1-85c59f5-abi'
REG, OTHER, ZERO = ('0x' + h * 32 for h in ('aa', 'bb', '00'))
rows, gaps = [], []

class PublicStub:
    def __init__(self, profile, registered):
        self.profile, self.registered = profile, registered
    def call(self, contract, method, *args):
        return {'profile': self.profile, 'recipientKeyHash': self.registered}[method]

class LedgerStub:
    def __init__(self, profile, registered):
        self.pbc = PublicStub(profile, registered)
        self.PSC, self.RSC = object(), object()

def recipient(module, profile, grant, registered=REG):
    w = module.Worker.__new__(module.Worker)
    w.led = LedgerStub(profile, registered)
    try:
        return dict(accepted=True, recipient=w._recipient_for({'gid': '0x'+'11'*20, 'recipientKeyHash': grant}))
    except module.WorkerError as e:
        return dict(accepted=False, code=e.code, message=e.message)

for profile in ('0', '1', '2', '3'):
    cases = [(ZERO, REG), (REG, REG), (OTHER, REG), (ZERO, ZERO)]
    for grant, registered in cases:
        old, new = recipient(baseline, profile, grant, registered), recipient(worker, profile, grant, registered)
        expected = (grant == ZERO and registered != ZERO) if profile in ('0','1') else (grant != ZERO and grant == registered)
        assert new['accepted'] == expected, (profile, grant, registered, new)
        if profile != '3':
            assert old == new
        if profile == '3' and grant == REG:
            assert not old['accepted'] and new['accepted']
        rows.append(dict(control='recipient', profile=profile, grant=grant, registered=registered, before=old, after=new))

loaded = rv.load_pinned_abis(MANIFEST, str(ABI))
for name in loaded:
    assert hashlib.sha256((ABI / (name+'.json')).read_bytes()).hexdigest() == MANIFEST['abi'][name]['abiSha256']
rows.append(dict(control='ABI exact hashes', contracts=sorted(loaded)))

with tempfile.TemporaryDirectory(prefix='a3-cli-review-', dir=RUN) as td:
    tmp = Path(td)
    abi_copy = tmp / 'abi'
    abi_copy.mkdir()
    for p in ABI.glob('*.json'):
        (abi_copy / p.name).write_bytes(p.read_bytes())
    (abi_copy / 'PSC.json').write_bytes((abi_copy / 'PSC.json').read_bytes()+b' ')
    try:
        rv.load_pinned_abis(MANIFEST, str(abi_copy))
    except ValueError:
        rows.append(dict(control='one-byte ABI change', refused=True))
    else:
        raise AssertionError('changed ABI admitted')
    for revision in ('v2','v2.1'):
        captured = {}
        def capture(**kw):
            captured.update(kw)
            return 'captured'
        args=argparse.Namespace(deployment=str(FX/'agent1-85c59f5-f-base-deployment.json'), abi_dir=str(ABI), schema=str(SCHEMA_PATH), schema_sha256=hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(), schema_revision=revision, state_dir=str(tmp/'state'))
        assert cli.build_context(args, start=capture) == 'captured'
        assert captured['schema'] == SCHEMA and captured['schema_revision'] == revision
        assert captured['manifest'] == MANIFEST and callable(captured['worker_factory'])
        assert 'check_responses' not in captured and not (tmp/'state').exists()
        rows.append(dict(control='CLI wiring without startup', schemaRevision=revision, defaultResponsesEnabled=True, stateCreated=False))

    # Operator-corrupted input controls. These are startup robustness probes,
    # not claims of adversarial influence over the pinned deployment or schema.
    diagnostics = [('nonobject deployment', 'dep', b'[]'), ('overflowing numeric chainId', 'dep', json.dumps(MANIFEST).replace('"chainId": "18545"', '"chainId": 1e999').encode()), ('schema JSON array', 'schema', b'[]'), ('schema JSON null', 'schema', b'null')]
    # Replace the concrete first chain ID independently of fixture numbering.
    m=copy.deepcopy(MANIFEST)
    m['chains']['pbc']['chainId']='REVIEW_EXPONENT'
    diagnostics[1]=('overflowing numeric chainId', 'dep', json.dumps(m).replace('"REVIEW_EXPONENT"', '1e999').encode())
    env=dict(os.environ, PYTHONPATH=str(PROTO), PYTHONDONTWRITEBYTECODE='1')
    for i,(label,kind,raw) in enumerate(diagnostics):
        f=tmp/(str(i)+'.json')
        f.write_bytes(raw)
        state=tmp/('state-'+str(i))
        argv=[sys.executable,'-B','-m','hmbc_protocol.adapter_v2_main','--deployment',str(f if kind=='dep' else FX/'agent1-85c59f5-f-base-deployment.json'),'--abi-dir',str(ABI),'--schema',str(f if kind=='schema' else SCHEMA_PATH),'--schema-sha256',hashlib.sha256(raw if kind=='schema' else SCHEMA_PATH.read_bytes()).hexdigest(),'--schema-revision','v2','--state-dir',str(state)]
        r=subprocess.run(argv,cwd=PROTO,env=env,capture_output=True,text=True,timeout=40)
        obj=None
        try:
            obj=json.loads(r.stderr)
        except ValueError:
            pass
        clean=(r.returncode==2 and not r.stdout and isinstance(obj,dict) and set(obj)=={'error'} and not state.exists())
        row=dict(control=label,argv=argv,exit=r.returncode,stdout=r.stdout,stderr=r.stderr,stateCreated=state.exists(),cleanRefusal=clean)
        rows.append(row)
        if not clean:
            gaps.append(label)

ctx=adapter.Context(manifest=MANIFEST,schema_revision='v2',schema=SCHEMA,handlers={})
vector=next(v for v in json.loads((ROOT/'interfaces/v2/vectors/signing.json').read_text())['vectors'] if v['name']=='StateCheckpoint')
valid=dict(schemaVersion='v2',adapterMode='symbolic',checkpoint=vector['typedData']['message'],signatures=[vector['signatures'][0]['signature']])
def response(result):
    ctx.handlers['collect_checkpoint']=lambda i,c: copy.deepcopy(result)
    return adapter.handle_line(json.dumps(dict(schemaVersion='v2',operation='collect_checkpoint',input={},deploymentManifest=MANIFEST)),ctx)
assert response(valid)['result']==valid
bad=copy.deepcopy(valid)
bad['checkpoint']['sequence']=str(2**64)
r=response(bad)
assert not r['ok'] and r['error']['code']=='ADAPTER_UNAVAILABLE' and r['result'] is None
rows.append(dict(control='default response width check', validAccepted=True, overflowRefused=True))
result=dict(classification='tested reconstruction synthetic review',count=len(rows),controls=rows,startupDiagnosticGaps=gaps,limits='No native startup/grant, source-state, sign-time, store completeness, runtime READY or gate result. Arbitrary supplied schema hashes are operator configuration, not attacker control.')
(OUT/'probe-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
