"""One-command gate E run (A1-0082 P4-1; S3-0002 section 3.1 without the mutant and window stages).

Aggregation only: every catalog row goes through the real `evaluation.e2.run_row`, selected by the
existing `e2.create_plan` slice flags. Services are replaced by a control-flow double of `e1._profile`
that writes TEST-ONLY proof files (never peer or gate evidence). ProVerif runs for real with the
declared local build. No Anvil, no adapter, no repository write.
"""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOLO = 'solo-correlated'
P = ('paper-strict', 'paper-minimal', 'repaired-e')
SLICES = [('recovery-expiry', 'expired_retry'), ('duplicate-outcome', 'duplicate_outcome'), ('nonce-replay', 'nonce_replay'),
          ('sl1-subject', 'subject_substitution'), ('sl2-relay', 'relay_stress'), ('sl3-audit', 'audit_stress'),
          ('sl4-receipt', 'receipt_stress'), ('sl5-trust', 'trust_stress'), ('sl6-barrier', 'barrier_stress'),
          ('sl7-destination', 'destination_stress')]
STATUS = {'recovery-expiry': 'E2_RECOVERY_EXPIRY_SLICE_PASS', 'duplicate-outcome': 'E2_DUPLICATE_OUTCOME_SLICE_PASS',
          'nonce-replay': 'E2_NONCE_REPLAY_SLICE_PASS', 'sl1-subject': 'E2_SUBJECT_SUBSTITUTION_SLICE_PASS',
          'sl2-relay': 'E2_RELAY_STRESS_SLICE_PASS', 'sl3-audit': 'E2_AUDIT_STRESS_SLICE_PASS', 'sl4-receipt': 'E2_RECEIPT_STRESS_SLICE_PASS',
          'sl5-trust': 'E2_TRUST_STRESS_SLICE_PASS', 'sl6-barrier': 'E2_BARRIER_STRESS_SLICE_PASS',
          'sl7-destination': 'E2_DESTINATION_STRESS_SLICE_PASS'}
GUARDS = {'E01-same-nonce-distinct-digests-repaired-e': 'REPLAY',
          'E03-receipt-binding-control-requestDigest-repaired-e': 'WRONG_SUBJECT',
          'E03-receipt-binding-control-gid-repaired-e': 'WRONG_SUBJECT',
          'E03-receipt-binding-control-dataId-repaired-e': 'WRONG_SUBJECT',
          'E02-signed-list-rollback-repaired-e': 'STALE_ANCHOR', 'E02-post-barrier-revocation-repaired-e': 'STALE_STATE',
          'E02-expired-duty-repaired-e': 'EXPIRED', 'E01-wrong-destination-repaired-e': 'WRONG_DESTINATION'}
D47 = {'E03-crash-after-intent-paper-strict', 'E03-crash-after-intent-paper-minimal',
       'E03-crash-after-send-paper-strict', 'E03-crash-after-send-paper-minimal'}
D47_LABEL = 'frozen BLOCKED / decided SPEC_GAP, UNPROVED (D47)'
C4_NOTE = 'integrated live mutant matrix not run'
C4_REPO = ['repo:ledger/evidence/p3-mutant-suite-rerun/', 'repo:evaluation/evidence/e2/p3-proverif-20261012/',
           'repo:communication/agent-1/outbox/0080-decision-human-mutant-evidence-scope.md']


def gate():
    return importlib.import_module('evaluation.e_gate')


def e1():
    return importlib.import_module('evaluation.e1')


def e2():
    return importlib.import_module('evaluation.e2')


def criteria():
    return importlib.import_module('evaluation.gate').E_CRITERIA


@pytest.fixture(scope='module')
def plan():
    return gate().create_plan(run_id='E-gate-test', freeze_message='S3-0021')


def catalog_ids():
    ids = [c['id'] for c in json.loads((ROOT/'evaluation/scenarios/e0_cases.json').read_text())['cases']]
    return ids+[c['id'] for c in json.loads((ROOT/'evaluation/scenarios/e0_supplement_cases.json').read_text())['cases']]


# ---------------------------------------------------------------- plan

