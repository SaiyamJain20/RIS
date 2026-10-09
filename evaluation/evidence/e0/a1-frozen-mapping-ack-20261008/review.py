"""One-run C-E0 frozen mapping review; no module code or live service execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import subprocess
import sys

ROOT = Path('/home/karma/Documents/RIS')
RUN = Path(__file__).resolve().parent
BASE = 'f7b8f3fd74ae3dd52e385cd013a6429415b519a2'
A1 = '70f704da9bf1a7ed4aa2fc3fa8e7292e6eb7b37a'
A2 = 'f69e25027ff98a611774ad45924615eb2af37d89'
ACK_PATH = 'communication/agent-1/outbox/0027-ack-frozen-v1-mapping.md'
FREEZE_SHA = 'f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2'
PRIOR = RUN.parent / '20261008T144827Z/final-peer-communication.json'
commands = []

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(name, value):
    (RUN / name).write_text(json.dumps(value, indent=2) + '\n')

def command(argv, name=None, expected=0):
    number = len(commands) + 1
    label = name or f'git-read-{number:04}'
    started = now()
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=120)
    (RUN / (label + '.stdout')).write_bytes(proc.stdout)
    (RUN / (label + '.stderr')).write_bytes(proc.stderr)
    commands.append({'argv':argv, 'cwd':str(ROOT), 'startedAt':started, 'endedAt':now(),
                     'exitCode':proc.returncode, 'stdoutSha256':sha(proc.stdout),
                     'stderrSha256':sha(proc.stderr), 'stdoutPath':label+'.stdout',
                     'stderrPath':label+'.stderr'})
    save('commands.json', commands)
    if proc.returncode != expected:
        raise RuntimeError(f'{label}: expected {expected}, got {proc.returncode}')
    return proc.stdout

def git(*args):
    return command(['git', *args])

def blob(commit, path):
    return git('show', commit+':'+path)

def walk_diff(a, b, prefix=''):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(a.keys() | b.keys()):
            if key not in a or key not in b:
                yield prefix + key
            else:
                yield from walk_diff(a[key], b[key], prefix + key + '.')
    elif a != b:
        yield prefix.rstrip('.')

def verify_bytes():
    frozen = (ROOT / 'interfaces/v1/FREEZE.json').read_bytes()
    assert sha(frozen) == FREEZE_SHA
    assert frozen == blob(BASE, 'interfaces/v1/FREEZE.json')
    f = json.loads(frozen)
    result = {'freezeSha256':sha(frozen), 'copies':{}, 'reviewFiles':{}, 'owners':{}, 'abis':{}}
    for path, info in f['frozenCopies'].items():
        data = (ROOT / path).read_bytes()
        source = blob(info.get('commit', f['reviewedAgent3Commit']), info['sourcePath'])
        assert sha(data) == info['sha256'] and data == source == blob(BASE, path)
        result['copies'][path] = sha(data)
    assert len(result['copies']) == 15
    rp = f['reviewManifest']['path']
    reviewed = (ROOT / rp).read_bytes()
    assert sha(reviewed) == f['reviewManifest']['sha256']
    assert reviewed == blob(f['reviewedAgent3Commit'], rp)
    for path, expected in f['reviewManifest']['files'].items():
        data = (ROOT / path).read_bytes()
        assert sha(data) == expected and data == blob(f['reviewedAgent3Commit'], path)
        result['reviewFiles'][path] = sha(data)
    assert len(result['reviewFiles']) == 35
    for owner, info in f['owners'].items():
        manifest = blob(info['commit'], info['manifestPath'])
        assert sha(manifest) == info['manifestSha256']
        current = A1 if owner == 'ledger' else A2
        assert manifest == blob(current, info['manifestPath'])
        entries = {}
        for line in manifest.decode().splitlines():
            digest, path = line.split(None, 1)
            assert path.startswith(owner + '/') and path not in entries
            assert sha(blob(current, path)) == digest
            entries[path] = digest
        assert len(entries) == info['entries']
        assert git('diff','--name-only',info['commit'],current,'--',owner+'/').strip() == b''
        result['owners'][owner] = {'commit':info['commit'], 'currentCommit':current,
                                   'manifestSha256':sha(manifest), 'entries':entries}
    for role, digest in f['abiAgreement'].items():
        ledger = blob(f['owners']['ledger']['commit'], 'ledger/exports/abi/'+role+'.json')
        protocol = blob(A2, 'protocol/abi/'+role+'.json')
        assert ledger == protocol and sha(ledger) == digest
        result['abis'][role] = digest
    return f, result

def main():
    assert git('rev-parse','--show-toplevel').decode().strip() == str(ROOT)
    assert git('branch','--show-current').decode().strip() == 'agent-3'
    assert git('rev-parse','HEAD').decode().strip() == BASE
    assert not git('status','--porcelain=v1','--untracked-files=all').strip()
    command(['git','fetch','origin'], 'fetch')
    command([str(ROOT/'.venv/bin/python'),'-m','evaluation.peers','--output',
             str(RUN/'peer-communication.json')], 'scan')
    scan = json.loads((RUN/'peer-communication.json').read_text())
    assert scan['branches']['origin/agent-1'] == A1
    assert scan['branches']['origin/agent-2'] == A2
    assert scan['branches']['origin/agent-3'] == BASE
    assert not scan['missingBranches']
    assert not any(x['divergentRevisions'] or x['ambiguous'] for x in scan['files'].values())
    previous = json.loads(PRIOR.read_text())
    changed = {p:v for p,v in scan['files'].items()
               if previous['files'].get(p,{}).get('sha256') != v['sha256']}
    assert set(changed) == {ACK_PATH,'communication/agent-1/STATUS.md'}
    for p, info in changed.items():
        data = blob(info['commit'],p)
        assert info['changeCommit'] == A1 and sha(data) == info['sha256']
        (RUN/Path(p).name).write_bytes(data)
    ack = (RUN/Path(ACK_PATH).name).read_text()
    for token in [FREEZE_SHA, BASE, 'Message-ID: A1-0027', 'Type: ACK',
                  'all 15', 'Exclusions (unchanged from A1-0022)', 'metadataPolicy']:
        assert token in ack
    f, before = verify_bytes()
    vectors = json.loads((ROOT/'interfaces/v1/vectors/eip712-agent1.json').read_text())
    owner_vectors = json.loads(blob(f['owners']['ledger']['commit'],
                                   'ledger/exports/vectors/eip712-v0-ledger.json'))
    vector_changes = list(walk_diff(vectors,owner_vectors))
    assert vector_changes == ['interfaceVersion'] and vectors['vectors'] == owner_vectors['vectors']
    assert len(vectors['vectors']) == 10
    sample = json.loads((ROOT/'interfaces/v1/vectors/deployment-agent1.json').read_text())
    sample_changes = {}
    for deployment in sample['deployments']:
        profile = deployment['profile']
        owner_sample = json.loads(blob(f['owners']['ledger']['commit'],
                       'ledger/exports/deployments/sample-'+profile+'/deployment.json'))
        differences = list(walk_diff(deployment,owner_sample))
        assert set(differences) == {'interfaceVersion','createdAt','chains.pbc.deployBlock','chains.dbc.deployBlock'}
        assert deployment['interfaceVersion'] == 'v0 proposed' and owner_sample['interfaceVersion'] == 'v1'
        sample_changes[profile] = differences
    assert len(sample_changes) == 4
    schema = json.loads((ROOT/'interfaces/v1/hmbc.schema.json').read_text())
    assert set(schema['$defs']['LedgerDeployment']['properties']['interfaceVersion']['enum']) == {'v0 proposed','v1'}
    adapter_data = blob(A2,'protocol/exports/adapter.json')
    adapter = json.loads(adapter_data)
    tools = json.loads((ROOT/'evaluation/toolchain.json').read_text())
    binaries = dict(tools['foundry']['binaryPaths'])
    binaries['solc'] = tools['solc']
    binaries['proverif'] = tools['proverif']
    tool_hashes = {}
    for name, info in binaries.items():
        digest = sha(Path(info['path']).read_bytes())
        assert digest == info.get('sha256',info.get('binarySha256'))
        tool_hashes[name] = {'path':info['path'],'sha256':digest}
    assert sha((ROOT/'uv.lock').read_bytes()) == tools['pythonLock']['sha256']
    versions = {'python':sys.version, 'packages':{p:importlib.metadata.version(p) for p in tools['packagePins']}}
    assert versions['packages'] == tools['packagePins']
    command([str(ROOT/'.venv/bin/python'),'--version'],'python-version')
    command(['git','--version'],'git-version')
    command([str(ROOT/'.venv/bin/python'),'communication/build_prompts.py','--check'],'prompt-check')
    _, after = verify_bytes()
    assert before == after
    assert not git('status','--porcelain=v1','--untracked-files=all').strip()
    review = {'capturedAt':now(),'baseline':BASE,'publicationCommit':BASE,
              'peerChanges':changed,'peerFiles':len(scan['files']), 'divergentRevisions':[],
              'ack':{'messageId':'A1-0027','path':ACK_PATH,'commit':A1,
                     'changeCommit':A1,'sha256':sha(ack.encode())},
              'freezeSha256':FREEZE_SHA,'sourceBefore':before,'sourceAfter':after,'sourceStable':True,
              'packaging':{'vectorChangedFields':vector_changes,'vectorEntries':10,
                           'deploymentChangedFields':sample_changes,
                           'schemaEip712Annotations':sum('x-eip712Type' in v for v in schema['$defs'].values()),
                           'annotationNote':'10 annotations include CredentialRecord; 9 signed primary types remain unchanged.'},
              'adapter':{'commit':A2,'path':'protocol/exports/adapter.json',
                         'sha256':sha(adapter_data),'interfaceVersion':adapter['interfaceVersion'],
                         'integrationServiceReady':False},'toolVersions':versions,'toolHashes':tool_hashes,
              'caseStatus':'56 schedules NOT_RUN; four paper crash classifications BLOCKED/unproved',
              'classification':'tested reconstruction result: static byte/version mapping only',
              'limitations':['No runtime/schema/unit/formal/service experiments rerun.',
                             'Prior freeze tests remain historical evidence, not fresh run claims.',
                             'A1 scope only; no whole-package/evaluator/root-lock/formal/protocol ACK inferred.',
                             'A2 frozen mapping ACK absent; E0 closure/E1 unlock pending; F/G locked.',
                             'A1 integration willingness is not an exact integration FREEZE ACK.',
                             'Synthetic fixtures; seed none; symbolic E; no live provider or process started.'],
              'commands':{'path':'commands.json','count':len(commands),
                          'exitCodes':sorted(set(x['exitCode'] for x in commands))},
              'programSha256':sha(Path(__file__).read_bytes())}
    save('review.json',review)
    print(json.dumps({'ack':review['ack'],'peerFiles':review['peerFiles'],
                      'copies':15,'reviewFiles':35,'ownerInputs':195,
                      'commands':review['commands'],'sourceStable':True,
                      'freezeUnchanged':True,'e0Closed':False,'e1Unlocked':False},indent=2))

if __name__ == '__main__':
    main()
