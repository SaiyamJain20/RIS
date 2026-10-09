"""A recovery-slice startup contract ACK never substitutes for plan ACKs.

No services; missing/stale config must refuse before snapshots and native calls.
"""
import copy
import importlib
import json

import pytest


def module():
    assert importlib.util.find_spec('evaluation.e2') is not None,'Executable C-E2 recovery-slice plan missing'
    return importlib.import_module('evaluation.e2')


def test_exact_plan_pins_scoped_successors_and_all_six_fresh_cases():
    m=module();p=m.create_plan(run_id='E2-recovery-test',freeze_message='A3-0035');m.verify_plan(p)
    assert p['owners']['ledger']['commit']=='933d2a75483a08e7374cd417a6cf8a9e5c13a33c'
    assert p['owners']['protocol']['commit']=='0716a8e2d46f985f35a612d42acaae02ab8701a4'
    assert len(p['matrix'])==6
    assert {r['point'] for r in p['matrix']}=={'after_intent','after_send'}
    assert p['fullCatalogComplete'] is False


@pytest.mark.parametrize('change',['point','clock','source','owner','contract','actor','ports'])
def test_changed_plan_refuses_before_services(change):
    m=module();p=m.create_plan(run_id='E2-test',freeze_message='A3-0035')
    if change=='point':p['matrix'][0]['point']='os_kill'
    if change=='clock':p['mining']='interval'
    if change=='source':p['agent3Sources']['evaluation/recovery.py']='00'*32
    if change=='owner':p['owners']['protocol']['commit']='0'*40
    if change=='contract':p['startContractSha256']='00'*32
    if change=='actor':p['deployerSignerRole']='witness-1'
    if change=='ports':p['ports']['pbc']=p['ports']['dbc']
    with pytest.raises(ValueError):m.verify_plan(p)


def test_absent_full_plan_ack_is_blocked_without_services_or_snapshots(tmp_path):
    m=module();p=m.create_plan(run_id='E2-test',freeze_message='A3-0035');path=tmp_path/'plan.json';path.write_text(json.dumps(p))
    result=m.execute(path,None,tmp_path/'output')
    assert result['status']=='BLOCKED' and result['servicesStarted']==[]
    assert not (tmp_path/'output/snapshots').exists() and result['cases']=={}


def test_startup_supplement_hash_and_message_cannot_pass_plan_ack_guard():
    m=module();p=m.create_plan(run_id='E2-test',freeze_message='A3-0035')
    from evaluation.e1 import verify_ack_message
    raw=b'Message-ID: A1-9999\nFrom: agent-1\nTo: all\nRQ: E\nType: ACK\nInterface-version: v1\nResponds-to: A3-0032\nAccepted-plan-sha256: '+p['startContractSha256'].encode()+b'\n'
    with pytest.raises(ValueError):verify_ack_message(raw,agent='agent-1',plan=p,plan_sha256='ab'*32)


def test_expiry_plan_cannot_start_without_new_exact_full_ack(tmp_path):
    m = module()
    p = m.create_plan(run_id='E2-expiry-test', freeze_message='A3-0037', expired_retry=True)
    m.verify_plan(p)
    path = tmp_path/'plan.json'; path.write_text(json.dumps(p))
    result = m.execute(path, None, tmp_path/'output')
    assert result['status'] == 'BLOCKED' and result['servicesStarted'] == [] and result['cases'] == {}
    # Even exact old-plan metadata cannot authorize the new message/source recipe.
    from evaluation.e1 import verify_ack_message
    old = b'Message-ID: A1-0048\nFrom: agent-1\nTo: agent-3\nRQ: E\nType: ACK\nInterface-version: v1\nResponds-to: A3-0035\nAccepted-plan-sha256: '+b'4bceffc347be2267348d8b781a4c30b5db00567712f1b0d14a48aae0bee5929a\n'
    with pytest.raises(ValueError): verify_ack_message(old, agent='agent-1', plan=p, plan_sha256='ab'*32)


@pytest.mark.parametrize('omit_expiry', [False, True])
def test_expiry_execution_cannot_accept_recovery_only(tmp_path, monkeypatch, omit_expiry):
    m = module()
    p = m.create_plan(run_id='E2-expiry-test', freeze_message='A3-0037', expired_retry=True)
    path = tmp_path/'plan.json'; path.write_text(json.dumps(p))
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})

    def supplied_profile(plan, profile, output, record, *, recovery_point, expired_retry):
        assert expired_retry is True
        (output/'recovery').mkdir(parents=True)
        (output/'recovery/result.json').write_text(json.dumps(dict(ok=True, delivery='unknown')))
        if not omit_expiry:
            (output/'expired-retry').mkdir()
            (output/'expired-retry/result.json').write_text(json.dumps(dict(ok=True, error='EXPIRED', delivery='unknown',
                                                                          workerUnchanged=True, nativeUnchanged=True)))

    monkeypatch.setattr(m.e1, '_profile', supplied_profile)
    result = m.execute(path, None, tmp_path/'output')
    assert result['status'] == ('FAILED' if omit_expiry else 'E2_RECOVERY_EXPIRY_SLICE_PASS')
