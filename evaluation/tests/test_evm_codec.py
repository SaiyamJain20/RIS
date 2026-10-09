"""Independent ABI controls: literal words, pinned owner ABI and Cast encoding.

No receipt came from a running chain. Synthetic decoding is sensitivity evidence.
"""
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT/'evaluation/fixtures/e1'
ADDRESS = '0x'+'33'*20
SUBJECT = '0x'+'11'*20
GRANT = '0x'+'aa'*32
REQUEST = '0x'+'bb'*32
DATA = '0x'+'44'*32
RECIPIENT = '0x'+'55'*32
TOPIC = '0x05227b04f749c38d58a5b2fb3e53db12197f13fad4723d789bb040abe60dab58'


def codec(role='KSSC', path=None):
    try: module = importlib.import_module('evaluation.evm')
    except ModuleNotFoundError: pytest.fail('C-E1 public ABI codec is not implemented')
    pins = json.loads((FIXTURES/'abi/PROVENANCE.json').read_text())['files']
    return module.AbiContract(path or FIXTURES/'abi'/f'{role}.json', ADDRESS, pins[role]['sha256'])


def word(value): return f'{value:064x}'


def native_grant():
    return {'address':ADDRESS, 'removed':False, 'topics':[TOPIC, GRANT, REQUEST, '0x'+'00'*12+SUBJECT[2:]],
            'data':'0x'+DATA[2:]+word(0)+word(2000000000)+RECIPIENT[2:]+word(1)+word(7)}


def test_selector_and_address_encoding_match_literal_cast_control():
    assert codec('RSC').calldata('recipientKeyHash', SUBJECT) == '0x3fefd37d'+'00'*12+SUBJECT[2:]


def test_nested_request_encoding_matches_independent_pinned_cast():
    v=json.loads((FIXTURES/'cast-request-calldata.json').read_text())
    assert codec('PSC').calldata('requestAccess', v['request'], v['userSignature'], v['bundle']) == v['expectedCalldata']


def test_altered_owner_abi_is_refused_before_use(tmp_path):
    p=tmp_path/'KSSC.json';p.write_bytes((FIXTURES/'abi/KSSC.json').read_bytes()+b' ')
    with pytest.raises(ValueError, match='ABI hash'):codec(path=p)


def test_literal_event_words_decode_to_named_wire_values():
    decoded = codec().decode_log(native_grant())
    assert decoded == {'name':'GrantIssued','fields':{'grantId':GRANT,'requestDigest':REQUEST,'gid':SUBJECT,
                       'dataId':DATA,'keyEpoch':'0','expiresAt':'2000000000','recipientKeyHash':RECIPIENT,
                       'nonceConsumed':True,'nonce':'7'}}


@pytest.mark.parametrize('change', ['emitter','removed','topics','boolean','extra-data','truncated-data'])
def test_corrupt_native_grant_is_refused(change):
    v=native_grant()
    if change=='emitter':v['address']='0x'+'99'*20
    if change=='removed':v['removed']=True
    if change=='topics':v['topics'].append('0x'+'00'*32)
    if change=='boolean':v['data']='0x'+DATA[2:]+word(0)+word(2000000000)+RECIPIENT[2:]+word(2)+word(7)
    if change=='extra-data':v['data']+=word(0)
    if change=='truncated-data':v['data']=v['data'][:-64]
    with pytest.raises(ValueError):codec().decode_log(v)


def test_unknown_native_topic_is_not_a_fabricated_grant():
    v=native_grant();v['topics'][0]='0x'+'ee'*32
    assert codec().decode_log(v) is None


def test_view_return_has_exact_tuple_fields_and_widths():
    raw='0x'+REQUEST[2:]+DATA[2:]+'00'*12+SUBJECT[2:]+word(0)+word(2000000000)+word(1)
    assert codec().decode_return('getGrant', raw)==[REQUEST,DATA,SUBJECT,'0','2000000000',True]
    with pytest.raises(ValueError):codec().decode_return('getGrant',raw+word(0))


def test_unknown_method_and_wrong_argument_count_do_not_fallback():
    c=codec()
    with pytest.raises(ValueError):c.calldata('madeUpMethod',REQUEST)
    with pytest.raises(ValueError):c.calldata('getGrant')


def test_extra_tuple_field_and_noncanonical_decimal_refuse_encoding():
    v=json.loads((FIXTURES/'cast-request-calldata.json').read_text());c=codec('PSC')
    req={**v['request'],'extra':'1'}
    with pytest.raises(ValueError):c.calldata('requestAccess',req,v['userSignature'],v['bundle'])
    req={**v['request'],'nonce':'07'}
    with pytest.raises(ValueError):c.calldata('requestAccess',req,v['userSignature'],v['bundle'])
