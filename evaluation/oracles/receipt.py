"""Independent E03 receipt-control oracle (SL4) for the paper-derived HMBC reconstruction.

Expectations: frozen supplement rows E03-receipt-binding-control-{requestDigest,gid,dataId}-repaired-e,
E03-receipt-signature-control-{...}-repaired-e and E03-receipt-binding-positive-repaired-e, SPEC4/E03,
and the pinned ledger (933d2a7) PSC.reportAttestedOutcome/_checkReceipt: the requestDigest/gid/dataId
binding (WRONG_SUBJECT, 2) is checked before destination, epoch, expiry, witness-set and quorum, so
both a receipt re-signed by the TEST-ONLY deviating witness (deliberate A40 deviation, outside the
honest-witness assumption) and an altered receipt that keeps the honest signature are rejected with
no outcome. The honest receipt records exactly one AttestedOutcomeRecorded with an LSC OUTCOME(4) log
whose details are abi.encode(digest, outcomeDigest, receipt, relay). S2-0007 (accepted A1-0064)
three-way artifact check. Tested reconstruction results, never HMBC exploits.
"""
import copy

from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from evaluation.access_artifacts import require
from evaluation.bootstrap import _frozen, frozen_validate
from evaluation.evm import _hex, _internal, _type
from evaluation.oracles.provenance import _idle

BOUND = ('requestDigest', 'gid', 'dataId')
VARIANTS = {'receipt-binding-control': BOUND, 'receipt-signature-control': BOUND, 'receipt-binding-positive': (None,)}
STEP = {'receipt-binding-control': 'RESIGN_RECEIPT_FIELD', 'receipt-signature-control': 'ALTER_RECEIPT_KEEP_SIGNATURE',
        'receipt-binding-positive': None}
ARTIFACT_SCHEMA = 'hmbc-test-deviating-witness/v0'
A40_LABEL = ('A40 deliberate witness deviation: TEST-ONLY tool output, not an honest-witness receipt and not an HMBC result '
             '(defence-in-depth control outside the honest-witness assumption)')
_NATIVE = ('grants', 'requests', 'accessLogCount', 'nonces', 'logs')


def _native(snapshot):
    return {k: copy.deepcopy(snapshot[k]) for k in _NATIVE}


def deviation_value(field, original):
    """S2-0007 default alteration (no --value): keccak("hmbc-test-deviation:"||field||":"||original); gid keeps 20 bytes."""
    require(field in BOUND, 'receipt-bound field')
    digest = keccak(b'hmbc-test-deviation:'+field.encode()+b':'+_hex(original))
    return '0x'+(digest[:20] if field == 'gid' else digest).hex()


def receipt_signer(receipt, signature, *, pbc_chain_id, psc):
    """Recover a GrantReceipt signer under the evaluator's own EIP-712 encoder (frozen template, HMBCReceipt v1, PBC PSC)."""
    frozen_validate('GrantReceipt', receipt); frozen_validate('Signature', signature)
    template = next(v['typedData'] for v in _frozen('vectors/eip712-agent1.json')['vectors'] if v['name'] == 'GrantReceipt')
    typed = copy.deepcopy(template)
    require(typed['domain']['name'] == 'HMBCReceipt' and typed['domain']['version'] == '1', 'frozen GrantReceipt domain')
    typed['domain'].update(chainId=pbc_chain_id, verifyingContract=psc); typed['message'] = copy.deepcopy(receipt)
    try:
        return Account.recover_message(encode_typed_data(full_message=typed), signature=signature).lower()
    except Exception as error:
        raise ValueError('Public receipt signature recovery failed') from error


def _differs(left, right):
    require(isinstance(left, dict) and isinstance(right, dict) and set(left) == set(right), 'receipt field set')
    return {k for k in left if left[k] != right[k]}


def check_deviation_artifact(artifact, *, honest_receipt, field, witness, pbc_chain_id, psc):
    """S2-0007 three-way check of one TEST-ONLY deviating-witness output; the collector runs it before use."""
    require(isinstance(artifact, dict) and set(artifact) == {'schemaVersion', 'testOnly', 'deviation', 'receipt', 'signatures'},
            'deviating witness artifact fields')
    # (3) TEST-ONLY artifact naming exactly this row's field.
    require(artifact['schemaVersion'] == ARTIFACT_SCHEMA and artifact['testOnly'] is True, 'TEST-ONLY deviating witness artifact')
    deviation = artifact['deviation']
    require(field in BOUND and isinstance(deviation, dict) and set(deviation) == {'field', 'original', 'altered'}
            and deviation['field'] == field, 'deviation names the row field')
    # (1) Only the named field differs from the honest receipt at the same DBC block.
    receipt = artifact['receipt']
    require(_differs(honest_receipt, receipt) == {field}, 'only the named field differs from the honest receipt')
    require(deviation['original'] == honest_receipt[field] and deviation['altered'] == receipt[field]
            == deviation_value(field, deviation['original']), 'default deterministic alteration (no --value)')
    # (2) The signature recovers to the configured witness under the evaluator's own encoder.
    signatures = artifact['signatures']
    require(isinstance(signatures, list) and len(signatures) == 1
            and receipt_signer(receipt, signatures[0], pbc_chain_id=pbc_chain_id, psc=psc) == witness,
            'deviating signature recovers to the configured witness (own HMBCReceipt encoder)')
    return copy.deepcopy(artifact)


