import copy
import json
from pathlib import Path
import pytest
from jsonschema import ValidationError
from evaluation.schema import validate

V = json.loads(Path('interfaces/vectors/eip712-agent1-candidate.json').read_text())
REQUEST = next(v['typedData']['message'] for v in V['vectors'] if v['name'] == 'AccessRequest')


def test_valid_request():
    validate('AccessRequest', REQUEST)


@pytest.mark.parametrize('field,value', [('action','256'), ('action',1), ('nonce','-1'), ('nonce','01'), ('nonce','1.0'), ('nonce',str(2**256)), ('expiresAt',str(2**64)), ('gid','0x'+'AB'*20), ('dataId','0x00'), ('unexpected','x'), ('keyEpoch','1')])
def test_reject_invalid_wire_request(field, value):
    request = copy.deepcopy(REQUEST)
    request[field] = value
    with pytest.raises((ValidationError, ValueError)):
        validate('AccessRequest', request)


def test_missing_required_field_rejects():
    request = copy.deepcopy(REQUEST)
    del request['recipientKeyHash']
    with pytest.raises(ValidationError):
        validate('AccessRequest', request)


def test_credential_record_order_rejects_duplicates_and_reversal():
    records = next(v['records'] for v in V['vectors'] if 'records' in v)
    validate('CredentialRecords', records)
    for invalid in (records[::-1], [records[0],records[0]]):
        with pytest.raises(ValueError):
            validate('CredentialRecords', invalid)


def test_signature_canonicality():
    signature = V['vectors'][0]['signature']
    validate('Signature', signature)
    for invalid in ('0x'+'00'*65, signature[:-2]+'00', '0x'+'01'*32+'ff'*32+'1b'):
        with pytest.raises((ValidationError, ValueError)):
            validate('Signature', invalid)


def test_adapter_response_exclusive_result_error():
    validate('AdapterResponse', {'schemaVersion':'v1','ok':False,'result':None,'error':{'code':'ADAPTER_UNAVAILABLE','message':'unavailable'}})
    with pytest.raises(ValidationError):
        validate('AdapterResponse', {'schemaVersion':'v1','ok':True,'result':None,'error':None})


RECEIPT = next(v['typedData']['message'] for v in V['vectors'] if v['name']=='GrantReceipt')


def test_matching_past_grant_receipt_wire_form_is_valid():
    validate('GrantReceipt',RECEIPT)
    # A past grant may be reconciled late. Wire validation has no wall-clock expiry check.
    receipt=copy.deepcopy(RECEIPT);receipt['grantExpiresAt']='1'
    validate('GrantReceipt',receipt)


@pytest.mark.parametrize('field,value',[('dbcResult','1'),('keyEpoch','1'),('witnessSetVersion','2'),('grantExpiresAt','0')])
def test_receipt_obsolete_result_and_invalid_e_constants_reject(field,value):
    receipt=copy.deepcopy(RECEIPT);receipt[field]=value
    with pytest.raises((ValidationError,ValueError)):validate('GrantReceipt',receipt)


@pytest.mark.parametrize('field',['gid','dataId','witnessSetVersion'])
def test_receipt_added_bindings_are_required(field):
    receipt=copy.deepcopy(RECEIPT);del receipt[field]
    with pytest.raises(ValidationError):validate('GrantReceipt',receipt)


def test_all_declared_positive_scenarios_validate_and_unknown_nested_field_fails():
    scenarios=json.loads(Path('evaluation/scenarios/e_positive.json').read_text())
    for scenario in scenarios: validate('Scenario',scenario)
    bad=copy.deepcopy(scenarios[0]);bad['fixture']['policy']['silentOverride']=True
    with pytest.raises(ValidationError):validate('Scenario',bad)


def test_run_manifest_schema_rejects_unknown_fields_and_accepts_preflight(tmp_path):
    from evaluation.run import run
    manifest=run('E','repaired-e',tmp_path/'run')
    validate('RunManifest',manifest)
    manifest['fabricatedPass']=True
    with pytest.raises(ValidationError):validate('RunManifest',manifest)


def test_signed_certificate_enforces_nested_role_order():
    v=next(v for v in V['vectors'] if v['name']=='RoleCertificate')
    cert=copy.deepcopy(v['typedData']['message'])
    cert['roles']=[cert['roles'][0],cert['roles'][0]]
    with pytest.raises(ValueError):validate('SignedRoleCertificate',{'cert':cert,'signature':v['signature']})


def test_e_certificate_cannot_have_more_than_one_witness_signature():
    v=next(v for v in V['vectors'] if v['name']=='AccessDecision')
    cert={'decision':v['typedData']['message'],'signatures':[v['signature'],v['signature']]}
    with pytest.raises(ValidationError):validate('DecisionCertificate',cert)


@pytest.mark.parametrize('name', ['Registration','RoleCertificate','RevocationList','TemporalAcl','AccessRequest','AccessDecision','StateCheckpoint','GrantReceipt'])
def test_schema_signing_metadata_matches_producer_vectors(name):
    from evaluation.vectors import type_string
    schema=json.loads(Path('interfaces/proposals/v1/hmbc.schema.json').read_text())['$defs'][name]
    typed=next(v['typedData'] for v in V['vectors'] if v['name']==name)
    assert schema.get('x-eip712Type')==type_string(name,typed['types'])
    assert list(schema['properties'])==[field['name'] for field in typed['types'][name]]


def test_empty_credential_bundle_is_malformed():
    # A bundle with one temporal claim is structurally valid; membership is a state check.
    validate('CredentialBundle',{'certificates':[],'temporalClaims':[{'authority':REQUEST['gid'],'role':REQUEST['dataId']}]})
    with pytest.raises(ValueError,match='MALFORMED'):
        validate('CredentialBundle',{'certificates':[],'temporalClaims':[]})


@pytest.mark.parametrize('nested',[False,True])
def test_zero_subject_in_temporal_acl_is_malformed(nested):
    acl=copy.deepcopy(next(v['typedData']['message'] for v in V['vectors'] if v['name']=='TemporalAcl'))
    entry=acl['entries'][0]
    validate('TempAclEntry',entry)
    entry['gid']='0x'+'00'*20
    # One entry avoids confounding this check with the separate canonical-order constraint.
    acl['entries']=[entry]
    with pytest.raises(ValueError,match='MALFORMED'):
        validate('TemporalAcl' if nested else 'TempAclEntry',acl if nested else entry)


@pytest.mark.parametrize('name,value',[('Address','0x'+'11'*20),('Hash','0x'+'22'*32),('FileHash','33'*32)])
def test_canonical_hex_rejects_trailing_newline(name,value):
    validate(name,value)
    with pytest.raises(ValidationError):validate(name,value+'\n')
