"""Isolated A1-0115 source/export delta review. No chains or peer checkout writes.

Run with the root .venv Python and a NEW absolute scratch directory argument.
The fixed timestamp below is a synthetic exporter fixture, not a measured time.
"""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
from types import SimpleNamespace
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from evaluation.manifests import record_command
from evaluation.peers import scan
from evaluation.schema import validate as validate_v1
from evaluation.schema_v2 import validate

SOURCE = '85c59f588de58a8ff5e87b9fe6f630c9d8c43642'
BASE = 'aef3daa5ebbe434f97b016719f8762d4aaf09441'
MANIFEST = '70f541cd63bb8e8c4c0c1202dda0e5611ab15fde6d1ab4b8a0451497b6fb08dd'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def command(label, argv, cwd, expected=0, env=None):
    log = OUT / (label + '.txt')
    if log.exists():
        rows = json.loads((OUT / 'commands.json').read_text())
        row, = [r for r in rows if r['log'] == str(log.relative_to(ROOT))]
        assert row['argv'] == argv and row['cwd'] == str(cwd)
        assert row['exitCode'] == expected and row['outputSha256'] == sha(log.read_bytes())
        print(label, 'reuse hash-verified same-run result', expected, flush=True)
        return log.read_text()
    row = record_command(argv, cwd, log, timeout=300, env=env)
    row['log'] = str(log.relative_to(ROOT))
    rows = json.loads((OUT / 'commands.json').read_text()) if (OUT / 'commands.json').exists() else []
    write('commands.json', rows + [row])
    print(label, row['exitCode'], flush=True)
    assert row['exitCode'] == expected, label
    return log.read_text()


def inventory(commit):
    raw = git('show', commit + ':ledger/evidence/source-manifest.sha256')
    result = {}
    for line in raw.decode().splitlines():
        digest, path = line.split(maxsplit=1)
        path = path.lstrip('*').removeprefix('./')
        assert path.startswith('ledger/') and '..' not in Path(path).parts
        assert path not in result
        assert sha(git('show', commit + ':' + path)) == digest, path
        result[path] = digest
    tracked = set(git('ls-tree', '-r', '--name-only', commit, 'ledger/').decode().splitlines())
    assert set(result) == tracked - {'ledger/evidence/source-manifest.sha256'}
    return raw, result


def load_tool(path, name, ledger):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.LEDGER = ledger

    class FixedTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 4, 0, 0, 0, tzinfo=timezone.utc)

    module.datetime = SimpleNamespace(datetime=FixedTime, timezone=timezone)
    return module


