"""Verify review evidence and immutable historical inputs; no owner helpers rerun."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run():
    for p in OUT.glob('*.json'):
        json.loads(p.read_text())
    prov = json.loads((OUT / 'input-provenance.json').read_text())
    owner = prov['refs']['agent-2']
    for row in json.loads((OUT / 'owner-commands.json').read_text()):
        name = row['argv'][-1]
        stem = name.removesuffix('.py')
        assert row['exitCode'] == 0
        assert sha(subprocess.check_output(['git', 'show', owner + ':protocol/f0/vectors/' + name], cwd=ROOT)) == row['sourceSha256']
        for stream in ['stdout', 'stderr']:
            assert sha((OUT / (stem + '.' + stream + '.txt')).read_bytes()) == row[stream + 'Sha256']
    for name, count in [('test_d50_reference', 126), ('test_export_layouts', 62), ('check_wire_examples', 77)]:
        assert sum(line.startswith('ok ') for line in (OUT / (name + '.stdout.txt')).read_text().splitlines()) == count
    probes = json.loads((OUT / 'layout-probes.json').read_text())
    assert len(probes) == 7
    assert [r['checkerAccepted'] for r in probes] == [True, True, True, True, False, False, False]
    bad = probes[2]['document']
    dead = next(r for r in bad['superseded'] if r['type'] == 'AccessDecision')
    assert dead['effect']['result'] == '0' and dead['death']['kind'] == 'overtaken-decision-grant'
    recurrence = probes[4]['document']
    a_old, b_old = recurrence['superseded']
    live = recurrence['conflicts'][0]
    assert a_old['effect'] == live['effect'] != b_old['effect']
    assert a_old['keyField'] == b_old['keyField'] == live['keyField']
    for previous, following in [(a_old, b_old), (b_old, live)]:
        assert previous['effect'] != following['effect']
        assert int(previous['death']['observation']['timestamp']) >= int(previous['digests'][0]['expiresAt'])
        assert int(previous['death']['observation']['timestamp']) < int(following['digests'][0]['observation']['timestamp'])
        assert int(previous['death']['observation']['blockNumber']) < int(following['digests'][0]['observation']['blockNumber'])
    for p in [ROOT / 'interfaces/proposals/v2/MANIFEST.json',
              ROOT / 'evaluation/evidence/reviews/f0-v2-candidate1-20261104/review-manifest.json',
              ROOT / 'evaluation/evidence/reviews/f0-v2-owner-review-20261104/review-manifest.json']:
        for path, digest in json.loads(p.read_text())['files'].items():
            assert sha((ROOT / path).read_bytes()) == digest, path
    assert not subprocess.check_output(['git', 'diff', '--name-only', prov['refs']['agent-3'], '--',
        'interfaces/proposals/v2', 'interfaces/v1', 'ledger', 'protocol', 'archive',
        'evaluation/evidence/frozen', 'evaluation/evidence/reviews/f0-v2-owner-review-20261104'], cwd=ROOT)
    assert subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT).decode().strip() == 'agent-3'
    print('REVIEW_EVIDENCE_VERIFIED: six owner command logs, seven probes, three historical manifests; unchanged historical/module bytes; no RQ gate result.')


if __name__ == '__main__':
    run()
