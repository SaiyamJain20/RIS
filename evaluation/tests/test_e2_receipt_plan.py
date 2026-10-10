"""SL4 receipt-control plan: seven exact repaired-e rows, solo-only, fail-closed per row.

The TEST-ONLY deviating witness (S2-0007, accepted A1-0064) is pinned by exact module, path,
sha256 and invocation; its argv is built only from that template. No services: the profile
executor is a control-flow double writing supplied proof files.
"""
import hashlib
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOLO = 'solo-correlated'
TOOL_SHA256 = '0511ba571b71d960d8ffbe4b8c811da99ed7de53a4b7515ac425c5291cc3c2d7'
FIELDS = ('requestDigest', 'gid', 'dataId')
ROWS = [('receipt-binding-control', f) for f in FIELDS]+[('receipt-signature-control', f) for f in FIELDS]+[('receipt-binding-positive', None)]
EXPECTED = {'receipt-binding-control': ('REPAIR_SUPPORTED', 'WRONG_SUBJECT'), 'receipt-signature-control': ('SUPPORTED', 'WRONG_SUBJECT'),
            'receipt-binding-positive': ('SUPPORTED', None)}
TEMPLATE = ['{python}', '-m', 'testtools.deviating_witness', '--deployment', '{deployment}', 'receipt', '--grant-id', '{grantId}',
            '--field', '{field}', '--at-block', '{atBlock}']


def module():
    return importlib.import_module('evaluation.e2')


def plan():
    return module().create_plan(run_id='E2-receipt-test', freeze_message='S3-0013', receipt_stress=True, review_mode=SOLO)


def case_id(variant, field):
    return 'E03-'+variant+('-'+field if field else '')+'-repaired-e'


def test_receipt_plan_pins_seven_frozen_rows_and_solo_configuration():
    p = plan(); module().verify_plan(p)
    assert [(r['profile'], r['variant'], r['field']) for r in p['matrix']] == [('repaired-e', v, f) for v, f in ROWS]
    assert p['caseIds'] == [case_id(v, f) for v, f in ROWS]
    assert p['receiptStress'] is True and p['fullCatalogComplete'] is False and 'workerExpected' not in p
    assert p['reviewMode'] == SOLO and p['ports'] == dict(pbc=18545, dbc=18546) and p['castHashPolicy'] == 'checkpoint'
    catalog = {c['id']: c for c in json.loads((ROOT/'evaluation/scenarios/e0_supplement_cases.json').read_text())['cases']}
    for (variant, field), cid in zip(ROWS, p['caseIds']):
        c = catalog[cid]
        assert c['variant'] == variant and c['profile'] == 'repaired-e'
        assert (c['expected']['classification'], c['expected']['error']) == EXPECTED[variant]
        assert [s.get('receiptField') for s in c['steps'] if 'receiptField' in s] == ([field] if field else [])


def test_receipt_probe_pins_the_exact_test_only_tool_and_conditions():
    p = plan(); probe = p['receiptProbe']; tool = probe['deviatingWitness']
    assert tool['module'] == 'testtools.deviating_witness' and tool['path'] == 'protocol/testtools/deviating_witness.py'
    assert tool['sha256'] == TOOL_SHA256 == p['owners']['protocol']['entries'][tool['path']]
    assert tool['invocation'] == TEMPLATE and '--value' not in tool['invocation']
    assert tool['cwd'] == 'materialized protocol snapshot (protocol/)'
    text = ' '.join(tool['conditions'])
    for needle in ('S2-0007', 'A1-0064', 'non-zero exit', 'failed trial', 'same deployment file', 'only the named field',
                   'HMBCReceipt', 'testOnly', 'A40', 'never publish', 'sha256 and first line'):
        assert needle in text, needle
    worker = probe['workerPrecondition']
    for needle in ('adapter.py:133-136', 'release', 'encrypt_record', 'finish_decryption', 'attest_grant', 'every catalog step', 'D49'):
        assert needle in worker, needle


def test_deviation_argv_is_built_only_from_the_pinned_template():
    e1 = module().e1; tool = plan()['receiptProbe']['deviatingWitness']
    argv = e1.deviation_argv(tool, python='/py', deployment=Path('/d/deployment.json'), grant_id='0x'+'ab'*32, field='gid', at_block='351')
    assert argv == ['/py', '-m', 'testtools.deviating_witness', '--deployment', '/d/deployment.json', 'receipt', '--grant-id', '0x'+'ab'*32,
                    '--field', 'gid', '--at-block', '351']


