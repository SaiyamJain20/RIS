"""Publish exact ACKed payloads and a separate F0 acceptance; no runtime work."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = 'f1fe7e79c178cd168c2d4b43af72dada2db3395f'
REFS = {
    'agent-1': 'd8eddf1e9d194df29e8016e3749c9e0935b5e5a7',
    'agent-2': '5639e8f638645acf0bf122109f8bae2ffc2b6fc4',
    'agent-3': BASE,
}
ACK_PATHS = {
    'agent-1': 'communication/agent-1/outbox/0110-ack-f0-freeze-candidate2-ledger-scope.md',
    'agent-2': 'communication/agent-2/outbox/0058-ack-f0-freeze-candidate2-protocol-scope.md',
}
REQUEST_SHA = 'f9f0906faf8dbfb9ccd2d06a794c715bb6a3167b6f273a50347742db41196df5'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(path, value):
    data = (json.dumps(value, indent=2) + '\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def main():
    request_path = 'communication/F0_FREEZE_CANDIDATE2.json'
    raw = git('show', BASE + ':' + request_path)
    assert sha(raw) == REQUEST_SHA
    assert (ROOT / request_path).read_bytes() == raw
    request = json.loads(raw)
    assert request['freezeAcks'] == [] and not request['executionAuthorized']
    receipts = []
    for owner, path in ACK_PATHS.items():
        commit = REFS[owner]
        data = git('show', commit + ':' + path)
        text = data.decode()
        message_id = 'A1-0110' if owner == 'agent-1' else 'A2-0058'
        assert 'Message-ID: ' + message_id in text and 'Type: ACK' in text
        assert 'Responds-to: A3-0072' in text and REQUEST_SHA in text
        assert 'From: ' + owner in text
        change = git('log', '-1', '--format=%H', commit, '--', path).decode().strip()
        assert git('show', change + ':' + path) == data
        subprocess.run(['git', 'merge-base', '--is-ancestor', change, commit], cwd=ROOT, check=True)
        receipts.append({'owner': owner, 'messageId': message_id, 'commit': commit,
                         'fileChangingCommit': change, 'path': path, 'sha256': sha(data),
                         'scope': ('ledger' if owner == 'agent-1' else 'protocol') + ' F0 design freeze only'})
        (OUT / (message_id + '.md')).write_bytes(data)
    candidate = request['candidateManifest']
    candidate_raw = git('show', candidate['commit'] + ':' + candidate['path'])
    assert sha(candidate_raw) == candidate['sha256']
    assert request['candidateFiles'] == json.loads(candidate_raw)['files']
    for path, digest in request['historicalBase'].items():
        assert sha((ROOT / path).read_bytes()) == digest
        assert sha(git('show', candidate['commit'] + ':' + path)) == digest
    for path, digest in request['protocolF0Files'].items():
        assert sha(git('show', request['ownerInputs']['ownerCommit'] + ':' + path)) == digest
        assert sha(git('show', REFS['agent-2'] + ':' + path)) == digest
    for path, digest in request['ownerInputs']['files'].items():
        assert sha(git('show', request['ownerInputs']['ownerCommit'] + ':' + path)) == digest
    assert sha(git('show', REFS['agent-1'] + ':ledger/f0/A-F1-DESIGN.md')) == request['ownerInputs']['ledgerDesignSha256']
    # Review newest communication by file-changing ancestry, never wall-clock order.
    latest = {}
    for commit in REFS.values():
        for path in git('ls-tree', '-r', '--name-only', commit, '--', 'communication').decode().splitlines():
            change = git('log', '-1', '--format=%H', commit, '--', path).decode().strip()
            row = {'observedCommit': commit, 'fileChangingCommit': change,
                   'sha256': sha(git('show', commit + ':' + path))}
            old = latest.get(path)
            if old and old['sha256'] != row['sha256']:
                def ancestor(a, b):
                    result = subprocess.run(['git', 'merge-base', '--is-ancestor', a, b], cwd=ROOT)
                    assert result.returncode in (0, 1)
                    return result.returncode == 0
                if ancestor(change, old['fileChangingCommit']):
                    continue
                assert ancestor(old['fileChangingCommit'], change), path
            latest[path] = row
    put(OUT / 'communication-provenance.json', {'refs': REFS, 'latest': latest, 'incomparableConflicts': []})
    publication = {}
    for source, digest in request['candidateFiles'].items():
        data = git('show', candidate['commit'] + ':' + source)
        assert sha(data) == digest and (ROOT / source).read_bytes() == data
        target = source.replace('interfaces/proposals/v2-candidate2/', 'interfaces/v2/', 1)
        assert target != source
        publication[target] = {'sourcePath': source, 'sha256': digest}
    accepted = {
        'format': 'RIS-F0-acceptance-1', 'freezeId': request['freezeId'], 'rq': 'F',
        'status': 'ACCEPTED_FOR_OWNED_IMPLEMENTATION_ONLY',
        'acceptedUtc': datetime.now(timezone.utc).isoformat(),
        'request': {'commit': BASE, 'path': request_path, 'sha256': REQUEST_SHA},
        'freezeAcks': receipts, 'mappingAcks': request['mappingAcks'],
        'candidate8DesignAcks': request['candidate8DesignAcks'],
        'candidateManifest': candidate, 'historicalBase': request['historicalBase'],
        'compositionRule': request['compositionRule'],
        'ownerInputs': request['ownerInputs'], 'protocolF0Files': request['protocolF0Files'],
        'explicitLayoutPins': request['explicitLayoutPins'],
        'implementationAuthorized': True, 'executionAuthorized': False,
        'publication': publication, 'caseIds': request['caseIds'],
        'caseResults': request['caseResults'], 'componentCount': request['componentCount'],
        'numericPlan': request['numericPlan'], 'ownership': request['ownership'],
        'mandatoryBoundaries': request['mandatoryBoundaries'],
        'clarifications': request['clarifications'],
        'eSourceRule': {
            'respondsTo': 'A2-0058 N-1',
            'historicalProtocolCommit': '376347d9b0979d1e46824a30197b935ffe91e4fb',
            'historicalManifest': 'protocol/evidence/source-manifest.sha256',
            'historicalManifestSha256': '005c8448faeb90d2dade129211a5f220635ee1c8bf421c89f17b2b7d0c2d7612',
            'rule': 'Historical E evidence/manifests remain immutable and verify at their historical commits. Approved F changes to E-listed source are allowed in owned paths; new F READY manifests list every new hash. Preserve E behavior, operations, outputs, default export, legacy fingerprint and assertions; run isolated E regressions. Integrated successor E regression requires new exact source/run ACKs and a separate execution FREEZE. This does not claim parity before tests.',
            'sourceReadyDefinition': 'communication/F_SOURCE_READY.md',
        },
        'next': 'Owners implement/test in owned paths; Agent3 implements independent evaluator/model. Obtain exact source READYs, interface mapping receipts and separate execution FREEZE ACKs before integrated services/scenarios.',
        'evidenceLimits': 'Exact receipt/pin/publication verification only; correlated same-model reviews. No new runtime, cryptography, timing, TLC, E/F/G gate result or consensus claim. All 32 F cases NOT_RUN; G locked.',
    }
    # Publication begins only after every input and receipt above was checked.
    acceptance_path = ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json'
    put(acceptance_path, accepted)
    for target, pin in publication.items():
        path = ROOT / target
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write((ROOT / pin['sourcePath']).read_bytes())
    put(ROOT / 'interfaces/v2/FREEZE.json', {
        'format': 'RIS-interface-publication-1', 'interfaceVersion': 'v2',
        'status': 'F0_ACCEPTED_FOR_IMPLEMENTATION_EXECUTION_LOCKED',
        'acceptance': {'path': 'communication/F0_ACCEPTANCE_CANDIDATE2.json',
                       'sha256': sha(acceptance_path.read_bytes())},
        'candidateManifest': candidate, 'files': publication,
        'implementationAuthorized': True, 'executionAuthorized': False,
        'note': 'All 14 reviewed payloads copied byte-for-byte. Candidate titles/pending prose remain historical; this sidecar and the acceptance record determine publication state. Frozen v1 and all proposals remain unchanged. Source READY and exact execution FREEZE ACKs still required.',
    })
    print(json.dumps({'status': accepted['status'], 'freezeAcks': receipts,
                      'publishedPayloads': len(publication),
                      'acceptanceSha256': sha(acceptance_path.read_bytes())}, indent=2))


if __name__ == '__main__':
    main()
