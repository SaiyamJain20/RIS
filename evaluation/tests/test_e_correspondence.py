"""Real model checks: missing binding, vacuous denial and weak mutants must fail."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def run_model(filename):
    model = ROOT / 'evaluation/models/e' / filename
    assert model.is_file(), f'C-E2 model not implemented: {filename}'
    pin = json.loads((ROOT / 'evaluation/toolchain.json').read_text())['proverif']
    binary = Path(pin['path'])
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == pin['binarySha256']
    result = subprocess.run([str(binary), str(model)], cwd=ROOT, capture_output=True,
                            text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not result.stderr, result.stderr
    assert 'cannot be proved' not in result.stdout
    verdicts = re.findall(r'^RESULT .+ is (true|false)\.$', result.stdout, re.MULTILINE)
    return verdicts, result.stdout


def test_full_signed_tuple_implies_user_and_witness_agreement():
    # Removing any checked binding must break full eight-field agreement.
    verdicts, _ = run_model('access.pv')
    assert verdicts[:3] == ['true', 'true', 'true']


@pytest.mark.parametrize('model', ['access.pv', 'access_mutant.pv'])
def test_legitimate_grant_reachable_and_policy_denial_preserved(model):
    # A deny-all witness/sink must break reachability; grant-all breaks denial.
    verdicts, _ = run_model(model)
    assert len(verdicts) == 5
    assert verdicts[3:] == ['false', 'true']  # not-event allowed false, denied true


def test_unsigned_destination_mutant_has_real_attack_and_other_fields_agree():
    # Reintroducing destination binding removes the attack; disabling signatures
    # breaks the seven-field projection. Both mistakes must be detected.
    verdicts, output = run_model('access_mutant.pv')
    assert verdicts[:3] == ['false', 'false', 'true']
    correspondence_blocks = [b for b in output.split('-- Query ')
                             if b.startswith('event(Grant(')]
    assert len(correspondence_blocks) == 3
    for block in correspondence_blocks[:2]:
        assert 'A trace has been found' in block
        assert re.search(r'^RESULT .+ is false\.$', block, re.MULTILINE)


@pytest.mark.parametrize('old,new,index,expected', [
    ('if d = allowedData then', 'if allowedData = deniedData then', 3, 'true'),
    ('if d = allowedData then', '', 4, 'false'),
    ('if claimedDestination = t then', '', 0, 'false'),
])
def test_checks_detect_vacuity_policy_bypass_and_unchecked_envelope(tmp_path, old, new, index, expected):
    # Deliberate scratch mutations never alter the reviewed model in place.
    model = tmp_path / 'sensitivity.pv'
    baseline = (ROOT / 'evaluation/models/e/access.pv').read_text()
    assert old in baseline
    model.write_text(baseline.replace(old, new, 1))
    verdicts, _ = run_model(model)
    assert len(verdicts) == 5
    assert verdicts[index] == expected