@pytest.mark.parametrize('change', ['field', 'grant', 'block', 'template', 'module', 'value'])
def test_deviation_argv_refuses_anything_else(change):
    e1 = module().e1; tool = plan()['receiptProbe']['deviatingWitness']
    kwargs = dict(python='/py', deployment=Path('/d/deployment.json'), grant_id='0x'+'ab'*32, field='gid', at_block='351')
    if change == 'field': kwargs['field'] = 'grantId'
    if change == 'grant': kwargs['grant_id'] = '0x'+'AB'*32
    if change == 'block': kwargs['at_block'] = 'latest'
    if change == 'template': tool = dict(tool, invocation=tool['invocation'][:-2])
    if change == 'module': tool = dict(tool, module='testtools.faulty_adapter')
    if change == 'value': tool = dict(tool, invocation=tool['invocation']+['--value', '{field}'])
    with pytest.raises(ValueError):
        e1.deviation_argv(tool, **kwargs)


@pytest.mark.parametrize('options', [dict(review_mode='strict', freeze_message='A3-0050'), dict(audit_stress=True),
                                     dict(relay_stress=True), dict(subject_substitution=True), dict(duplicate_outcome=True)])
def test_receipt_plan_refuses_strict_mode_and_combined_probes(options):
    kwargs = dict(run_id='E2-receipt-test', freeze_message='S3-0013', receipt_stress=True, review_mode=SOLO); kwargs.update(options)
    with pytest.raises(ValueError):
        module().create_plan(**kwargs)


@pytest.mark.parametrize('change', ['row', 'field', 'tool-sha', 'invocation', 'classification'])
def test_changed_receipt_plan_refuses(change):
    p = plan()
    if change == 'row': p['matrix'][0]['variant'] = 'fabricated-outcome'
    if change == 'field': p['matrix'][0]['field'] = 'grantId'
    if change == 'tool-sha': p['receiptProbe']['deviatingWitness']['sha256'] = hashlib.sha256(b'other').hexdigest()
    if change == 'invocation': p['receiptProbe']['deviatingWitness']['invocation'].append('--value')
    if change == 'classification': p['classification'] = 'HMBC vulnerability'
    with pytest.raises(ValueError):
        module().verify_plan(p)


def supplied(mode):
    def profile(plan, profile, output, record, *, recovery_point, expired_retry, receipt_stress, receipt_field):
        assert recovery_point is None and expired_retry is False and profile == 'repaired-e'
        if mode == 'missing': return
        classification, error = EXPECTED[receipt_stress]
        proof = dict(ok=True, delivery='unknown', classification=classification, error=error, variant=receipt_stress, field=receipt_field)
        if mode == 'wrong-class': proof['classification'] = 'REPAIR_SUPPORTED' if classification == 'SUPPORTED' else 'SUPPORTED'
        if mode == 'other-variant': proof['variant'] = 'fabricated-outcome'
        if mode == 'other-field': proof['field'] = 'dataId' if receipt_field != 'dataId' else 'gid'
        (output/'receipt-stress').mkdir(parents=True); (output/'receipt-stress/result.json').write_text(json.dumps(proof))
    return profile


@pytest.mark.parametrize('mode', ['missing', 'wrong-class', 'other-variant', 'other-field', 'complete'])
def test_receipt_execution_requires_each_complete_row_proof(tmp_path, monkeypatch, mode):
    m = module(); path = tmp_path/'plan.json'; path.write_text(json.dumps(plan()))
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    monkeypatch.setattr(m.e1, '_profile', supplied(mode))
    result = m.execute(path, None, tmp_path/'out')
    assert result['status'] == ('E2_RECEIPT_STRESS_SLICE_PASS' if mode == 'complete' else 'FAILED')
    if mode == 'complete':
        assert len(result['cases']) == 7 and {c['status'] for c in result['cases'].values()} == {'RECEIPT_STRESS_CONTROL_PASS'}
        assert sorted(result['cases']) == sorted('repaired-e-'+v+('-'+f if f else '') for v, f in ROWS)
