"""Read-only publication/compatibility/source audit; no owner code execution."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from evaluation.schema_v2 import validate, validate_response


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def inputs():
    paths = []
    for folder in ['evaluation', 'interfaces']:
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and
                     not {'runs', '__pycache__', 'evidence'} & set(p.relative_to(ROOT).parts) and
                     p.suffix in ('.py', '.json', '.csv', '.pv', '.tla', '.cfg'))
    paths.extend(ROOT / p for p in ['pyproject.toml', 'uv.lock', 'AGENTS.md', 'SPEC.md',
        'PLAN.md', 'communication/F0_ACCEPTANCE_CANDIDATE2.json',
        'communication/E_SOURCE_CLOSURE_ACCEPTANCE.json'])
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(set(paths))}


def audit():
    successor = json.loads((ROOT / 'interfaces/v2.1/FREEZE.json').read_text())
    for pin in [successor['acceptance'], successor['baseFreeze'], successor['baseSchema'], successor['amendment']]:
        assert sha((ROOT / pin['path']).read_bytes()) == pin['sha256']
    for path, pin in successor['files'].items():
        assert sha((ROOT / path).read_bytes()) == pin['sha256']
    for path, digest in successor['inheritedPayloads'].items():
        assert sha((ROOT / path).read_bytes()) == digest
    base = json.loads((ROOT / 'interfaces/v2/FREEZE.json').read_text())
    for path, pin in base['files'].items():
        assert sha((ROOT / path).read_bytes()) == pin['sha256']
    # Exhaustive byte comparison for existing version/proposal trees.
    preserved = git('ls-tree', '-r', '--name-only', '222cdf244eab376199ccbd02fa43bedef0d084d3',
                    'interfaces/v1', 'interfaces/v2', 'interfaces/proposals').decode().splitlines()
    for path in preserved:
        assert (ROOT / path).read_bytes() == git('show', '222cdf244eab376199ccbd02fa43bedef0d084d3:' + path), path
    receipt = json.loads((ROOT / successor['acceptance']['path']).read_text())
    for ack in receipt['proposalAcks']:
        assert sha(git('show', ack['commit'] + ':' + ack['path'])) == ack['sha256']
        assert git('log', '-1', '--format=%H', ack['commit'], '--', ack['path']).decode().strip() == ack['fileChangingCommit']
    assert receipt['publicationMappingAcks'] == [] and not receipt['executionAuthorized']
    provenance = json.loads((OUT / 'communication-provenance.json').read_text())
    assert not provenance['missingBranches']
    assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
    owner = 'aef3daa5ebbe434f97b016719f8762d4aaf09441'
    inventory = git('show', owner + ':ledger/evidence/source-manifest.sha256')
    assert sha(inventory) == '6358359e35771ac2f3a6041148ee28a5ae8c979fde657406db16515d09e1c0a0'
    entries = inventory.decode().splitlines()
    for line in entries:
        digest, path = line.split(maxsplit=1)
        assert sha(git('show', owner + ':' + path)) == digest, path
    f0 = json.loads((ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    for path, digest in f0['protocolF0Files'].items():
        assert sha(git('show', provenance['branches']['origin/agent-2'] + ':' + path)) == digest
    # Test actual reviewed owner artifacts against both schemas, using own
    # semantic walker as well as shape checks; do not run owner scripts/services.
    manifests = []
    for scenario, filename in [('e-successor', 'deployment-v2.json'),
                                ('f-base', 'deployment.json'), ('f-q2', 'deployment.json'),
                                ('f-bit7', 'deployment.json')]:
        value = json.loads(git('show', owner + ':ledger/evidence/af1/slice6-smoke/' + scenario + '/' + filename))
        for revision in ('v2', 'v2.1'):
            validate('LedgerDeployment', value, schema_revision=revision)
        manifests.append(scenario)
    # Every existing successful operation example remains accepted by the opt-in schema.
    successes = json.loads((ROOT / 'interfaces/v2/vectors/success.json').read_text())
    for row in successes:
        validate_response(row['operation'], row['response'], schema_revision='v2.1')
    return {'capturedUtc': datetime.now(timezone.utc).isoformat(),
            'preservedOriginalInterfaceFiles': len(preserved),
            'basePayloads': len(base['files']), 'inheritedPayloads': len(successor['inheritedPayloads']),
            'reviewedLedgerSourceEntries': len(entries), 'protocolF0Pins': len(f0['protocolF0Files']),
            'ownerManifestCompatibility': manifests, 'successfulOperationExamples': len(successes),
            'communicationPaths': len(provenance['files']), 'conflicts': [],
            'tools': {'python': sys.version, 'executable': sys.executable,
                      'git': git('--version').decode().strip(),
                      **{p: importlib.metadata.version(p) for p in ['pytest', 'jsonschema', 'eth-account']}},
            'sourceReadyOrExecutionAckInferred': False, 'Fcases': 'ALL_32_NOT_RUN', 'G': 'LOCKED'}


if __name__ == '__main__':
    mode = sys.argv[1]
    result = audit()
    current = inputs()
    if mode == 'before':
        dump(OUT / 'inputs-before.json', {'localCommit': git('rev-parse', 'HEAD').decode().strip(),
                                        'inputs': current, 'audit': result})
    elif mode == 'after':
        assert json.loads((OUT / 'inputs-before.json').read_text())['inputs'] == current
        result['stableInputs'] = len(current)
        dump(OUT / 'verification.json', result)
    else:
        raise SystemExit('Use before or after')
    print(json.dumps(result, indent=2))
