"""Pinned F0 specification review. No production modules or services execute."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REFS = {
    'agent-1': '8a943a7c64e881ac0686587f01a9ebfaf2368706',
    'agent-2': 'dcad9745a594770654810ca366ed78c6e559539f',
    'agent-3': '8b510fff03bf51615f1e1264523eee05cedf4576',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def load(path):
    return json.loads(git('show', REFS['agent-2'] + ':' + path))


def run():
    prov = {'refs': REFS, 'classification': 'TESTED_SPECIFICATION_REVIEW_NOT_RUNTIME',
            'ownerManifests': {}, 'inputs': {}, 'latestCommunication': {}}
    for owner, manifest in [
        ('agent-1', 'ledger/evidence/source-manifest.sha256'),
        ('agent-2', 'protocol/evidence/source-manifest.sha256'),
        ('agent-2', 'protocol/f0/MANIFEST.sha256')]:
        blob = git('show', REFS[owner] + ':' + manifest)
        rows = []
        for line in blob.decode().splitlines():
            digest, path = line.split(maxsplit=1)
            path = path.lstrip('*').removeprefix('./')
            assert sha(git('show', REFS[owner] + ':' + path)) == digest, path
            rows.append(path)
        prov['ownerManifests'][manifest] = {'sha256': sha(blob), 'verifiedEntries': len(rows)}
    for owner, paths in {
        'agent-1': ['communication/agent-1/outbox/0107-note-export-layouts-l1-l2-ledger-facts.md',
                    'communication/agent-1/outbox/0108-ack-a2-revision9-export-layouts-ledger-scope.md'],
        'agent-2': ['communication/agent-2/outbox/0056-rfc-f0-revision9-export-layout-generations-allow.md',
                    'protocol/f0/D50-DEPLOYMENT-BINDING.md', 'protocol/f0/SUCCESSOR-WIRE.md',
                    'protocol/f0/EXPORT-LAYOUTS.md', 'protocol/f0/SIGNING-RULES.md']}.items():
        for path in paths:
            prov['inputs'][path] = {'sha256': sha(git('show', REFS[owner] + ':' + path)),
                'commit': REFS[owner], 'fileChangingCommit': git('log', '-1', '--format=%H', REFS[owner], '--', path).decode().strip()}
    for commit in REFS.values():
        for path in git('ls-tree', '-r', '--name-only', commit, '--', 'communication').decode().splitlines():
            change = git('log', '-1', '--format=%H', commit, '--', path).decode().strip()
            row = {'commit': commit, 'fileChangingCommit': change, 'sha256': sha(git('show', commit + ':' + path))}
            old = prov['latestCommunication'].get(path)
            if old and old['sha256'] != row['sha256']:
                def ancestor(a, b):
                    result = subprocess.run(['git', 'merge-base', '--is-ancestor', a, b], cwd=ROOT)
                    assert result.returncode in (0, 1)
                    return result.returncode == 0
                if ancestor(change, old['fileChangingCommit']):
                    continue
                assert ancestor(old['fileChangingCommit'], change), path
            prov['latestCommunication'][path] = row
    for owner, base, paths in [
        ('agent-1', '933d2a7', ['ledger/src', 'ledger/script', 'ledger/foundry.toml']),
        ('agent-2', '9ced19af68bec8348d696f4db510fd9cfca497f4',
         ['protocol/hmbc_protocol', 'protocol/exports', 'protocol/testtools', 'protocol/v2-review'])]:
        assert not git('diff', '--name-only', base, REFS[owner], '--', *paths)
    for path in ['protocol/f0/D50-DEPLOYMENT-BINDING.md', 'protocol/f0/SUCCESSOR-WIRE.md',
                 'protocol/f0/SIGNING-RULES.md', 'protocol/f0/INVENTORY.md',
                 'protocol/f0/vectors/d50_reference.py', 'protocol/f0/vectors/d50_binding_vector.json',
                 'protocol/f0/vectors/check_wire_examples.py']:
        assert git('show', REFS['agent-2']+':'+path) == git('show', '64ec86acfac2a8d3db337782e34c1b7b7e1f84b7:'+path), path
    # Three independent encodings; never ask the owner's reference for expected hashes.
    vectors = load('protocol/f0/vectors/d50_binding_vector.json')
    hashes = {}
    for name, row in vectors['documents'].items():
        text = canonical(row['document'])
        assert text.decode() == row['canonicalJson']
        digest = sha(b'hmbc-deployment-binding/v2\n' + text)
        assert digest == row['bindingV2']
        hashes[name] = digest
    old = json.loads((ROOT / 'interfaces/proposals/v2/d50-owner-vectors.json').read_text())
    new_f = vectors['documents']['repaired-f']['document']
    old_f = copy.deepcopy(old['documents']['repaired-f']['document'])
    old_f['interfaceVersion'] = 'v2'
    assert old_f == new_f
    assert old['documents']['repaired-e'] == vectors['documents']['repaired-e']
    assert old['immutableRefs'] == vectors['immutableRefs']
    # Derive the closed profile table independently from the published ledger generator.
    import ast
    tree = ast.parse(git('show', REFS['agent-1'] + ':ledger/tools/make_manifest.py'))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('PROFILES', 'MUTATIONS'):
                    values[target.id] = ast.literal_eval(node.value)
    table = {name: (enum, values['MUTATIONS'].get(name, 0)) for name, enum in values['PROFILES'].items()}
    table['repaired-f'] = (3, None)
    assert vectors['profileTable'] == {name: {'enum': str(enum), 'mutations': 'any 0..511' if mask is None else str(mask)} for name, (enum, mask) in table.items()}
    case_results = []
    for case in vectors['manifestProfileCases']:
        name, enum, mask, live_enum, live_masks = case['input']
        row = table.get(name)
        reason = None
        if row is None or enum != str(row[0]) or live_enum != enum:
            reason = 'PROFILE_MISMATCH'
        else:
            holders = {'TMSC', 'PSC', 'KSSC', 'ACSC'} | ({'Governance'} if enum == '3' else set())
            if (not 0 <= int(mask) <= 511 or (row[1] is not None and int(mask) != row[1])
                    or set(live_masks) != holders or any(m != mask for m in live_masks.values())):
                reason = 'MUTATIONS_MISMATCH'
        if reason:
            assert reason == case['expectedRefusal']
        else:
            expected = {'name': ['paper-strict', 'paper-minimal', 'repaired-e', 'repaired-f'][int(enum)], 'enum': enum}
            assert expected == case['expectedProfile']
        case_results.append({'input': case['input'], 'independentResult': reason or expected})
    dump('independent-bindings.json', {'bindingHashes': hashes, 'profileCases': case_results})
    commands = []
    with tempfile.TemporaryDirectory(prefix='ris-a3-f0-r9-') as td:
        scratch = Path(td)
        archive = git('archive', REFS['agent-2'], 'protocol')
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(scratch, filter='data')
        before = {str(p.relative_to(scratch)): sha(p.read_bytes()) for p in scratch.rglob('*') if p.is_file()}
        here = scratch / 'protocol/f0/vectors'
        for filename in ['test_export_layouts.py', 'run_export_layout_mutants.py']:
            cmd = [sys.executable, '-B', '-I', filename]
            start = datetime.now(timezone.utc).isoformat()
            result = subprocess.run(cmd, cwd=here, capture_output=True)
            stem = filename.removesuffix('.py')
            (OUT / (stem + '.stdout.txt')).write_bytes(result.stdout)
            (OUT / (stem + '.stderr.txt')).write_bytes(result.stderr)
            commands.append({'argv': cmd, 'cwd': '<exact-scratch>/protocol/f0/vectors', 'startUtc': start,
                'endUtc': datetime.now(timezone.utc).isoformat(), 'exitCode': result.returncode,
                'sourceSha256': sha((here / filename).read_bytes()),
                'stdoutSha256': sha(result.stdout), 'stderrSha256': sha(result.stderr)})
            dump('owner-commands.json', commands)
            assert result.returncode == 0, filename
        spec = importlib.util.spec_from_file_location('layout_review', here / 'export_layouts_reference.py')
        layout = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(layout)
        dump('layout-owner-vectors.json', load('protocol/f0/vectors/export_layouts_vectors.json'))
        probes = []

        def probe(name, doc, expected_acceptance):
            layout.seal(doc)
            try:
                layout.validate_evidence(doc)
                accepted, error = True, None
            except layout.LayoutError as exc:
                accepted, error = False, str(exc)
            assert accepted == expected_acceptance, (name, error)
            probes.append({'name': name, 'checkerAccepted': accepted, 'error': error, 'document': doc})

        base = layout.synthetic_evidence()
        probe('owner history positive', copy.deepcopy(base), True)
        # Isolate the documented ALLOW-only predicate, with all document hashes refreshed.
        old_ad = next(r for r in base['superseded'] if r['type'] == 'AccessDecision')
        grant_death = copy.deepcopy(base)
        dead = next(r for r in grant_death['superseded'] if r['type'] == 'AccessDecision')
        dead['death'] = {'kind': 'overtaken-decision-grant', 'observation': copy.deepcopy(old_ad['death']['observation'])}
        probe('ALLOW with grant death positive', copy.deepcopy(grant_death), True)
        dead['effect']['result'] = '0'
        dead['vHash'] = sha(canonical(dead['effect']))
        probe('DENY with ALLOW-only grant death refused', grant_death, False)
        deny_expiry = copy.deepcopy(grant_death)
        d = next(r for r in deny_expiry['superseded'] if r['type'] == 'AccessDecision')
        d['death'] = {'kind': 'expiry', 'observation': copy.deepcopy(old_ad['death']['observation'])}
        d['death']['observation']['timestamp'] = str(max(int(x['expiresAt']) for x in d['digests']))
        probe('DENY expiry positive', deny_expiry, True)
        deny_seq = copy.deepcopy(grant_death)
        d = next(r for r in deny_seq['superseded'] if r['type'] == 'AccessDecision')
        d['death'] = copy.deepcopy(old_ad['death'])
        probe('DENY sequence positive', deny_seq, True)
        # Legal governance history A -> B -> A. Neither action is ever executed;
        # nonce remains 3, both tuple approvals remain configured, each old digest expires.
        gov = copy.deepcopy(next(r for r in base['conflicts'] if r['type'] == 'GovernanceAction'))
        chain = base['binding']['document']['chains']['pbc']['chainId']

        def obs(number, timestamp):
            return {'chainId': chain, 'blockNumber': str(number), 'blockHash': layout._h('review:block:' + str(number)), 'timestamp': str(timestamp)}

        def record(effect, label, number, timestamp, expiry):
            row = copy.deepcopy(gov)
            row['effect'] = copy.deepcopy(effect)
            row['vHash'] = sha(canonical(effect))
            row['digests'] = [{'digest': layout._h('review:' + label), 'signature': layout._sig('review:' + label),
                               'observation': obs(number, timestamp), 'expiresAt': str(expiry)}]
            return row

        a = gov['effect']
        b = copy.deepcopy(a)
        b['root'] = layout._a('review:root-B')
        c = copy.deepcopy(a)
        c['root'] = layout._a('review:root-C')
        t = 1791521400
        first = record(a, 'A-old', 100, t, t + 60)
        first.update(seq='1', death={'kind': 'expiry', 'observation': obs(110, t + 60)})
        second = record(b, 'B-old', 111, t + 61, t + 121)
        second.update(seq='2', death={'kind': 'expiry', 'observation': obs(121, t + 121)})

        def history(live_effect):
            doc = copy.deepcopy(base)
            doc['conflicts'] = [record(live_effect, 'current', 122, t + 122, t + 182)]
            doc['superseded'] = [copy.deepcopy(first), copy.deepcopy(second)]
            doc['observations'] = [obs(123, t + 123)]
            return doc

        probe('A then B then distinct C positive', history(c), True)
        probe('legal A then B then A accepted', history(a), True)
        probe('adjacent equal first pair refused', history(c) | {'superseded': [copy.deepcopy(first), dict(copy.deepcopy(second), effect=copy.deepcopy(a), vHash=sha(canonical(a)))]}, False)
        probe('adjacent equal live pair refused', history(b), False)
        for target, idx in [('superseded', 1), ('conflicts', 0)]:
            doc = history(c)
            doc[target][idx]['digests'][0]['observation'] = obs(109 if idx else 120, t+59 if idx else t+120)
            probe('early generation refused '+target, doc, False)
        exact = history(c)
        exact['superseded'][1]['digests'][0]['observation'] = copy.deepcopy(first['death']['observation'])
        probe('same death observation permitted', exact, True)
        logged = history(c)
        logged['superseded'][1]['digests'][0]['observation'] = obs(109, t+59)
        logged['faultLog'] = copy.deepcopy(layout.synthetic_evidence('cleared')['faultLog'])
        # The cleared fault references DBC, so keep the unrelated history observations.
        logged['observations'] = copy.deepcopy(layout.synthetic_evidence('cleared')['observations'])
        probe('fault clear exempts monotonic generation order', logged, True)
        malformed = history(c)
        malformed['superseded'][1]['seq'] = '1'
        probe('duplicate append sequence negative control', malformed, False)
        early = history(c)
        early['superseded'][0]['death']['observation'] = obs(109, t + 59)
        probe('death before expiry negative control', early, False)
        dump('layout-probes.json', probes)
        after = {str(p.relative_to(scratch)): sha(p.read_bytes()) for p in scratch.rglob('*') if p.is_file()}
        assert before == after
        dump('scratch-input-hashes.json', {'before': before, 'after': after})
        prov['scratchInputsStable'] = {'files': len(before), 'allPrePostHashesEqual': True}
    dump('input-provenance.json', prov)
    summary = {'status': 'REVISION9_LAYOUT_SCOPED_DESIGN_ACK_NO_MAPPING_OR_FREEZE',
        'bindingHashes': hashes, 'independentProfileCases': len(case_results),
        'layoutProbes': len(probes), 'ownerCommandsAllExit0': len(commands),
        'communicationPaths': len(prov['latestCommunication']), 'ownerManifests': prov['ownerManifests'],
        'limits': 'Specification-only helpers and synthetic placeholder signatures; no runtime, chain, storage, timing, Forge, TLC, F implementation or RQ gate.'}
    dump('summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    run()