def test_gate_plan_aggregates_the_ten_slice_plans_and_all_56_rows(plan):
    gate().verify_plan(plan)  # real: gate equality plus e2.verify_plan of every slice plan
    assert [(s['name'], s['flag']) for s in plan['slices']] == SLICES
    for s in plan['slices']:
        assert s['plan'] == e2().create_plan(run_id='E-gate-test-'+s['name'], freeze_message='S3-0021', review_mode=SOLO, **{s['flag']: True})
        assert s['runId'] == s['plan']['runId'] and len(s['caseIds']) == len(s['plan']['matrix'])
        if 'caseIds' in s['plan']:
            assert s['caseIds'] == s['plan']['caseIds']
    recovery = plan['slices'][0]
    assert recovery['caseIds'] == ['E03-crash-'+point+'-'+p for p in P for point in ('after-intent', 'after-send')]
    ids = [i for s in plan['slices'] for i in s['caseIds']]
    assert len(ids) == 56 == len(set(ids)) and set(ids) == set(catalog_ids())
    assert plan['rq'] == 'E' and plan['executionMode'] == 'real-integrated' and plan['adapterMode'] == 'symbolic'
    assert plan['interfaceVersion'] == 'v1' and plan['freezeMessage'] == 'S3-0021'
    assert plan['reviewMode'] == SOLO and 'correlated' in plan['reviewDisclosure'] and plan['reviewDecision'] == 'A1-0082'
    assert all(s['history']['evidence'].startswith('evaluation/evidence/e2/') and s['history']['message'] for s in plan['slices'])


def test_gate_plan_drops_the_mutant_and_window_stages_by_human_decision(plan):
    assert plan['stages'] == ['verify-freeze-and-versions', 'source-bracket-pre', 'catalog-56', 'proverif',
                              'source-bracket-post', 'manifest', 'gate-evidence']
    assert set(plan['droppedStages']) == {'mutants', 'window'}
    assert 'A1-0080' in plan['droppedStages']['mutants'] and 'A1-0081' in plan['droppedStages']['window']
    assert 'mutant' not in json.dumps(plan['stages']).lower() and 'window' not in json.dumps(plan['stages']).lower()
    assert set(plan['criteriaRules']) == set(criteria())
    c4 = plan['criteriaRules']['repairs-and-mutants']
    assert C4_NOTE in c4['note'] and 'A1-0080' in c4['note']
    assert all(path in c4['evidence'] for path in C4_REPO)
    assert plan['criteriaRules']['RQ1-report']['pendingAfterRun'] is True
    assert plan['criteriaRules']['three-matching-acks']['pendingAfterRun'] is True
    assert {k: v['error'] for k, v in plan['guardRows'].items()} == GUARDS
    assert 'cannot kill' in plan['guardRows']['E01-wrong-destination-repaired-e']['mutant']


def test_gate_plan_hashes_its_evidence_inputs_and_pins_the_declared_proverif_build(plan):
    inputs = plan['gateInputs']
    for path in ('evaluation/models/e/access.pv', 'evaluation/models/e/access_mutant.pv',
                 'evaluation/evidence/e2/formal-and-hook-review-20261009/positive-final.stdout',
                 'evaluation/evidence/e2/formal-and-hook-review-20261009/mutant-final.stdout',
                 'evaluation/evidence/e2/p3-proverif-20261012/access.stdout', 'evaluation/evidence/e2/p3-proverif-20261012/access_mutant.stdout',
                 'ledger/evidence/p3-mutant-suite-rerun/mutants.json', 'ledger/evidence/p3-mutant-suite-rerun/mutants.txt',
                 'communication/agent-1/outbox/0080-decision-human-mutant-evidence-scope.md',
                 'communication/agent-1/outbox/0081-decision-human-window-evidence-p3-closed.md',
                 'communication/agent-1/outbox/0082-decision-p4-gate-run-report-acks.md'):
        assert inputs[path] == hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), path
    assert inputs['ledger/evidence/p3-mutant-suite-rerun/mutants.json'].startswith('60a30adc')
    tool = plan['proverif']['tool']
    assert tool['resolution'] == 'declared-local-build' and tool['sha256'].startswith('bc2cd5ed')
    expected = {Path(m['model']).name: m['expectedVerdicts'] for m in plan['proverif']['models']}
    assert expected == {'access.pv': ['true', 'true', 'true', 'false', 'true'],
                        'access_mutant.pv': ['false', 'false', 'true', 'false', 'true']}
    assert all(set(m['references']) == {'A3-0033', 'p3-proverif-20261012'} for m in plan['proverif']['models'])


