"""Independent E03 audit-correspondence oracles (SL3): dropped and fabricated outcomes.

Expectations: frozen rows E03-dropped-outcome and E03-fabricated-outcome, SPEC4/E03 and the
pinned ledger (933d2a7): PSC.reportOutcome (paper) checks only request status and the derived
grant id, never DBC state, and writes an LSC OUTCOME(4) log with abi.encode(digest, grantId,
outcomeDigest, relay); repaired-e disables it (WRONG_PROFILE 21) and the honest witness refuses
to attest a non-existent grant (NOT_COMMITTED). Synthetic facts only.
"""
import copy
import importlib

import pytest
from eth_abi import encode
from eth_utils import keccak

ZERO = '0x'+'00'*32
ALICE, RELAY = '0xc4ff0022e776c3471e39abf6c69ce679440c956d', '0x'+'7e'*20
DATA, DIGEST, GRANT = '0x'+'da'*32, '0x'+'d1'*32, '0x'+'d2'*32
KEY_ALICE, CIPHER, OUTCOME = '0x'+'a5'*32, '0x'+'c1'*32, '0x'+'0c'*32
TOKEN_DIGEST = '0x290decd9548b62a8d60345a988386fc84ba6bc95484008f6362f93160ef3e563'  # keccak of 32 zero bytes
FP = 'ab'*32
TS = 1000


def oracle(name):
    module = importlib.import_module('evaluation.oracles.audit')
    assert hasattr(module, name), name+' oracle missing'
    return getattr(module, name)


NEVER = dict(instantiated=False, exitCode=1, message='no worker.sqlite in /tmp/p3/s (looked in <dir>/worker/ and in <dir>)\n',
             checkedAbsent=['/tmp/p3/s/worker/worker.sqlite', '/tmp/p3/s/worker.sqlite'])


def log(events=(), releases=()):
    n = str(len(releases))
    return dict(instantiated=True, log=dict(schemaVersion='hmbc-worker-log/v0', adapterMode='symbolic', deploymentFingerprint=FP,
                                            note='synthetic', events=list(events), releases=list(releases),
                                            counts=dict(releaseIntentCount=n, releaseSentCount=n)))


def request_state(status='1', outcome='0'):
    return dict(status=status, gid=ALICE, dataId=DATA, destinationChainId='28545', kssc='0x'+'5c'*20, credentialDigest='0x'+'cd'*32,
                decidedAt=str(TS-5), expiresAt=str(TS+25), requestLogId='7', outcomeLogId=outcome)


def grant(repaired):
    return dict(exists=True, allowed=True, requestDigest=DIGEST, dataId=DATA, gid=ALICE, keyEpoch='0',
                expiresAt=str(TS+25 if repaired else TS+28), recipientKeyHash=KEY_ALICE if repaired else ZERO, issuedAt=str(TS-2))


EMPTY = dict(exists=False, allowed=False, requestDigest=ZERO, dataId=ZERO, gid='0x'+'00'*20, keyEpoch='0', expiresAt='0',
             recipientKeyHash=ZERO, issuedAt='0')


def snap(grant_row, req, count, worker, *, pbc=(), dbc=(), nonce=False):
    return dict(grants={GRANT: copy.deepcopy(grant_row)}, requests={DIGEST: copy.deepcopy(req)}, accessLogCount=str(count),
                nonces=[[ALICE, '1', nonce]], logs=dict(pbc=[dict(name='LogRecorded', fields=dict(kind='3'))]+list(pbc), dbc=list(dbc)),
                worker=copy.deepcopy(worker))


# ------------------------------------------------------------------- dropped

