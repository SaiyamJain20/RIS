"""Narrow in-memory bypass controls; source on disk stays unchanged."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'evaluation/export_snapshot_v2.py'
TEST = 'evaluation/tests/test_export_snapshot_v2.py'
source = SOURCE.read_text()
controls = [
    ('exit-status', 'type(exit_code) is int and exit_code == 0', 'True',
     'test_refusal_usage_failure_or_wrong_kind_never_succeeds[changes0]'),
    ('stderr', 'type(stderr) is bytes and not stderr', 'True',
     'test_refusal_usage_failure_or_wrong_kind_never_succeeds[changes4]'),
    ('framing', 'stdout == canonical', 'True',
     'test_export_requires_exact_canonical_single_line[extra-lf]'),
    ('physical-marker', "marker == dict(schema='2', owner=expected_owner, binding_v2=binding)", 'True',
     'test_physical_marker_cannot_be_self_declared[owner-BindingExport]'),
    ('anchored-binding', 'verify_export(export, **context)', 'pass',
     'test_existing_context_and_signature_checks_are_composed[context-BindingExport]'),
    ('signed-history', 'history = verify_signed_history(export, **context)', 'history = {}',
     'test_existing_context_and_signature_checks_are_composed[anchor-or-signature-WitnessEvidence]'),
    ('duplicate-marker', 'if key in value:', 'if False:',
     'test_duplicate_marker_keys_refused_even_if_last_value_matches[schema]'),
]
rows = []
for name, old, new, test in controls:
    assert source.count(old) == 1, name
    mutated = source.replace(old, new)
    code = ('import sys,types,pytest; '
            'm=types.ModuleType("evaluation.export_snapshot_v2"); '
            'sys.modules[m.__name__]=m; '
            f'exec(compile({mutated!r}, {str(SOURCE)!r}, "exec"),m.__dict__); '
            f'raise SystemExit(pytest.main([{TEST + "::" + test!r},"-q"]))')
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, timeout=30)
    output = result.stdout + result.stderr
    print(name + '\n' + output.decode(), flush=True)
    assert result.returncode == 1 and b'1 failed' in output and b'FAILED ' in output, name
    assert b'ERROR at setup' not in output and b'ERROR collecting' not in output, name
    rows.append(dict(name=name, test=test, exitCode=result.returncode,
        outputSha256=hashlib.sha256(output).hexdigest(),
        mutatedSourceSha256=hashlib.sha256(mutated.encode()).hexdigest()))
assert SOURCE.read_text() == source
print(json.dumps(dict(controls=rows, sourceUnchanged=True), indent=2))