@pytest.mark.parametrize('kwargs', [dict(review_mode='strict', freeze_message='A3-0051'), dict(freeze_message='A3-0051'),
                                    dict(freeze_message='S2-0021'), dict(run_id='bad id')])
def test_gate_plan_is_solo_only_with_an_s3_freeze(kwargs):
    options = dict(run_id='E-gate-test', freeze_message='S3-0021'); options.update(kwargs)
    with pytest.raises(ValueError):
        gate().create_plan(**options)


@pytest.mark.parametrize('change', ['slice-dropped', 'slice-plan', 'stage-added', 'proverif-expected', 'gate-input', 'criterion-4-note'])
def test_changed_gate_plan_refuses(plan, change):
    p = copy.deepcopy(plan)
    if change == 'slice-dropped': p['slices'].pop()
    if change == 'slice-plan': p['slices'][9]['plan']['destinationProbe']['expiryBoundaryRepaired'] = 'consume one second later'
    if change == 'stage-added': p['stages'].insert(3, 'mutants')
    if change == 'proverif-expected': p['proverif']['models'][1]['expectedVerdicts'][0] = 'true'
    if change == 'gate-input': p['gateInputs'][sorted(p['gateInputs'])[0]] = '00'*32
    if change == 'criterion-4-note': p['criteriaRules']['repairs-and-mutants']['note'] = 'all mutants killed live'
    with pytest.raises(ValueError):
        gate().verify_plan(p)


# ---------------------------------------------------------------- verify-freeze

def test_verify_freeze_rechecks_every_frozen_copy_and_moved_owner_inventories():
    result = gate().verify_freeze()
    assert result['status'] == 'UNCHANGED' and result['freezeSha256Ok'] is True and len(result['copies']) == 15
    assert all(c['ok'] for c in result['copies'])
    owners = [c for c in result['copies'] if c['path'].startswith('interfaces/v1/owners/')]
    assert len(owners) == 2 and all(c['source']['frozenGitBlob'] is True for c in owners)


def test_verify_freeze_reports_a_changed_copy():
    freeze = json.loads((ROOT/'interfaces/v1/FREEZE.json').read_text())
    freeze['frozenCopies']['interfaces/v1/BOUNDARY.md']['sha256'] = '00'*32
    result = gate().verify_freeze(freeze)
    assert result['status'] == 'CHANGED'
    assert [c['path'] for c in result['copies'] if not c['ok']] == ['interfaces/v1/BOUNDARY.md']


# ---------------------------------------------------------------- ProVerif

def test_proverif_stage_reproduces_the_saved_outputs_byte_for_byte(tmp_path, plan):
    summary = gate().run_proverif(plan, tmp_path)
    assert summary['matched'] is True and set(summary['runs']) == {'access', 'access_mutant'}
    for name, run in summary['runs'].items():
        assert run['exitCode'] == 0 and run['stderrBytes'] == 0 and run['verdicts'] == run['expectedVerdicts']
        assert all(ref['fullOutputIdentical'] is True for ref in run['references'].values())
        saved = ROOT/'evaluation/evidence/e2/p3-proverif-20261012'/(name+'.stdout')
        assert (tmp_path/'proverif'/(name+'.stdout')).read_bytes() == saved.read_bytes()
    assert json.loads((tmp_path/'proverif/summary.json').read_text())['matched'] is True


@pytest.mark.parametrize('change', ['verdict', 'reference'])
def test_proverif_stage_reports_a_mismatch(tmp_path, plan, change):
    p = copy.deepcopy(plan); model = p['proverif']['models'][0]
    if change == 'verdict': model['expectedVerdicts'][3] = 'true'
    if change == 'reference': model['references']['A3-0033']['sha256'] = '00'*32
    summary = gate().run_proverif(p, tmp_path)
    assert summary['matched'] is False and summary['runs']['access']['matched'] is False
    assert summary['runs']['access_mutant']['matched'] is True


# ---------------------------------------------------------------- execution (control-flow doubles)

