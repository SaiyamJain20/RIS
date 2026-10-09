import json
import pytest
from evaluation.gate import check_gate


def test_missing_or_stub_only_run_cannot_pass(tmp_path):
    assert check_gate(tmp_path)['decision']=='BLOCKED'
    (tmp_path/'manifest.json').write_text(json.dumps({'rq':'E','status':'PASS','executionMode':'provided-traces','interfaceVersion':'v1','claims':{'allPassed':True}}))
    assert check_gate(tmp_path)['decision']=='BLOCKED'


def test_boolean_claims_without_artifact_and_peer_acks_do_not_pass(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({'rq':'E','executionMode':'real-integrated','status':'PASS','sourceStable':True,'interfaceVersion':'v1','resultFiles':{},'exitCodes':[0]}))
    (tmp_path/'gate-evidence.json').write_text(json.dumps({'criteria':{'everything':True},'acks':[]}))
    assert check_gate(tmp_path)['decision']=='BLOCKED'


def test_future_phases_locked(tmp_path):
    assert check_gate(tmp_path,'F')['decision']=='BLOCKED'
    assert check_gate(tmp_path,'G')['decision']=='BLOCKED'


def test_non_object_manifest_is_blocked_instead_of_crashing(tmp_path):
    (tmp_path/'manifest.json').write_text('[]')
    assert check_gate(tmp_path)['decision']=='BLOCKED'
