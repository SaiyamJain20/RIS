"""Retain exact review commands, UTC, exits and lossless compressed output."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from evaluation.manifests import record_command

label, cwd, *argv = sys.argv[1:]
log = OUT / (label + '.txt')
assert not log.exists() and not log.with_suffix('.txt.gz').exists()
row = record_command(argv, cwd, log, timeout=1200, owned_process_group=True)
raw = log.read_bytes()
packed = log.with_suffix('.txt.gz')
packed.write_bytes(gzip.compress(raw, mtime=0))
log.unlink()
row.update(log=str(packed.relative_to(ROOT)), contentEncoding='gzip',
           compressedSha256=hashlib.sha256(packed.read_bytes()).hexdigest())
index = OUT / 'commands.json'
rows = json.loads(index.read_text()) if index.exists() else []
index.write_text(json.dumps(rows + [row], indent=2) + '\n')
print(json.dumps(row, indent=2), flush=True)
raise SystemExit(row['exitCode'])