def profile_double(calls, fail=None):
    """TEST-ONLY stand-in for e1._profile: writes the proof files each slice check reads; never peer evidence."""
    fail = fail or {}
    m = e2()

    def profile(plan, profile, output, record, *, recovery_point=None, expired_retry=False, duplicate_outcome=False,
                nonce_replay=False, subject_substitution=False, relay_stress=None, audit_stress=None, receipt_stress=None,
                receipt_field=None, trust_stress=None, barrier_stress=None, destination_stress=None):
        key = (output.parent.parent.name, output.parent.name); calls.append(key)
        output.mkdir(parents=True)

        def put(rel, data):
            path = output/rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data))
        record['servicesStarted'].append(dict(profile=profile, chain='pbc', port=18545, pid=0, testOnly=True))
        if fail.get(key) == 'raise':
            raise RuntimeError('TEST-ONLY injected row failure')
        put('alice/result.json', dict(ok=True, delivery='unknown')); put('bob/result.json', dict(ok=True, delivery='unknown'))
        if recovery_point is not None:
            put('recovery/result.json', dict(ok=True, delivery='unknown'))
            put('expired-retry/result.json', dict(ok=True, error='EXPIRED', delivery='unknown', workerUnchanged=True, nativeUnchanged=True))
        elif duplicate_outcome or nonce_replay:
            put('alice/'+('duplicate-outcome' if duplicate_outcome else 'nonce-replay')+'/result.json',
                dict(ok=True, error='REPLAY', delivery='unknown', workerUnchanged=True, nativeUnchanged=True, identicalCalldata=True))
        elif subject_substitution:
            repaired = profile == 'repaired-e'
            put('subject-stress/subject-substitution/result.json',
                dict(ok=True, delivery='unknown', workerUnchanged=True, classification='REPAIR_SUPPORTED' if repaired else 'SPEC_GAP',
                     error='WRONG_SUBJECT' if repaired else None))
            if not repaired:
                put('subject-stress/subject-completion/result.json',
                    dict(ok=True, classification='SPEC_GAP', delivery='unknown', bobDecryptable=True, aliceError='WRONG_SUBJECT', outcomeTested=False))
        else:
            if receipt_stress is not None:
                kind, variant = 'receipt', receipt_stress; classification, error = m.RECEIPT_EXPECTED[variant]
            else:
                kind, variant, table = next((k, v, t) for k, v, t in (
                    ('relay', relay_stress, m.RELAY_EXPECTED), ('audit', audit_stress, m.AUDIT_EXPECTED), ('trust', trust_stress, m.TRUST_EXPECTED),
                    ('barrier', barrier_stress, m.BARRIER_EXPECTED), ('destination', destination_stress, m.DESTINATION_EXPECTED)) if v is not None)
                classification, error = table[(profile, variant)]
            if fail.get(key) == 'wrong-class':
                classification = 'SUPPORTED' if classification != 'SUPPORTED' else 'SPEC_GAP'
            proof = dict(ok=True, delivery='unknown', variant=variant, classification=classification, error=error, testOnly=True)
            if kind == 'receipt':
                proof['field'] = receipt_field
            put(kind+'-stress/result.json', proof)
        record['profiles'][profile] = dict(status='CONTROL_PASS', servicesStopped=True)
    return profile


