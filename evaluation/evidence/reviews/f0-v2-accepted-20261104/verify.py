"""Verify F0 acceptance/publication and historical sources without runtime work."""
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

from publish import ROOT, OUT, BASE, REFS, ACK_PATHS, REQUEST_SHA, git, sha


def main():
    request_path = 'communication/F0_FREEZE_CANDIDATE2.json'
    raw = (ROOT / request_path).read_bytes()
    assert sha(raw) == REQUEST_SHA and raw == git('show', BASE + ':' + request_path)
    request = json.loads(raw)
    acceptance_path = ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json'
    accepted = json.loads(acceptance_path.read_bytes())
    publication = json.loads((ROOT / 'interfaces/v2/FREEZE.json').read_bytes())
    assert accepted['status'] == 'ACCEPTED_FOR_OWNED_IMPLEMENTATION_ONLY'
    assert accepted['implementationAuthorized'] is True
    assert accepted['executionAuthorized'] is False and publication['executionAuthorized'] is False
    assert request['implementationAuthorized'] is False and request['freezeAcks'] == []
    assert len(accepted['freezeAcks']) == 2
    assert {r['owner'] for r in accepted['freezeAcks']} == set(ACK_PATHS)
    for receipt in accepted['freezeAcks']:
        owner = receipt['owner']
        assert receipt['path'] == ACK_PATHS[owner] and receipt['commit'] == REFS[owner]
        data = git('show', receipt['commit'] + ':' + receipt['path'])
        assert sha(data) == receipt['sha256']
        assert git('show', receipt['fileChangingCommit'] + ':' + receipt['path']) == data
        assert git('log', '-1', '--format=%H', receipt['commit'], '--', receipt['path']).decode().strip() == receipt['fileChangingCommit']
        assert (OUT / (receipt['messageId'] + '.md')).read_bytes() == data
        text = data.decode()
        assert REQUEST_SHA in text and 'Type: ACK' in text
        assert 'Responds-to: A3-0072' in text and 'From: ' + owner in text
    assert publication['acceptance']['sha256'] == sha(acceptance_path.read_bytes())
    assert publication['files'] == accepted['publication']
    assert len(publication['files']) == 14
    for target, pin in publication['files'].items():
        assert target == pin['sourcePath'].replace('interfaces/proposals/v2-candidate2/', 'interfaces/v2/', 1)
        assert request['candidateFiles'][pin['sourcePath']] == pin['sha256']
        assert sha((ROOT / target).read_bytes()) == pin['sha256']
        assert (ROOT / target).read_bytes() == (ROOT / pin['sourcePath']).read_bytes()
    for field in ['historicalBase', 'mappingAcks', 'candidate8DesignAcks', 'candidateManifest',
                  'ownerInputs', 'protocolF0Files', 'explicitLayoutPins', 'caseIds',
                  'caseResults', 'componentCount', 'numericPlan', 'ownership',
                  'mandatoryBoundaries', 'clarifications', 'compositionRule']:
        assert accepted[field] == request[field], field
    for receipt in accepted['mappingAcks'] + accepted['candidate8DesignAcks']:
        assert sha(git('show', receipt['commit'] + ':' + receipt['path'])) == receipt['sha256']
        assert sha(git('show', receipt['fileChangingCommit'] + ':' + receipt['path'])) == receipt['sha256']
    candidate = accepted['candidateManifest']
    assert sha(git('show', candidate['commit'] + ':' + candidate['path'])) == candidate['sha256']
    for path, digest in accepted['historicalBase'].items():
        assert sha((ROOT / path).read_bytes()) == digest
    matrix = json.loads((ROOT / 'evaluation/evidence/reviews/f0-revision8-20261104/f_matrix.json').read_bytes())
    assert len(matrix['cases']) == 32 and [c['id'] for c in matrix['cases']] == accepted['caseIds']
    assert all(c['executionStatus'] == 'NOT_RUN' for c in matrix['cases'])
    assert accepted['numericPlan'] == {k: v for k, v in matrix['numericPlan'].items() if k not in ['status', 'actualTimings']}
    rows = list(csv.DictReader(io.StringIO((ROOT / 'evaluation/evidence/reviews/f0-revision8-20261104/fault-model.csv').read_text())))
    assert len(rows) == accepted['componentCount'] == 14
    counts = {}
    for commit, manifest_path, prefix in [
        (REFS['agent-1'], 'ledger/evidence/source-manifest.sha256', ''),
        (REFS['agent-2'], 'protocol/evidence/source-manifest.sha256', ''),
        (REFS['agent-2'], 'protocol/f0/MANIFEST.sha256', ''),
        (REFS['agent-2'], 'protocol/v2-review/freeze-candidate2/MANIFEST.sha256', 'protocol/v2-review/freeze-candidate2/'),
    ]:
        manifest = git('show', commit + ':' + manifest_path)
        entries = {}
        for line in manifest.decode().splitlines():
            digest, name = line.split(maxsplit=1)
            name = prefix + name.lstrip('*').removeprefix('./')
            assert sha(git('show', commit + ':' + name)) == digest, name
            entries[name] = digest
        counts[manifest_path] = {'sha256': sha(manifest), 'entries': len(entries)}
        if manifest_path == 'protocol/f0/MANIFEST.sha256':
            assert entries == accepted['protocolF0Files']
    assert counts['protocol/v2-review/freeze-candidate2/MANIFEST.sha256']['sha256'] == '5484fb6752933f1bf82b5f66cc92a7e4a9e126ebe2341b60a231cafa93eb46db'
    historical = accepted['eSourceRule']
    historical_manifest = git('show', historical['historicalProtocolCommit'] + ':' + historical['historicalManifest'])
    assert sha(historical_manifest) == historical['historicalManifestSha256']
    for line in historical_manifest.decode().splitlines():
        digest, path = line.split(maxsplit=1)
        assert sha(git('show', historical['historicalProtocolCommit'] + ':' + path.lstrip('*'))) == digest
    assert (ROOT / historical['sourceReadyDefinition']).is_file()
    # Preserve every historical/module/mailbox byte, including untracked peer files.
    assert not git('diff', BASE, '--', 'ledger', 'protocol', 'archive', 'interfaces/v1',
                   'interfaces/proposals', 'communication/agent-1/STATUS.md',
                   'communication/agent-1/HANDOFF.md', 'communication/agent-1/outbox',
                   'communication/agent-2/STATUS.md', 'communication/agent-2/HANDOFF.md',
                   'communication/agent-2/outbox')
    untracked = git('ls-files', '--others', '--exclude-standard', '--', 'ledger', 'protocol', 'archive').decode().splitlines()
    assert not untracked, untracked
    provenance = json.loads((OUT / 'communication-provenance.json').read_bytes())
    assert provenance['refs'] == REFS and not provenance['incomparableConflicts']
    result = {
        'status': 'EXACT_FREEZE_ACKS_ACCEPTANCE_AND_V2_PUBLICATION_VERIFIED',
        'capturedUtc': datetime.now(timezone.utc).isoformat(), 'refs': REFS,
        'requestSha256': REQUEST_SHA, 'acceptanceSha256': sha(acceptance_path.read_bytes()),
        'publicationSha256': sha((ROOT / 'interfaces/v2/FREEZE.json').read_bytes()),
        'freezeAcks': accepted['freezeAcks'], 'publishedPayloads': 14,
        'ownerManifests': counts, 'historicalEManifestEntries': 142,
        'communicationPaths': len(provenance['latest']), 'incomparableConflicts': [],
        'caseResults': 'ALL_32_NOT_RUN', 'implementationAuthorized': True,
        'executionAuthorized': False, 'newRuntimeOrGateResults': False,
        'tools': {'python': subprocess.check_output(['python3', '--version']).decode().strip(),
                  'git': git('--version').decode().strip()},
    }
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
