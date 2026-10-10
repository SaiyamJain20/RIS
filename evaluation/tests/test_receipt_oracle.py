"""Independent E03 receipt-control oracle (SL4, repaired-e supplement rows).

Expectations: frozen rows E03-receipt-binding-control-*, E03-receipt-signature-control-* and
E03-receipt-binding-positive; pinned ledger PSC._checkReceipt (933d2a7): requestDigest/gid/dataId
binding precedes destination, epoch, expiry, witness-set and quorum checks, so a re-signed
(deliberate A40 witness deviation) or an altered-but-honestly-signed receipt both give
WRONG_SUBJECT (2) with no outcome; the honest receipt records one AttestedOutcomeRecorded.
S2-0007 three-way artifact check for the TEST-ONLY deviating witness. Synthetic facts only.
"""
import copy
import importlib
import json

import pytest
from eth_abi import encode
from eth_utils import keccak

from evaluation.evm import _internal, _type
from evaluation.tests.test_access_artifacts import artifacts, sign
from evaluation.tests.test_bootstrap import inputs

ZERO = '0x'+'00'*32
DIGEST, GRANT, OUTCOME = '0x'+'d1'*32, '0x'+'d2'*32, '0x'+'0c'*32
ALICE, DATA = '0xc4ff0022e776c3471e39abf6c69ce679440c956d', '0x53ff15331656b9b303d95970634a992ed32268c5d9723c90ddc94ceeb397061e'


def oracle():
    module = importlib.import_module('evaluation.oracles.receipt')
    assert hasattr(module, 'check_receipt_row'), 'receipt oracle missing'
    return module.check_receipt_row


def altered(field, original):
    h = keccak(b'hmbc-test-deviation:'+field.encode()+b':'+bytes.fromhex(original[2:]))
    return '0x'+(h[:20] if field == 'gid' else h).hex()


def receipt_spec():
    abi = json.load(open('evaluation/fixtures/e1/abi/PSC.json'))
    abi = abi['abi'] if isinstance(abi, dict) else abi
    return next(f for f in abi if f.get('name') == 'reportAttestedOutcome')['inputs'][2]


NEVER = dict(instantiated=False, exitCode=1, message='no worker.sqlite in /tmp/p3/r (looked in <dir>/worker/ and in <dir>)\n',
             checkedAbsent=['/tmp/p3/r/worker/worker.sqlite', '/tmp/p3/r/worker.sqlite'])