@pytest.fixture
def doubles(monkeypatch):
    """No services and no peer evidence: profile double, TEST-ONLY ACK record, no-op per-slice e2.verify_plan (cost)."""
    calls = []; verified = []
    monkeypatch.setattr(e1(), '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    monkeypatch.setattr(e2(), 'verify_plan', lambda plan: verified.append(plan['runId']))

    def install(fail=None):
        monkeypatch.setattr(e1(), '_profile', profile_double(calls, fail))
        return calls, verified
    return install


def write_plan(tmp_path, plan):
    path = tmp_path/'integration-plan.json'; path.write_text(json.dumps(plan, indent=1)+'\n'); return path


def test_gate_run_sends_all_56_rows_through_e2_run_row_and_keeps_the_slice_layouts(tmp_path, plan, doubles):
    calls, verified = doubles(); out = tmp_path/'gate'
    result = gate().execute(write_plan(tmp_path, plan), None, out)
    assert result['status'] == 'PASS', result.get('failure')
    assert result['rq'] == 'E' and result['executionMode'] == 'real-integrated' and result['interfaceVersion'] == 'v1'
    assert result['adapterMode'] == 'symbolic' and 'correlated' in result['reviewDisclosure']
    assert result['sourceStable'] is True and result['worktreeUnchanged'] is True
    assert len(result['rows']) == 56 and {r['status'] for r in result['rows']} == {'PASS'}
    assert len(calls) == 56 == len(set(calls))  # each row exactly once
    assert len(verified) >= 56  # e2.run_row re-verifies its slice plan before every row
    assert [r['caseId'] for r in result['rows']] == [i for s in plan['slices'] for i in s['caseIds']]
    catalog = out/'catalog'
    for name, kind, n in (('sl2-relay', 'relay', 7), ('sl3-audit', 'audit', 6), ('sl4-receipt', 'receipt', 7),
                          ('sl5-trust', 'trust', 6), ('sl6-barrier', 'barrier', 9), ('sl7-destination', 'destination', 6)):
        assert len(list((catalog/name).glob('*/*/'+kind+'-stress/result.json'))) == n
    assert len([p for p in (catalog/'sl1-subject').glob('*-subject-substitution/*') if p.is_dir()]) == 3
    assert len(list(catalog.rglob('recovery/result.json'))) == 6
    assert len(list(catalog.rglob('alice/duplicate-outcome/result.json'))) == 3
    assert len(list(catalog.rglob('alice/nonce-replay/result.json'))) == 3
    assert (catalog/'recovery-expiry/paper-strict-after_intent/paper-strict/expired-retry/result.json').is_file()
    for name, status in STATUS.items():
        assert json.loads((catalog/name/'manifest.json').read_text())['status'] == status
    coverage = json.loads((out/'catalog-coverage-56.json').read_text())['rows']
    assert len(coverage) == 56 and {r['caseId'] for r in coverage} == set(catalog_ids())
    assert {r['caseId'] for r in coverage if r.get('label') == D47_LABEL} == D47
    assert all(r['status'] == 'PASS' and r['reportedClassification'] for r in coverage)
    evidence = json.loads((out/'gate-evidence.json').read_text())['criteria']
    assert set(evidence) == set(criteria())
    assert {k for k, v in evidence.items() if v['status'] != 'VERIFIED'} == {'RQ1-report', 'three-matching-acks'}
    assert {v['status'] for k, v in evidence.items() if k in ('RQ1-report', 'three-matching-acks')} == {'PENDING'}
    c4 = evidence['repairs-and-mutants']
    assert C4_NOTE in c4['note'] and all(path in c4['evidencePaths'] for path in C4_REPO)
    assert sum(path.startswith('run:catalog/') for path in c4['evidencePaths']) == len(GUARDS)
    assert result['hostMemory']['before']['MemAvailable'] > 0 and result['hostMemory']['after']['MemAvailable'] > 0
    assert 'manifest.json' not in result['resultFiles'] and 'gate-evidence.json' in result['resultFiles']
    for rel, digest in result['resultFiles'].items():
        assert hashlib.sha256((out/rel).read_bytes()).hexdigest() == digest
    assert json.loads((out/'manifest.json').read_text())['status'] == 'PASS'
    # evaluation.gate stays fail-closed on a complete run (A1-0082): no automated PASS
    decision = importlib.import_module('evaluation.gate').check_gate(out)
    assert decision['decision'] == 'BLOCKED' and 'RQ1-report' in decision['missing'] and 'three-matching-acks' in decision['missing']


def test_gate_run_keeps_failed_rows_and_continues_without_retry(tmp_path, plan, doubles, monkeypatch):
    monkeypatch.setattr(gate(), 'verify_plan', lambda p: None)
    fail = {('sl6-barrier', 'repaired-e-expired-duty'): 'wrong-class', ('sl2-relay', 'paper-minimal-forged-tuple'): 'raise'}
    calls, _ = doubles(fail); out = tmp_path/'gate'
    result = gate().execute(write_plan(tmp_path, plan), None, out)
    assert result['status'] == 'FAILED' and len(calls) == 56 == len(set(calls))
    failed = {(r['slice'], r['case']): r for r in result['rows'] if r['status'] != 'PASS'}
    assert set(failed) == set(fail) and all(r['status'] == 'FAILED' and r['failure']['message'] for r in failed.values())
    assert sum(r['status'] == 'PASS' for r in result['rows']) == 54
    for name in ('sl2-relay', 'sl6-barrier'):
        record = json.loads((out/'catalog'/name/'manifest.json').read_text())
        assert record['status'] == 'FAILED' and len(record['failure']['failedCases']) == 1
    assert json.loads((out/'catalog/sl7-destination/manifest.json').read_text())['status'] == 'E2_DESTINATION_STRESS_SLICE_PASS'
    evidence = json.loads((out/'gate-evidence.json').read_text())['criteria']
    for name in ('legitimate-and-denied-controls', 'E01-E02-E03-classification', 'repairs-and-mutants', 'real-two-chain-and-recovery'):
        assert evidence[name]['status'] == 'FAILED'
    assert evidence['proverif-and-negative-control']['status'] == 'VERIFIED'
    coverage = {r['caseId']: r for r in json.loads((out/'catalog-coverage-56.json').read_text())['rows']}
    assert coverage['E02-expired-duty-repaired-e']['status'] == 'FAILED' and coverage['E02-expired-duty-repaired-e']['reportedClassification'] is None


def test_gate_run_is_blocked_without_acks_and_starts_nothing(tmp_path, plan, monkeypatch):
    monkeypatch.setattr(e2(), 'verify_plan', lambda p: None)
    started = []
    monkeypatch.setattr(e1(), '_profile', lambda *args, **kwargs: started.append(args))
    out = tmp_path/'gate'
    result = gate().execute(write_plan(tmp_path, plan), None, out)
    assert result['status'] == 'BLOCKED' and result['servicesStarted'] == [] and not started
    assert not (out/'catalog').exists() and {r['status'] for r in result['rows']} == {'NOT_RUN'} and len(result['rows']) == 56
    assert json.loads((out/'manifest.json').read_text())['status'] == 'BLOCKED'


def test_gate_refuses_an_output_inside_the_repository(plan, tmp_path, doubles):
    doubles(); target = ROOT/'evaluation/runs/e-gate-test-refused'
    with pytest.raises(ValueError):
        gate().execute(write_plan(tmp_path, plan), None, target)
    assert not target.exists()


def test_gate_run_fails_on_a_proverif_mismatch(tmp_path, plan, doubles, monkeypatch):
    monkeypatch.setattr(gate(), 'verify_plan', lambda p: None)
    monkeypatch.setattr(gate(), 'run_proverif', lambda p, output: dict(matched=False, runs={}))
    doubles(); out = tmp_path/'gate'
    result = gate().execute(write_plan(tmp_path, plan), None, out)
    assert result['status'] == 'FAILED' and {r['status'] for r in result['rows']} == {'PASS'}
    evidence = json.loads((out/'gate-evidence.json').read_text())['criteria']
    assert evidence['proverif-and-negative-control']['status'] == 'FAILED' and evidence['repairs-and-mutants']['status'] == 'FAILED'


def test_gate_run_fails_when_an_input_changes_during_the_run(tmp_path, plan, doubles, monkeypatch):
    monkeypatch.setattr(gate(), 'verify_plan', lambda p: None)
    g = gate(); real = g._bracket; seen = []

    def bracket():
        value = real(); seen.append(1)
        if len(seen) > 1:
            value = copy.deepcopy(value); first = sorted(value['agent3Sources'])[0]; value['agent3Sources'][first] = '00'*32
        return value
    monkeypatch.setattr(g, '_bracket', bracket)
    doubles(); out = tmp_path/'gate'
    result = g.execute(write_plan(tmp_path, plan), None, out)
    assert result['status'] == 'FAILED' and result['sourceStable'] is False
    evidence = json.loads((out/'gate-evidence.json').read_text())['criteria']
    assert evidence['stable-hashed-input-output-tools']['status'] == 'FAILED'


def test_main_exits_2_unless_the_run_stages_pass(tmp_path, plan, monkeypatch, capsys):
    monkeypatch.setattr(e2(), 'verify_plan', lambda p: None)
    monkeypatch.setattr(sys, 'argv', ['e_gate', '--plan', str(write_plan(tmp_path, plan)), '--output', str(tmp_path/'gate')])
    assert gate().main() == 2
    printed = json.loads(capsys.readouterr().out)
    assert printed['status'] == 'BLOCKED' and 'correlated' in printed['reviewDisclosure'] and 'not gate E PASS' in printed['gateDecision']
