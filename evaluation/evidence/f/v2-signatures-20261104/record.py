"""Retain this slice's exact commands, exits, UTC and output hashes."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from evaluation.manifests import record_command

OUT = Path(__file__).resolve().parent
label, *argv = sys.argv[1:]
log = OUT / (label + '.txt')
if log.exists():
    raise SystemExit('Refuse to overwrite a command log')
row = record_command(argv, ROOT, log, timeout=900)
index = OUT / 'commands.json'
rows = json.loads(index.read_text()) if index.exists() else []
rows.append(row | {'log': str(log.relative_to(ROOT))})
index.write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(row, indent=2))
raise SystemExit(row['exitCode'])
