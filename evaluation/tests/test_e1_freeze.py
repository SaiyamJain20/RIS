"""Freeze guards must refuse services on missing ACKs or moving inputs."""
import copy
import importlib
import json

import pytest


def module():
    assert importlib.util.find_spec('evaluation.e1') is not None, 'Executable E1 freeze/runner is missing'
    return importlib.import_module('evaluation.e1')


def test_plan_pins_existing_reviewed_sources_without_starting_services(tmp_path):
    m=module();plan=m.create_plan(run_id='E1-20261008-public-access',freeze_message='A3-0027')
    m.verify_plan(plan)
    assert plan['owners']['ledger']['commit']=='9d6911d9a35c7d20b3e0226400f8f0fcc99ef256'
    assert plan['owners']['protocol']['commit']=='465aff52688179fd983fd8da9e2af3032189ff6e'
    assert plan['profiles']==['paper-strict','paper-minimal','repaired-e']


@pytest.mark.parametrize('change',['source','lock','tool','owner','profile','port','freeze','actor'])
def test_unreviewed_execution_input_cannot_pass_freeze_guard(change):
    m=module();plan=m.create_plan(run_id='E1-test',freeze_message='A3-0027')
    if change=='source':plan['agent3Sources']['evaluation/access_execution.py']='00'*32
    if change=='lock':plan['dependencyLockSha256']='00'*32
    if change=='tool':plan['tools']['cast']['sha256']='00'*32
    if change=='owner':plan['owners']['ledger']['commit']='0'*40
    if change=='profile':plan['profiles']=['repaired-f']
    if change=='port':plan['ports']['pbc']=plan['ports']['dbc']
    if change=='freeze':plan['interfaceFreezeSha256']='00'*32
    if change=='actor':plan['deployerSignerRole']='witness-1'
    with pytest.raises(ValueError):m.verify_plan(plan)


def test_missing_exact_ack_is_blocked_before_snapshot_or_services(tmp_path):
    m=module();plan=m.create_plan(run_id='E1-test',freeze_message='A3-0027');p=tmp_path/'plan.json';p.write_text(json.dumps(plan))
    result=m.execute(p,None,tmp_path/'run')
    assert result['status']=='BLOCKED' and result['servicesStarted']==[]
    assert not (tmp_path/'run'/'snapshots').exists()


def test_owner_readiness_message_is_not_an_integration_ack():
    m=module();plan=m.create_plan(run_id='E1-test',freeze_message='A3-0027')
    raw=b'Message-ID: A1-0030\nFrom: agent-1\nTo: agent-3\nRQ: E\nType: READY\nInterface-version: v1\nResponds-to: A3-0024\n'
    with pytest.raises(ValueError):m.verify_ack_message(raw,agent='agent-1',plan=plan,plan_sha256='ab'*32)


def test_only_exact_plan_revision_and_freeze_message_can_be_acked():
    m=module();plan=m.create_plan(run_id='E1-test',freeze_message='A3-0027')
    raw=('Message-ID: A1-9999\nFrom: agent-1\nTo: all\nRQ: E\nType: ACK\nInterface-version: v1\n'
         'Responds-to: A3-0027\nAccepted-plan-sha256: '+'ab'*32+'\n').encode()
    # Synthetic parser control, never stored/used as a peer ACK.
    assert m.verify_ack_message(raw,agent='agent-1',plan=plan,plan_sha256='ab'*32)=='A1-9999'
    for old,new in [(b'ab'*32,b'cd'*32),(b'A3-0027',b'A3-0026'),(b'agent-1',b'agent-2'),(b'Type: ACK',b'Type: REVIEW')]:
        with pytest.raises(ValueError):m.verify_ack_message(raw.replace(old,new),agent='agent-1',plan=plan,plan_sha256='ab'*32)


def test_snapshot_materialization_refuses_path_escape_before_writing(tmp_path):
    m=module();plan=m.create_plan(run_id='E1-test',freeze_message='A3-0027')
    owner=copy.deepcopy(plan['owners']['ledger']);owner['entries']['../escape']='00'*32
    with pytest.raises(ValueError):m.materialize_owner(owner,tmp_path/'snapshot')
    assert not (tmp_path/'escape').exists()


def test_runtime_template_checks_all_bytes_outside_declared_immutable_slots():
    m=module();artifact=dict(object='0x60010000000060ff',immutableReferences={'7':[dict(start=2,length=4)]})
    m.check_runtime_bytecode('0x60011234567860ff',artifact)
    with pytest.raises(ValueError):m.check_runtime_bytecode('0x60021234567860ff',artifact)
    with pytest.raises(ValueError):m.check_runtime_bytecode('0x',artifact)
    artifact['immutableReferences']['7'][0]['start']=20
    with pytest.raises(ValueError):m.check_runtime_bytecode('0x60011234567860ff',artifact)


def test_interruption_records_failure_and_propagates_cancellation(tmp_path, monkeypatch):
    m=module();plan=m.create_plan(run_id='E1-test',freeze_message='A3-0027')
    p=tmp_path/'plan.json';p.write_text(json.dumps(plan))
    # Control-flow double only: no peer identities/ACK files, services or gate evidence.
    monkeypatch.setattr(m,'_acks',lambda *args: {'TEST_ONLY_CONTROL': 'not peer evidence'})
    def interrupt(*args): raise KeyboardInterrupt()
    monkeypatch.setattr(m,'_profile',interrupt)
    with pytest.raises(KeyboardInterrupt):m.execute(p,None,tmp_path/'run')
    manifest=json.loads((tmp_path/'run/manifest.json').read_text())
    assert manifest['status']=='FAILED' and manifest['endedAt']
    assert manifest['failure']['type']=='KeyboardInterrupt' and manifest['servicesStarted']==[]
