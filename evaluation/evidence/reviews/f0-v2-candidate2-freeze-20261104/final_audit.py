"""Review only owned pending paths and preserve exact proposal/freeze hashes."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OWNED = {'communication/BOARD.md', 'communication/GATES.md',
         'communication/INTEGRATION.md', 'communication/agent-3/STATUS.md',
         'communication/agent-3/HANDOFF.md', 'communication/F0_FREEZE_CANDIDATE2.json',
         'communication/agent-3/outbox/0072-freeze-f0-candidate2-exact-mapping-acks.md',
         'evaluation/README.md'}
DIRS = ('evaluation/evidence/reviews/f0-v2-candidate2-freeze-20261104/',
        'evaluation/evidence/reviews/f0-v2-candidate2-ledger-ack-20261104/')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    assert git('branch', '--show-current').decode().strip() == 'agent-3'
    files = set(git('diff', '--name-only', 'HEAD').decode().splitlines())
    files.update(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
    assert OWNED <= files
    assert all(p in OWNED or p.startswith(DIRS) for p in files), sorted(files)
    assert not git('diff', 'HEAD', '--', 'interfaces', 'ledger', 'protocol', 'archive',
                   'communication/agent-1', 'communication/agent-2')
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    frozen = ROOT / 'communication/F0_FREEZE_CANDIDATE2.json'
    digest = hashlib.sha256(frozen.read_bytes()).hexdigest()
    assert digest == 'f9f0906faf8dbfb9ccd2d06a794c715bb6a3167b6f273a50347742db41196df5'
    request = (ROOT / 'communication/agent-3/outbox/0072-freeze-f0-candidate2-exact-mapping-acks.md').read_text()
    assert digest in request and 'Type: FREEZE' in request
    result = {'status': 'OWNED_DIFF_AND_REQUEST_HASH_PASS', 'freezeRequestSha256': digest,
              'implementationAuthorized': False, 'executionAuthorized': False,
              'reviewedPaths': sorted(files)}
    (OUT / 'final-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Owned diff and request hash verified:', len(files), 'paths; no peer/historical edits.')


if __name__ == '__main__':
    main()
