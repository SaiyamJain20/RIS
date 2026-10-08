import json
import pytest
from evaluation.run import run


def test_missing_protocol_stops_with_manifest_and_no_fake_success(tmp_path):
    output=tmp_path/'run'
    result=run('E','repaired-e',output)
    assert result['status']=='BLOCKED'
    manifest=json.loads((output/'manifest.json').read_text())
    assert manifest['adapterMode']=='symbolic'
    assert manifest['interfaceVersion']!='v1'
    assert manifest['sourceManifest']
    assert manifest['exitCodes']==[2]
    assert not manifest['resultFiles']


def test_existing_output_is_never_overwritten(tmp_path):
    (tmp_path/'manifest.json').write_text('keep')
    with pytest.raises(FileExistsError):run('E','paper-strict',tmp_path)
    assert (tmp_path/'manifest.json').read_text()=='keep'


def test_unimplemented_phase_rejects_explicitly(tmp_path):
    with pytest.raises(ValueError,match='NOT_IMPLEMENTED_IN_PHASE'):run('F','repaired-e',tmp_path/'f')


def test_explicit_integration_plan_requires_both_exact_acks(tmp_path):
    from evaluation.e1 import create_plan
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(create_plan(run_id='E1-test',freeze_message='A3-0027')))
    result=run('E','paper-strict',tmp_path/'run',integration_plan=plan)
    assert result['status']=='BLOCKED' and result['executionMode']=='two-chain-e1'
    assert not result['servicesStarted']