def main():
    scratch = Path(sys.argv[1]).resolve()
    resume = sys.argv[2:] == ['--resume']
    assert resume == scratch.exists(), 'New scratch or explicit same-run --resume required'
    scratch.mkdir(parents=True, exist_ok=resume)
    provenance = scan(ROOT)
    write('communication-provenance.json', provenance)
    assert not provenance['missingBranches']
    assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
    messages = {}
    for owner, number in [('agent-1', '0115'), ('agent-2', '0061')]:
        path, = [p for p in provenance['files'] if p.startswith(f'communication/{owner}/outbox/{number}-')]
        row = provenance['files'][path]
        commit = provenance['branches']['origin/' + owner]
        raw = git('show', commit + ':' + path)
        (OUT / f'{owner}-{number}.md').write_bytes(raw)
        messages[owner] = {'path': path, 'commit': commit, 'fileChangingCommit': row['changeCommit'], 'sha256': sha(raw)}
    raw, entries = inventory(SOURCE)
    assert sha(raw) == MANIFEST and len(entries) == 429
    _, prior = inventory(BASE)
    changed = sorted(p for p in prior if prior[p] != entries.get(p))
    added = sorted(set(entries) - set(prior))
    assert len(prior) == 418 and len(added) == 11
    assert changed == ['ledger/evidence/af1/README.md', 'ledger/tools/check_successor_export.py',
                       'ledger/tools/deploy_local.sh', 'ledger/tools/make_manifest.py']
    assert not git('diff', '--name-only', BASE, SOURCE, '--', 'ledger/src', 'ledger/test',
                   'ledger/test-mutants', 'ledger/script', 'ledger/exports', 'ledger/foundry.toml')
    if not resume:
        with tarfile.open(fileobj=io.BytesIO(git('archive', SOURCE, 'ledger'))) as archive:
            archive.extractall(scratch, filter='data')
    ledger = scratch / 'ledger'
    assert all(sha((scratch / p).read_bytes()) == h for p, h in entries.items())
    pins = json.loads((ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    for p, h in pins['protocolF0Files'].items():
        assert sha(git('show', provenance['branches']['origin/agent-2'] + ':' + p)) == h
    freeze = json.loads((ROOT / 'interfaces/v2.1/FREEZE.json').read_text())
    fixed = {freeze[k]['path']: freeze[k]['sha256'] for k in ('acceptance', 'baseFreeze', 'baseSchema', 'amendment')}
    fixed.update({p: v['sha256'] for p, v in freeze['files'].items()})
    fixed.update(freeze['inheritedPayloads'])
    for p, h in fixed.items():
        assert sha((ROOT / p).read_bytes()) == h, p
    tools = json.loads((ROOT / 'evaluation/toolchain.json').read_text())
    binaries = {'forge': tools['foundry']['binaryPaths']['forge'], 'solc': tools['solc']}
    for tool in binaries.values():
        assert sha(Path(tool['path']).read_bytes()) == tool['sha256']
    write('inputs.json', {'capturedUtc': datetime.now(timezone.utc).isoformat(), 'source': SOURCE,
        'manifestSha256': MANIFEST, 'entries': entries, 'base': BASE, 'changedPriorPaths': changed,
        'addedPaths': added, 'messages': messages, 'publicationPins': fixed,
        'tools': binaries, 'python': platform.python_version(), 'scratch': str(scratch),
        'versions': {p: __import__('importlib.metadata', fromlist=['version']).version(p)
                     for p in ('jsonschema', 'pytest', 'eth-account')}})
    env = dict(os.environ, PATH=str(Path(binaries['forge']['path']).parent) + os.pathsep + os.environ['PATH'],
               FOUNDRY_SOLC=binaries['solc']['path'])
    command('forge-version', [binaries['forge']['path'], '--version'], scratch, env=env)
    command('build', [binaries['forge']['path'], 'build', '--root', str(ledger)], scratch, env=env)
    # No Forge test rerun: all contract/test/config bytes match the reviewed base.
    names = ['e-successor/deployment-v2.json', 'f-base/deployment.json', 'f-q2/deployment.json', 'f-bit7/deployment.json']
    paths = [ledger / 'evidence/af1/migration-v2.1' / n for n in names]
    command('compiled-exports', [sys.executable, '-I', str(ledger / 'tools/check_successor_export.py'),
        '--schema', str(ROOT / 'interfaces/v2.1/hmbc.schema.json'), *map(str, paths)], scratch)
    old_carrier = ledger / 'evidence/af1/slice6-smoke/e-successor/deployment-v2.json'
    red = command('old-carrier-rejected', [sys.executable, '-I', str(ledger / 'tools/check_successor_export.py'),
        '--schema', str(ROOT / 'interfaces/v2.1/hmbc.schema.json'), str(old_carrier)], scratch, expected=1)
    assert 'src/Governance.sol' in red and 'src/interfaces/IPolicyVersion.sol' in red
    e = json.loads(paths[0].read_text())
    source_map = {str(p.relative_to(ledger)): sha(p.read_bytes()) for p in (ledger / 'src').rglob('*.sol')}
    assert len(source_map) == 12 and e['sources'] == source_map
    for path in paths:
        d = json.loads(path.read_text())
        validate('LedgerDeployment', d, schema_revision='v2.1')
        assert d['sources'] == source_map
        for entry in d['abi'].values():
            assert sha((ledger / entry['abi']).read_bytes()) == entry['abiSha256']
    try:
        validate('LedgerDeployment', e)
    except ValidationError:
        pass
    else:
        raise AssertionError('New E carrier accepted by old schema')
    validate_v1('LedgerDeployment', json.loads((paths[0].parent / 'deployment.json').read_text()))
    # Compare the actual producer paths on independently reconstructed synthetic stage files.
    old_tool = scratch / 'make_manifest_before.py'
    old_tool.write_bytes(git('show', BASE + ':ledger/tools/make_manifest.py'))
    old = load_tool(old_tool, 'old_manifest', ledger)
    new = load_tool(ledger / 'tools/make_manifest.py', 'new_manifest', ledger)
    old_ast, new_ast = ast.parse(old_tool.read_text()), ast.parse((ledger / 'tools/make_manifest.py').read_text())
    for function in ('e_manifest', 'f_manifest', 'write'):
        a = next(n for n in old_ast.body if isinstance(n, ast.FunctionDef) and n.name == function)
        b = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == function)
        assert ast.dump(a) == ast.dump(b), function
    trials = []
    for profile in list(new.PROFILES) + list(new.F_PROFILES):
        for mode in new.LOG_MODES:
            base = json.loads((paths[1] if profile in new.F_PROFILES else paths[0]).read_text())
            ws = base['fixture']['witnessSet']
            pbc = {k.lower(): v for k, v in base['chains']['pbc']['contracts'].items()}
            pbc.update(blockNumber=base['chains']['pbc']['deployBlock'], authorities=base['fixture']['authorities'],
                       relay=base['fixture']['relay']['address'], witnesses=ws['witnesses'])
            dbc = {k.lower(): v for k, v in base['chains']['dbc']['contracts'].items()}
            dbc.update(blockNumber=base['chains']['dbc']['deployBlock'], witnesses=ws['witnesses'],
                       dataOwner=base['fixture']['data'][0]['owner'])
            if profile in new.F_PROFILES:
                pbc['threshold'] = dbc['threshold'] = str(new.F_PROFILES[profile][1])
            results = []
            for tool, label in ((old, 'old'), (new, 'new')):
                out = scratch / 'synthetic-stages' / profile / mode / label
                out.mkdir(parents=True)
                (out / 'pbc-stage.json').write_text(json.dumps(pbc))
                (out / 'dbc-stage.json').write_text(json.dumps(dbc))
                args = ['make_manifest.py', '--successor', str(out), profile, mode, '18545', '28545',
                        'http://127.0.0.1:18545', 'http://127.0.0.1:28545']
                assert tool.main(args) == 0
                results.append(out)
            assert (results[0] / 'deployment.json').read_bytes() == (results[1] / 'deployment.json').read_bytes()
            if profile in new.PROFILES:
                validate_v1('LedgerDeployment', json.loads((results[1] / 'deployment.json').read_text()))
                a, b = [json.loads((r / 'deployment-v2.json').read_text()) for r in results]
                assert {k for k in a if a[k] != b[k]} == {'schemaVersion', 'sources'}
                assert b['sources'] == source_map and b['schemaVersion'] == 'hmbc-ledger-deployment/v2.1'
                validate('LedgerDeployment', b, schema_revision='v2.1')
            else:
                validate('LedgerDeployment', json.loads((results[1] / 'deployment.json').read_text()))
            trials.append({'profile': profile, 'logMode': mode, 'defaultBytesEqual': True})
    assert all(sha((scratch / p).read_bytes()) == h for p, h in entries.items())
    write('verification.json', {'verifiedUtc': datetime.now(timezone.utc).isoformat(), 'source': SOURCE,
        'inventoryEntriesBeforeAfter': len(entries), 'unchangedContractTestExports': True,
        'ownerCarriersCompiledChecked': len(paths), 'sourceMapEntries': len(source_map),
        'oldCarrierCompletenessRefused': True, 'syntheticProducerTrials': trials,
        'fixedTimestampFixture': '2026-11-04T00:00:00Z', 'protocolF0Pins': len(pins['protocolF0Files']),
        'forgeTestRerun': False, 'liveRpcRerun': False, 'protocolSuiteRerun': False,
        'executionAuthorized': False, 'fGate': 'NOT_RUN'})
    print('VERIFIED', len(entries), 'entries;', len(trials), 'producer trials; four compiled exports; no services', flush=True)


if __name__ == '__main__':
    main()