def facts(artifacts, variant, field=None):
    dep = artifacts[0]; pbc = dep['chains']['pbc']; dbc = dep['chains']['dbc']
    receipt = dict(requestDigest=DIGEST, grantId=GRANT, gid=ALICE, dataId=DATA, keyEpoch='0', grantExpiresAt='1791476040',
                   witnessSetVersion='1', dbcChainId=dbc['chainId'], kssc=dbc['contracts']['KSSC'], dbcBlockNumber='351', dbcBlockHash='0x'+'ab'*32)
    honest = dict(receipt=receipt, signatures=[sign('GrantReceipt', receipt, dep, 'witness-1')[0]])
    state = dict(status='1', gid=ALICE, dataId=DATA, outcomeLogId='0', requestLogId='7')
    granted = dict(exists=True, allowed=True, requestDigest=DIGEST, dataId=DATA, gid=ALICE, keyEpoch='0', expiresAt='1791476040',
                   recipientKeyHash='0x'+'a5'*32, issuedAt='1791476012')
    before = dict(grants={GRANT: granted}, requests={DIGEST: state}, accessLogCount='1', nonces=[[ALICE, '1', True]],
                  logs=dict(pbc=[dict(name='LogRecorded', fields=dict(kind='3'))], dbc=[dict(name='GrantIssued', fields={})]),
                  worker=copy.deepcopy(NEVER))
    witness = dep['fixture']['witnessSet']['witnesses'][0]; relay = dep['fixture']['relay']['address']
    common = dict(variant=variant, field=field, before=before, request_digest=DIGEST, grant_id=GRANT, honest=honest,
                  outcome_digest=OUTCOME, relay=relay, witness=witness, pbc_chain_id=pbc['chainId'], psc=pbc['contracts']['PSC'],
                  receipt_spec=receipt_spec())
    if variant == 'receipt-binding-positive':
        spec = receipt_spec()
        details = '0x'+encode(['bytes32', 'bytes32', _type(spec), 'address'],
                              [bytes.fromhex(DIGEST[2:]), bytes.fromhex(OUTCOME[2:]), _internal(spec, receipt), relay]).hex()
        events = [dict(name='LogRecorded', fields=dict(logId='9', kind='4', subject=DIGEST,
                                                      detailsHash='0x'+keccak(bytes.fromhex(details[2:])).hex(), details=details)),
                  dict(name='AttestedOutcomeRecorded', fields=dict(requestDigest=DIGEST, grantId=GRANT, outcomeDigest=OUTCOME,
                                                                    dbcBlockNumber='351', logId='9'))]
        after = copy.deepcopy(before); after['requests'][DIGEST] = dict(state, status='2', outcomeLogId='9')
        after['logs']['pbc'] += copy.deepcopy(events)
        return dict(common, after=after, submitted=copy.deepcopy(honest), deviation=None, success=True, rejection_code=None,
                    receipt_events=events)
    changed = dict(receipt, **{field: altered(field, receipt[field])})
    if variant == 'receipt-binding-control':
        signed = dict(receipt=changed, signatures=[sign('GrantReceipt', changed, dep, 'witness-1')[0]])
        deviation = dict(schemaVersion='hmbc-test-deviating-witness/v0', testOnly=True,
                         deviation=dict(field=field, original=receipt[field], altered=changed[field]), **copy.deepcopy(signed))
        submitted = signed
    else:
        deviation = None; submitted = dict(receipt=changed, signatures=copy.deepcopy(honest['signatures']))
    return dict(common, after=copy.deepcopy(before), submitted=submitted, deviation=deviation, success=False, rejection_code='2',
                receipt_events=[])


ROWS = [('receipt-binding-control', f) for f in ('requestDigest', 'gid', 'dataId')]+[('receipt-signature-control', f) for f in ('requestDigest', 'gid', 'dataId')]+[('receipt-binding-positive', None)]


@pytest.mark.parametrize('variant,field', ROWS)
def test_receipt_rows_expected_classes(artifacts, variant, field):
    result = oracle()(**facts(artifacts, variant, field))
    assert result['ok'] is True and result['delivery'] == 'unknown'
    expected = {'receipt-binding-control': ('REPAIR_SUPPORTED', 'WRONG_SUBJECT'), 'receipt-signature-control': ('SUPPORTED', 'WRONG_SUBJECT'),
                'receipt-binding-positive': ('SUPPORTED', None)}[variant]
    assert (result['classification'], result['error']) == expected
    if variant == 'receipt-binding-control': assert result['deliberateDeviation'] == 'A40'


@pytest.mark.parametrize('field', ['requestDigest', 'gid', 'dataId'])
@pytest.mark.parametrize('mutation', ['two-fields', 'not-test-only', 'other-field', 'other-signer', 'wrong-original', 'not-submitted',
                                      'accepted', 'other-code', 'logs', 'state-changed', 'honest-forged', 'other-alteration'])
