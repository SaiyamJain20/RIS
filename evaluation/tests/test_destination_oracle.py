"""Independent E01 wrong-destination and expiry-boundary oracle (SL7; frozen rows E01-wrong-destination-*,
E01-expiry-boundary-*).

Expectations: frozen catalog rows; pinned ledger (933d2a7): repaired-e DecisionVerifier step 1 (line 60,
source chain/PSC) and step 2 (lines 61-64, destination chain/KSSC, skipped only by MUT_NO_DESTINATION_BINDING)
give WRONG_DESTINATION; step 9 (line 74) uses >=, so a consumption exactly at the request expiry gives
EXPIRED; paper ACSC.policyEnf (ACSC.sol:140-167) has no destination or request-expiry input and fills the
grant expiry as block + grantTtl (line 154). A1 pre-FREEZE conditions (2026-10-11 ~13:20 IST): record which
step fires; the second deployment B is on the same chain pair; consumption at expiresAt exactly with the
decision expiry equal to it and the checkpoint expiry above it. Synthetic facts only.
"""
import copy
import importlib

import pytest
from eth_utils import keccak

from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_bootstrap import inputs

ZERO = '0x'+'00'*32
NOW = 1791476010
DIGEST, GRANT_A, GRANT_B = '0x'+'d1'*32, '0x'+'a2'*32, '0x'+'b2'*32
ALICE, DATA = '0xc4ff0022e776c3471e39abf6c69ce679440c956d', '0x53ff15331656b9b303d95970634a992ed32268c5d9723c90ddc94ceeb397061e'
RK = '0x'+keccak(text='HMBC.recipient-key.alice').hex()
NEVER = dict(instantiated=False, exitCode=1, message='no worker.sqlite in /tmp/p3/d (looked in <dir>/worker/ and in <dir>)\n',
             checkedAbsent=['/tmp/p3/d/worker/worker.sqlite', '/tmp/p3/d/worker.sqlite'])
PROFILES = ['paper-strict', 'paper-minimal', 'repaired-e']
A = dict(pbcChainId='18545', psc='0x'+'a1'*20, dbcChainId='28545', kssc='0x'+'a3'*20)
B = dict(pbcChainId='18545', psc='0x'+'b1'*20, dbcChainId='28545', kssc='0x'+'b3'*20)


def oracle(name):
    module = importlib.import_module('evaluation.oracles.destination')
    assert hasattr(module, name), 'destination oracle missing'
    return getattr(module, name)


def snapshot(grant_id, status, nonce=False):
    absent = dict(exists=False, allowed=False, requestDigest=ZERO, dataId=ZERO, gid='0x'+'00'*20, keyEpoch='0', expiresAt='0',
                  recipientKeyHash=ZERO, issuedAt='0')
    state = dict(status=status, gid=ALICE if status != '0' else '0x'+'00'*20, dataId=DATA if status != '0' else ZERO, outcomeLogId='0')
    return dict(grants={grant_id: absent}, requests={DIGEST: state}, accessLogCount='0', nonces=[[ALICE, '1', nonce]],
                logs=dict(pbc=[dict(name='TrustAnchorUpdated', fields={})], dbc=[dict(name='DataRegistered', fields={})]), worker=copy.deepcopy(NEVER))


def grant_events(grant_id, ts, relay, cd):
    return [dict(name='GrantIssued', fields=dict(grantId=grant_id, requestDigest=DIGEST, gid=ALICE, dataId=DATA, keyEpoch='0',
                                                 expiresAt=str(ts+30), recipientKeyHash=ZERO, nonceConsumed=False, nonce='0')),
            dict(name='AccessLog', fields=dict(accessLogId='1', requestRef=DIGEST, gid=ALICE, dataId=DATA, allowed=True, code='0',
                                               credentialDigest=cd, grantId=grant_id, submitter=relay))]


def apply_grant(snap, grant_id, events, ts):
    after = copy.deepcopy(snap)
    after['grants'][grant_id] = dict(exists=True, allowed=True, requestDigest=DIGEST, dataId=DATA, gid=ALICE, keyEpoch='0',
                                     expiresAt=str(ts+30), recipientKeyHash=ZERO, issuedAt=str(ts))
    after['accessLogCount'] = '1'; after['logs']['dbc'] += copy.deepcopy(events)
    return after


