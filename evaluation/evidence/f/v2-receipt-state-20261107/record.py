"""Immutable isolated command receipts; no service/execution authorization."""
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'evaluation/runs/v2-receipt-state-20261107'
sys.path.insert(0, str(ROOT))
from evaluation.manifests import record_command

label, *argv = sys.argv[1:]
receipt = OUT / (label + '-command.json')
assert not receipt.exists(), 'receipt is immutable; use a new label'
log = RUN / (label + '.log')
result = record_command(argv, ROOT, log, timeout=1800, owned_process_group=True)
receipt.write_text(json.dumps(result, indent=2) + '\n')
(OUT / (label + '.log.gz')).write_bytes(gzip.compress(log.read_bytes(), mtime=0))
print(json.dumps(result, indent=2))
print(log.read_text()[-3500:])
raise SystemExit(result['exitCode'])