def test_binding_control_rejects_unverified_artifact_or_outcome(artifacts, field, mutation):
    f = facts(artifacts, 'receipt-binding-control', field); dep = artifacts[0]; d = f['deviation']
    if mutation == 'two-fields':
        other = 'dataId' if field != 'dataId' else 'gid'
        d['receipt'][other] = altered(other, d['receipt'][other]); d['signatures'] = [sign('GrantReceipt', d['receipt'], dep, 'witness-1')[0]]
        f['submitted'] = dict(receipt=d['receipt'], signatures=d['signatures'])
    if mutation == 'not-test-only': d['testOnly'] = False
    if mutation == 'other-field': d['deviation']['field'] = 'gid' if field != 'gid' else 'dataId'
    if mutation == 'other-signer':
        d['signatures'] = [sign('GrantReceipt', d['receipt'], dep, 'relay')[0]]; f['submitted']['signatures'] = d['signatures']
    if mutation == 'wrong-original': d['deviation']['original'] = ZERO
    if mutation == 'not-submitted': f['submitted'] = copy.deepcopy(f['honest'])
    if mutation == 'accepted': f.update(success=True, rejection_code=None)   # MUT_NO_RECEIPT_BINDING behaviour
    if mutation == 'other-code': f['rejection_code'] = '1'
    if mutation == 'logs': f['receipt_events'] = [dict(name='AttestedOutcomeRecorded', fields={})]
    if mutation == 'state-changed': f['after']['requests'][DIGEST]['status'] = '2'
    if mutation == 'honest-forged': f['honest']['signatures'] = [sign('GrantReceipt', f['honest']['receipt'], dep, 'relay')[0]]
    if mutation == 'other-alteration':
        d['receipt'][field] = ('0x'+'77'*20) if field == 'gid' else '0x'+'77'*32
        d['deviation']['altered'] = d['receipt'][field]; d['signatures'] = [sign('GrantReceipt', d['receipt'], dep, 'witness-1')[0]]
        f['submitted'] = dict(receipt=d['receipt'], signatures=d['signatures'])
    with pytest.raises(ValueError):
        oracle()(**f)


@pytest.mark.parametrize('field', ['requestDigest', 'gid', 'dataId'])
@pytest.mark.parametrize('mutation', ['resigned', 'unchanged', 'two-fields', 'accepted', 'bad-signature-code', 'state-changed', 'tool-used'])
def test_signature_control_rejects_false_observations(artifacts, field, mutation):
    f = facts(artifacts, 'receipt-signature-control', field); dep = artifacts[0]
    if mutation == 'resigned': f['submitted']['signatures'] = [sign('GrantReceipt', f['submitted']['receipt'], dep, 'witness-1')[0]]
    if mutation == 'unchanged': f['submitted']['receipt'] = copy.deepcopy(f['honest']['receipt'])
    if mutation == 'two-fields':
        other = 'dataId' if field != 'dataId' else 'gid'; f['submitted']['receipt'][other] = altered(other, f['honest']['receipt'][other])
    if mutation == 'accepted': f.update(success=True, rejection_code=None)
    if mutation == 'bad-signature-code': f['rejection_code'] = '1'   # quorum before binding would be a different check order
    if mutation == 'state-changed': f['after']['accessLogCount'] = '2'
    if mutation == 'tool-used': f['deviation'] = facts(artifacts, 'receipt-binding-control', field)['deviation']
    with pytest.raises(ValueError):
        oracle()(**f)


@pytest.mark.parametrize('mutation', ['rejected', 'altered', 'log-kind', 'log-details', 'event-block', 'status', 'dbc-changed',
                                      'worker-changed', 'already-recorded', 'unsigned'])
def test_positive_control_rejects_false_observations(artifacts, mutation):
    f = facts(artifacts, 'receipt-binding-positive'); dep = artifacts[0]
    if mutation == 'rejected': f.update(success=False, rejection_code='2', receipt_events=[], after=copy.deepcopy(f['before']))
    if mutation == 'altered':
        f['submitted']['receipt'] = dict(f['submitted']['receipt'], dataId='0x'+'99'*32)
    if mutation == 'log-kind': f['receipt_events'][0]['fields']['kind'] = '3'
    if mutation == 'log-details': f['receipt_events'][0]['fields']['details'] = '0x'
    if mutation == 'event-block': f['receipt_events'][1]['fields']['dbcBlockNumber'] = '352'
    if mutation == 'status': f['after']['requests'][DIGEST]['status'] = '1'
    if mutation == 'dbc-changed': f['after']['logs']['dbc'].append(dict(name='GrantIssued', fields={}))
    if mutation == 'worker-changed': f['after']['worker'] = dict(instantiated=True, log=dict(events=[], releases=[], counts=dict(releaseIntentCount='0', releaseSentCount='0')))
    if mutation == 'already-recorded': f['before']['requests'][DIGEST]['status'] = '2'
    if mutation == 'unsigned': f['submitted']['signatures'] = []
    with pytest.raises(ValueError):
        oracle()(**f)
