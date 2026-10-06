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
