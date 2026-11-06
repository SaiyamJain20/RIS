"""In-memory guard-removal controls. Never alter source files on disk."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'evaluation/store_snapshot_v2.py'
TEST = 'evaluation/tests/test_store_snapshot_v2.py'
source = SOURCE.read_text()
controls = [
    ('ignore-wal', "'?mode=ro'", "'?mode=ro&immutable=1'", 'test_wal_only_refusal_is_not_in_main_hash'),
    ('omit-table-rows', "for r in cursor]", "for r in []]", 'test_wal_only_refusal_is_not_in_main_hash'),
    ('ignore-logical-state', 'if before.logical != after.logical:', 'if False:', 'test_wal_only_refusal_is_not_in_main_hash'),
    ('ignore-marker-bytes', 'if before.marker != after.marker:', 'if False:', 'test_exact_marker_bytes_are_separate_from_logical_state'),
    ('shared-lock', 'fcntl.LOCK_EX | fcntl.LOCK_NB', 'fcntl.LOCK_SH | fcntl.LOCK_NB', 'test_lock_is_exclusive_and_released_after_exception'),
    ('physical-only-comparison', 'if before.logical != after.logical:', 'if before.main_sha256 != after.main_sha256:', 'test_wal_only_refusal_is_not_in_main_hash'),
]
rows = []
for name, old, new, test in controls:
    assert source.count(old) == 1, (name, source.count(old))
    mutated = source.replace(old, new)
    code = ('import sys,types,pytest; '
            'm=types.ModuleType("evaluation.store_snapshot_v2"); '
            'sys.modules[m.__name__]=m; '
            f'exec(compile({mutated!r}, {str(SOURCE)!r}, "exec"),m.__dict__); '
            f'raise SystemExit(pytest.main([{TEST + "::" + test!r},"-q"]))')
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, timeout=30)
    output = result.stdout + result.stderr
    print(name + '\n' + output.decode(), flush=True)
    assert result.returncode == 1 and b'1 failed' in output and b'FAILED ' in output, name
    assert b'ERROR at setup' not in output and b'ERROR collecting' not in output, name
    rows.append({'name': name, 'test': test, 'exitCode': result.returncode,
                 'outputSha256': hashlib.sha256(output).hexdigest(),
                 'mutatedSourceSha256': hashlib.sha256(mutated.encode()).hexdigest()})
assert SOURCE.read_text() == source
print(json.dumps({'controls': rows, 'sourceUnchanged': True}, indent=2))