def dropped_facts(profile):
    repaired = profile == 'repaired-e'
    g = grant(repaired); granted = [dict(name='GrantIssued', fields={}), dict(name='AccessLog', fields={})]
    before = snap(g, request_state(), 1, log(), dbc=granted, nonce=repaired)
    identity = dict(requestDigest=DIGEST, grantId=GRANT, gid=ALICE, dataId=DATA)
    row = dict(**identity, ciphertextDigest=CIPHER, recipientKeyHash=KEY_ALICE, keyEpoch='0', tokenDigest=TOKEN_DIGEST,
               grantExpiresAt=g['expiresAt'], createdAt=str(TS), delivery='unknown', sendAttempts=1, completedAttempts=1)
    events = [dict(type=t, timestamp=str(TS), **identity) for t in ('RELEASE_INTENT', 'RELEASE_SENT')]
    after = copy.deepcopy(before); after['worker'] = log(events, [row])
    response = dict(schemaVersion='v1', adapterMode='symbolic', requestDigest=DIGEST, grantId=GRANT, dataId=DATA,
                    ciphertextDigest=CIPHER, recipientKeyHash=KEY_ALICE, keyEpoch='0',
                    responseEnvelope=dict(kind='symbolic-partial/v1', token=ZERO))
    return dict(profile=profile, before=before, after=after, request_digest=DIGEST, grant_id=GRANT, gid=ALICE, data_id=DATA,
                expected_recipient=KEY_ALICE, ciphertext_digest=CIPHER, response=response, dbc_now=str(TS+1), fingerprint=FP)


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_dropped_outcome_stays_pending_after_one_release(profile):
    result = oracle('check_dropped_outcome')(**dropped_facts(profile))
    assert result['ok'] is True and result['outcome'] == 'PENDING' and result['delivery'] == 'unknown'
    assert result['classification'] == ('REPAIR_SUPPORTED' if profile == 'repaired-e' else 'SUPPORTED')


@pytest.mark.parametrize('profile', ['paper-strict', 'repaired-e'])
@pytest.mark.parametrize('mutation', ['outcome-recorded', 'outcome-event', 'no-release', 'double-send', 'wrong-recipient',
                                      'native-recipient', 'response-grant', 'response-cipher', 'token', 'expired-release',
                                      'grant-changed', 'no-grant', 'prior-worker-release', 'delivery-claimed', 'never-instantiated'])
def test_dropped_outcome_rejects_false_observations(profile, mutation):
    f = dropped_facts(profile); after = f['after']['worker']['log']
    if mutation == 'outcome-recorded': f['after']['requests'][DIGEST] = request_state('2', '9')
    if mutation == 'outcome-event': f['after']['logs']['pbc'].append(dict(name='OutcomeRecorded', fields={}))
    if mutation == 'no-release': f['after']['worker'] = copy.deepcopy(f['before']['worker'])
    if mutation == 'double-send':
        after['events'].append(dict(after['events'][-1])); after['releases'][0]['sendAttempts'] = 2; after['counts']['releaseSentCount'] = '2'
    if mutation == 'wrong-recipient': f['expected_recipient'] = '0x'+'b0'*32
    if mutation == 'native-recipient':
        f['before']['grants'][GRANT]['recipientKeyHash'] = '0x'+'b0'*32 if profile == 'paper-strict' else ZERO
        f['after']['grants'][GRANT] = copy.deepcopy(f['before']['grants'][GRANT])
    if mutation == 'response-grant': f['response']['grantId'] = '0x'+'99'*32
    if mutation == 'response-cipher': f['response']['ciphertextDigest'] = '0x'+'98'*32
    if mutation == 'token': f['response']['responseEnvelope']['token'] = '0x'+'11'*32
    if mutation == 'expired-release': f['dbc_now'] = f['before']['grants'][GRANT]['expiresAt']
    if mutation == 'grant-changed': f['after']['grants'][GRANT]['expiresAt'] = str(TS+99)
    if mutation == 'no-grant':
        f['before']['grants'][GRANT] = EMPTY; f['after']['grants'][GRANT] = EMPTY
    if mutation == 'prior-worker-release': f['before']['worker'] = copy.deepcopy(f['after']['worker'])
    if mutation == 'delivery-claimed': after['releases'][0]['delivery'] = 'delivered'
    if mutation == 'never-instantiated': f['after']['worker'] = copy.deepcopy(NEVER)
    with pytest.raises(ValueError):
        oracle('check_dropped_outcome')(**f)


# ---------------------------------------------------------------- fabricated

def details():
    return '0x'+encode(['bytes32', 'bytes32', 'bytes32', 'address'], [bytes.fromhex(DIGEST[2:]), bytes.fromhex(GRANT[2:]),
                                                                        bytes.fromhex(OUTCOME[2:]), RELAY]).hex()