def destination_facts(artifacts, profile):
    relay = artifacts[0]['fixture']['relay']['address']; repaired = profile == 'repaired-e'; cd = '0x'+'cd'*32
    request = dict(digest=DIGEST, sourceChainId=B['pbcChainId'], psc=B['psc'], destinationChainId=B['dbcChainId'], kssc=B['kssc'],
                   gid=ALICE, dataId=DATA, nonce='1', expiresAt=str(NOW+33), credentialDigest=cd, timestamp=str(NOW+3))
    before_a, before_b = snapshot(GRANT_A, '0'), snapshot(GRANT_B, '1')
    ts = NOW+8
    decision = dict(decision=dict(requestDigest=DIGEST, result='1', stateSequence='1', expiresAt=str(NOW+33), credentialDigest=cd),
                    collectedDbcNow=str(NOW+5)) if repaired else None
    checkpoint = dict(sequence='1', expiresAt=str(NOW+65)) if repaired else None
    if repaired:
        events, after_a, success, code = [], copy.deepcopy(before_a), False, '3'
    else:
        events = grant_events(GRANT_A, ts, relay, cd); after_a = apply_grant(before_a, GRANT_A, events, ts); success, code = True, None
    return dict(profile=profile, request=request, receiver=dict(A), source=dict(B), grant_id_a=GRANT_A, grant_id_b=GRANT_B,
                before_a=before_a, after_a=after_a, before_b=before_b, after_b=copy.deepcopy(before_b), decision=decision,
                checkpoint=checkpoint, success=success, rejection_code=code, consume_events=events, consume_timestamp=str(ts),
                decision_collections=1 if repaired else 0, relay=relay)


def boundary_facts(artifacts, profile):
    relay = artifacts[0]['fixture']['relay']['address']; repaired = profile == 'repaired-e'; cd = '0x'+'cd'*32
    expires = NOW+33
    request = dict(digest=DIGEST, sourceChainId=A['pbcChainId'], psc=A['psc'], destinationChainId=A['dbcChainId'], kssc=A['kssc'],
                   gid=ALICE, dataId=DATA, nonce='1', expiresAt=str(expires), credentialDigest=cd, timestamp=str(NOW+3))
    before = snapshot(GRANT_A, '1')
    decision = dict(decision=dict(requestDigest=DIGEST, result='1', stateSequence='1', expiresAt=str(expires), credentialDigest=cd),
                    collectedDbcNow=str(NOW+5)) if repaired else None
    checkpoint = dict(sequence='1', expiresAt=str(NOW+65)) if repaired else None
    clock = dict(dbcBefore=str(NOW+6), target=str(expires))
    if repaired:
        events, after, success, code = [], copy.deepcopy(before), False, '7'
    else:
        events = grant_events(GRANT_A, expires, relay, cd); after = apply_grant(before, GRANT_A, events, expires); success, code = True, None
    return dict(profile=profile, request=request, grant_id=GRANT_A, before=before, after=after, decision=decision, checkpoint=checkpoint,
                clock=clock, success=success, rejection_code=code, consume_events=events, consume_timestamp=str(expires),
                decision_collections=1 if repaired else 0, relay=relay)


@pytest.mark.parametrize('profile', PROFILES)
def test_wrong_destination_expected_classes(artifacts, profile):
    result = oracle('check_wrong_destination')(**destination_facts(artifacts, profile))
    assert result['ok'] and result['delivery'] == 'unknown'
    if profile == 'repaired-e':
        assert (result['classification'], result['error'], result['outcome']) == ('REPAIR_SUPPORTED', 'WRONG_DESTINATION', 'REJECT')
        assert result['firingStep'] == 1 and result['step2Mismatch'] is True and result['killsNoDestinationBindingMutant'] is False
    else:
        assert (result['classification'], result['error'], result['outcome']) == ('SPEC_GAP', None, 'ACCEPT')
        assert result['receiverHasRequest'] is False


@pytest.mark.parametrize('profile', PROFILES)
def test_expiry_boundary_expected_classes(artifacts, profile):
    f = boundary_facts(artifacts, profile)
    result = oracle('check_expiry_boundary')(**f)
    assert result['ok'] and result['delivery'] == 'unknown'
    t = result['timing']
    assert t['consumeTimestamp'] == t['requestExpiresAt'] == f['request']['expiresAt']
    if profile == 'repaired-e':
        assert (result['classification'], result['error'], result['outcome']) == ('REPAIR_SUPPORTED', 'EXPIRED', 'REJECT')
        assert result['firingStep'] == 9 and t['decisionExpiresAt'] == f['request']['expiresAt']
    else:
        assert (result['classification'], result['error'], result['outcome']) == ('SPEC_GAP', None, 'ACCEPT')
        assert t['grantExpiresAt'] == str(int(f['request']['expiresAt'])+30)


DEST_COMMON = ['worker-a-changed', 'worker-b-changed', 'receiver-has-request', 'request-not-for-source', 'same-deployment', 'source-state-changed']
DEST_PAPER = ['rejected', 'grant-other-expiry', 'grant-recipient', 'state-unchanged', 'decision-present']
DEST_REPAIRED = ['accepted', 'other-code', 'two-decisions', 'receiver-changed', 'source-matches-receiver-psc']