def check_receipt_row(*, variant, field, before, after, request_digest, grant_id, honest, submitted, deviation, success,
                      rejection_code, receipt_events, outcome_digest, relay, witness, pbc_chain_id, psc, receipt_spec):
    """Classify one SL4 receipt row from authenticated snapshots and the mined report."""
    require(variant in VARIANTS and field in VARIANTS[variant], 'frozen SL4 receipt row')
    _idle(before['worker'])
    require(before['worker'].get('instantiated') is False and after['worker'] == before['worker'],
            'verified never-instantiated worker, unchanged (no SL4 step is a worker operation)')
    grant, state = before['grants'][grant_id], before['requests'][request_digest]
    require(grant['exists'] is True and grant['allowed'] is True and grant['requestDigest'] == request_digest
            and grant['gid'] == state['gid'] and grant['dataId'] == state['dataId'], 'allowed DBC grant for the forwarded request')
    require(state['status'] == '1' and state['outcomeLogId'] == '0', 'forwarded request without an outcome before the report')
    require(isinstance(honest, dict) and set(honest) == {'receipt', 'signatures'} and isinstance(honest['signatures'], list)
            and len(honest['signatures']) == 1, 'honest attest_grant receipt')
    h = honest['receipt']
    require(receipt_signer(h, honest['signatures'][0], pbc_chain_id=pbc_chain_id, psc=psc) == witness,
            'honest receipt signed by the configured witness (own HMBCReceipt encoder)')
    require(h['requestDigest'] == request_digest and h['grantId'] == grant_id and h['gid'] == grant['gid']
            and h['dataId'] == grant['dataId'] and h['keyEpoch'] == grant['keyEpoch'] == '0'
            and h['grantExpiresAt'] == grant['expiresAt'] and h['witnessSetVersion'] == '1', 'honest receipt joins the native grant')
    require(isinstance(submitted, dict) and set(submitted) == {'receipt', 'signatures'}, 'submitted receipt')
    if variant == 'receipt-binding-positive':
        require(deviation is None and submitted == honest, 'honest receipt and signature submitted unchanged')
        require(success is True and rejection_code is None, 'honest receipt accepted')
        require([e['name'] for e in receipt_events] == ['LogRecorded', 'AttestedOutcomeRecorded'], 'outcome log then attested outcome event')
        log, event = receipt_events[0]['fields'], receipt_events[1]['fields']
        details = '0x'+encode(['bytes32', 'bytes32', _type(receipt_spec), 'address'],
                              [_hex(request_digest, 32), _hex(outcome_digest, 32), _internal(receipt_spec, h), relay]).hex()
        require(log['kind'] == '4' and log['subject'] == request_digest and log['details'] == details
                and log['detailsHash'] == '0x'+keccak(_hex(details)).hex(), 'LSC OUTCOME log with complete receipt details')
        require(event == dict(requestDigest=request_digest, grantId=grant_id, outcomeDigest=outcome_digest,
                              dbcBlockNumber=h['dbcBlockNumber'], logId=log['logId']),
                'attested outcome event binds request, grant, outcome, receipt block and log')
        expected = _native(before)
        expected['requests'][request_digest] = dict(state, status='2', outcomeLogId=log['logId'])
        expected['logs']['pbc'] = expected['logs']['pbc']+copy.deepcopy(receipt_events)
        require(_native(after) == expected, 'only the PBC outcome delta; DBC grant/count/nonces/history unchanged')
        return dict(ok=True, classification='SUPPORTED', error=None, outcome='ACCEPT', delivery='unknown', deliberateDeviation=None,
                    qualification='honest attest_grant receipt records exactly one matching outcome; prevents deny-all from passing; '
                                  'attests DBC authorization only, not release or delivery; tested reconstruction result')
    binding = variant == 'receipt-binding-control'
    if binding:
        require(deviation is not None, 'TEST-ONLY deviating witness artifact present')
        artifact = check_deviation_artifact(deviation, honest_receipt=h, field=field, witness=witness, pbc_chain_id=pbc_chain_id, psc=psc)
        require(submitted == dict(receipt=artifact['receipt'], signatures=artifact['signatures']), 'submitted the verified deviating artifact')
    else:
        require(deviation is None, 'signature control uses no deviating witness')
        altered = submitted['receipt']
        require(_differs(h, altered) == {field} and altered[field] == deviation_value(field, h[field]),
                'only the named field altered (same deterministic value)')
        require(submitted['signatures'] == honest['signatures'], 'original honest signature kept')
        require(receipt_signer(altered, submitted['signatures'][0], pbc_chain_id=pbc_chain_id, psc=psc) != witness,
                'kept honest signature does not authenticate the altered receipt')
    require(success is False and rejection_code == '2' and receipt_events == [], 'mined Rejected(WRONG_SUBJECT) without events')
    require(_native(after) == _native(before), 'no outcome, log or status transition; whole native state unchanged')
    if binding:
        return dict(ok=True, classification='REPAIR_SUPPORTED', error='WRONG_SUBJECT', outcome='NO_NEW_OUTCOME', delivery='unknown',
                    deliberateDeviation='A40', qualification='receipt binding rejects a validly witness-signed inconsistent receipt '
                    '(TEST-ONLY A40 deliberate deviation, outside the honest-witness assumption); defence in depth, not an HMBC attack')
    return dict(ok=True, classification='SUPPORTED', error='WRONG_SUBJECT', outcome='NO_NEW_OUTCOME', delivery='unknown',
                deliberateDeviation=None, qualification='altered receipt with the honest signature kept is rejected by the binding '
                'check, which precedes quorum; this control cannot kill MUT_NO_RECEIPT_BINDING (that mutant reaches BAD_SIGNATURE)')