def fabricated_facts(profile):
    repaired = profile == 'repaired-e'
    before = snap(EMPTY, request_state(), 0, NEVER)
    if repaired:
        return dict(profile=profile, before=before, after=copy.deepcopy(before), request_digest=DIGEST, grant_id=GRANT,
                    outcome_digest=OUTCOME, relay=RELAY, success=False, rejection_code='21', receipt_events=[],
                    attestation=dict(ok=False, error='NOT_COMMITTED'))
    d = details()
    events = [dict(name='LogRecorded', fields=dict(logId='9', kind='4', subject=DIGEST, detailsHash='0x'+keccak(bytes.fromhex(d[2:])).hex(), details=d)),
              dict(name='OutcomeRecorded', fields=dict(requestDigest=DIGEST, grantId=GRANT, outcomeDigest=OUTCOME, logId='9'))]
    after = copy.deepcopy(before); after['requests'][DIGEST] = request_state('2', '9'); after['logs']['pbc'] += copy.deepcopy(events)
    return dict(profile=profile, before=before, after=after, request_digest=DIGEST, grant_id=GRANT, outcome_digest=OUTCOME, relay=RELAY,
                success=True, rejection_code=None, receipt_events=events, attestation=None)


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_fabricated_outcome_expected_classes(profile):
    result = oracle('check_fabricated_outcome')(**fabricated_facts(profile))
    assert result['ok'] is True
    if profile == 'repaired-e':
        assert result['classification'] == 'REPAIR_SUPPORTED' and result['error'] == 'WRONG_PROFILE'
    else:
        assert result['classification'] == 'SPEC_GAP' and result['outcomeWithoutGrant'] is True


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal'])
@pytest.mark.parametrize('mutation', ['grant-exists', 'consumed', 'deny', 'status', 'log-kind', 'log-details', 'log-hash',
                                      'event-grant', 'event-order', 'dbc-changed', 'worker-changed', 'already-recorded'])
def test_paper_fabricated_outcome_rejects_false_observations(profile, mutation):
    f = fabricated_facts(profile)
    if mutation == 'grant-exists':
        f['before']['grants'][GRANT] = grant(False); f['after']['grants'][GRANT] = grant(False)
    if mutation == 'consumed':
        for k in ('before', 'after'): f[k]['accessLogCount'] = '1'
    if mutation == 'deny': f.update(success=False, rejection_code='8', receipt_events=[], after=copy.deepcopy(f['before']))
    if mutation == 'status': f['after']['requests'][DIGEST]['status'] = '1'
    if mutation == 'log-kind': f['receipt_events'][0]['fields']['kind'] = '3'
    if mutation == 'log-details': f['receipt_events'][0]['fields']['details'] = '0x'
    if mutation == 'log-hash': f['receipt_events'][0]['fields']['detailsHash'] = ZERO
    if mutation == 'event-grant': f['receipt_events'][1]['fields']['grantId'] = '0x'+'99'*32
    if mutation == 'event-order': f['receipt_events'].reverse()
    if mutation == 'dbc-changed': f['after']['logs']['dbc'].append(dict(name='GrantIssued', fields={}))
    if mutation == 'worker-changed': f['after']['worker'] = log()
    if mutation == 'already-recorded':
        f['before']['requests'][DIGEST] = request_state('2', '5')
    with pytest.raises(ValueError):
        oracle('check_fabricated_outcome')(**f)


@pytest.mark.parametrize('mutation', ['accepted', 'other-code', 'logs', 'state-changed', 'witness-attests', 'witness-other-error',
                                      'no-attestation-check'])
def test_repaired_fabricated_outcome_rejects_false_observations(mutation):
    f = fabricated_facts('repaired-e')
    if mutation == 'accepted': f.update(success=True, rejection_code=None)
    if mutation == 'other-code': f['rejection_code'] = '16'
    if mutation == 'logs': f['receipt_events'] = [dict(name='OutcomeRecorded', fields={})]
    if mutation == 'state-changed': f['after']['requests'][DIGEST] = request_state('2', '9')
    if mutation == 'witness-attests': f['attestation'] = dict(ok=True, error=None)
    if mutation == 'witness-other-error': f['attestation'] = dict(ok=False, error='WRONG_SUBJECT')
    if mutation == 'no-attestation-check': f['attestation'] = None
    with pytest.raises(ValueError):
        oracle('check_fabricated_outcome')(**f)