def mutate_destination(f, m):
    if m == 'worker-a-changed': f['after_a']['worker'] = dict(instantiated=True, log=dict(events=[], releases=[]))
    if m == 'worker-b-changed': f['after_b']['worker'] = dict(instantiated=True, log=dict(events=[], releases=[]))
    if m == 'receiver-has-request': f['before_a']['requests'][DIGEST] = dict(f['before_b']['requests'][DIGEST])
    if m == 'request-not-for-source': f['request']['kssc'] = A['kssc']
    if m == 'same-deployment': f['source'] = dict(A); f['request'].update(psc=A['psc'], kssc=A['kssc'])
    if m == 'source-state-changed': f['after_b']['nonces'] = [[ALICE, '1', True]]
    if m == 'rejected': f.update(success=False, rejection_code='9', consume_events=[], after_a=copy.deepcopy(f['before_a']))
    if m == 'grant-other-expiry': f['consume_events'][0]['fields']['expiresAt'] = '1'
    if m == 'grant-recipient': f['consume_events'][0]['fields']['recipientKeyHash'] = RK
    if m == 'state-unchanged': f['after_a'] = copy.deepcopy(f['before_a'])
    if m == 'decision-present': f['decision'] = dict(decision=dict(requestDigest=DIGEST), collectedDbcNow='0')
    if m == 'accepted': f.update(success=True, rejection_code=None)
    if m == 'other-code': f['rejection_code'] = '2'
    if m == 'two-decisions': f['decision_collections'] = 2
    if m == 'receiver-changed': f['after_a']['accessLogCount'] = '1'
    if m == 'source-matches-receiver-psc': f['request']['psc'] = A['psc']; f['source']['psc'] = A['psc']
    return f


@pytest.mark.parametrize('profile', PROFILES[:2])
@pytest.mark.parametrize('mutation', DEST_COMMON+DEST_PAPER)
def test_wrong_destination_paper_refuses(artifacts, profile, mutation):
    with pytest.raises(ValueError):
        oracle('check_wrong_destination')(**mutate_destination(destination_facts(artifacts, profile), mutation))


@pytest.mark.parametrize('mutation', DEST_COMMON+DEST_REPAIRED)
def test_wrong_destination_repaired_refuses(artifacts, mutation):
    with pytest.raises(ValueError):
        oracle('check_wrong_destination')(**mutate_destination(destination_facts(artifacts, 'repaired-e'), mutation))


BOUND_COMMON = ['worker-changed', 'consume-plus-one', 'consume-minus-one', 'clock-target-other', 'clock-already-past', 'request-not-forwarded']
BOUND_PAPER = ['rejected', 'grant-other-expiry', 'state-unchanged', 'decision-present']
BOUND_REPAIRED = ['accepted', 'other-code', 'two-decisions', 'decision-capped', 'checkpoint-not-above', 'state-changed']


def mutate_boundary(f, m):
    e = int(f['request']['expiresAt'])
    if m == 'worker-changed': f['after']['worker'] = dict(instantiated=True, log=dict(events=[], releases=[]))
    if m == 'consume-plus-one': f['consume_timestamp'] = str(e+1)
    if m == 'consume-minus-one': f['consume_timestamp'] = str(e-1)
    if m == 'clock-target-other': f['clock']['target'] = str(e+1)
    if m == 'clock-already-past': f['clock']['dbcBefore'] = str(e)
    if m == 'request-not-forwarded': f['before']['requests'][DIGEST]['status'] = '0'
    if m == 'rejected': f.update(success=False, rejection_code='7', consume_events=[], after=copy.deepcopy(f['before']))
    if m == 'grant-other-expiry': f['consume_events'][0]['fields']['expiresAt'] = str(e)
    if m == 'state-unchanged': f['after'] = copy.deepcopy(f['before'])
    if m == 'decision-present': f['decision'] = dict(decision=dict(requestDigest=DIGEST), collectedDbcNow='0')
    if m == 'accepted': f.update(success=True, rejection_code=None)
    if m == 'other-code': f['rejection_code'] = '6'
    if m == 'two-decisions': f['decision_collections'] = 2
    if m == 'decision-capped': f['decision']['decision']['expiresAt'] = str(e-1)
    if m == 'checkpoint-not-above': f['checkpoint']['expiresAt'] = str(e)
    if m == 'state-changed': f['after']['nonces'] = [[ALICE, '1', True]]
    return f


@pytest.mark.parametrize('profile', PROFILES[:2])
@pytest.mark.parametrize('mutation', BOUND_COMMON+BOUND_PAPER)
def test_expiry_boundary_paper_refuses(artifacts, profile, mutation):
    with pytest.raises(ValueError):
        oracle('check_expiry_boundary')(**mutate_boundary(boundary_facts(artifacts, profile), mutation))


@pytest.mark.parametrize('mutation', BOUND_COMMON+BOUND_REPAIRED)
def test_expiry_boundary_repaired_refuses(artifacts, mutation):
    with pytest.raises(ValueError):
        oracle('check_expiry_boundary')(**mutate_boundary(boundary_facts(artifacts, 'repaired-e'), mutation))
