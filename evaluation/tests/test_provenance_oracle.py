"""Independent E01 relay-stress oracles (SL2): forged tuple, new reference, same nonce.

Expectations come from the frozen catalog rows and the pinned ledger source
(A1-0062, ledger 933d2a7: ACSC.policyEnf grants for any relay tuple; KSSC.sol:180
grant uniqueness then :182 nonce, both REPLAY 8; SigLib non-witness signer gives
BAD_SIGNATURE 1). Synthetic facts only; never integrated evidence. Each mutation
removes one join whose absence would admit a false result or deny-all.
"""
import copy
import importlib

import pytest

ZERO = '0x'+'00'*32
ALICE, RELAY, WITNESS = '0x'+'a1'*20, '0x'+'7e'*20, '0x'+'99'*20
DATA, CRED = '0x'+'da'*32, '0x'+'cd'*32
TS = 1000


def oracle(name):
    module = importlib.import_module('evaluation.oracles.provenance')
    assert hasattr(module, name), name+' oracle missing'
    return getattr(module, name)


def grant(ref, ts, *, recipient=ZERO, expires=None):
    return dict(exists=True, allowed=True, requestDigest=ref, dataId=DATA, gid=ALICE, keyEpoch='0',
                expiresAt=str(expires if expires is not None else ts+30), recipientKeyHash=recipient, issuedAt=str(ts))


EMPTY = dict(exists=False, allowed=False, requestDigest=ZERO, dataId=ZERO, gid='0x'+'00'*20, keyEpoch='0',
             expiresAt='0', recipientKeyHash=ZERO, issuedAt='0')


def events(ref, gid_, ts, *, count, consumed=False, nonce='0', expires=None, recipient=ZERO):
    return [dict(name='GrantIssued', fields=dict(grantId=gid_, requestDigest=ref, gid=ALICE, dataId=DATA, keyEpoch='0',
                                                 expiresAt=str(expires if expires is not None else ts+30), recipientKeyHash=recipient,
                                                 nonceConsumed=consumed, nonce=nonce)),
            dict(name='AccessLog', fields=dict(accessLogId=str(count), requestRef=ref, gid=ALICE, dataId=DATA, allowed=True,
                                               code='0', credentialDigest=CRED, grantId=gid_, submitter=RELAY))]


LOG = dict(schemaVersion='hmbc-worker-log/v0', events=[], releases=[], counts=dict(releaseIntentCount='0', releaseSentCount='0'))
# An idle but instantiated worker export, and the verified never-instantiated record (S3-0008):
# SL2 performs no worker operation, so the D2 worker database is never created.
WORKER = dict(instantiated=True, log=LOG)
NEVER = dict(instantiated=False, exitCode=1, message='no worker.sqlite in /tmp/p3/state (looked in <dir>/worker/ and in <dir>)\n',
             checkedAbsent=['/tmp/p3/state/worker/worker.sqlite', '/tmp/p3/state/worker.sqlite'])
MOVED = dict(instantiated=True, log=dict(LOG, events=[dict(type='RELEASE_INTENT')], counts=dict(releaseIntentCount='1', releaseSentCount='0')))


def snapshot(grants, requests, count, *, nonces=None, dbc=(), pbc=(), worker=NEVER):
    return dict(grants=copy.deepcopy(grants), requests=copy.deepcopy(requests), accessLogCount=str(count),
                nonces=copy.deepcopy(nonces or [[ALICE, '1', False]]),
                logs=dict(pbc=[dict(name='LogRecorded', fields={})]+list(pbc), dbc=list(dbc)), worker=copy.deepcopy(worker))


# ---------------------------------------------------------------- forged tuple

FORGED, FG = '0x'+'f0'*32, '0x'+'f1'*32
HONEST, HG = '0x'+'d1'*32, '0x'+'d2'*32


def forged_facts(profile):
    repaired = profile == 'repaired-e'
    if repaired:
        requests = {HONEST: dict(status='1', gid=ALICE)}
        before = snapshot({HG: EMPTY}, requests, 0)
        return dict(profile=profile, before=before, after=copy.deepcopy(before), gid=ALICE, data_id=DATA, relay=RELAY,
                    fabricated_ref=HONEST, grant_id=HG, credential_digest=CRED, success=False, rejection_code='1',
                    receipt_events=[], timestamp=str(TS),
                    forged=dict(honestSimulationGrantId=HG, recoveredSigner=RELAY, witnesses=[WITNESS],
                                decisionUnchanged=True, signatureChanged=True, signedDigestEqual=True))
    requests = {FORGED: dict(status='0')}
    before = snapshot({FG: EMPTY}, requests, 0)
    ev = events(FORGED, FG, TS, count=1)
    after = snapshot({FG: grant(FORGED, TS)}, requests, 1, dbc=ev)
    return dict(profile=profile, before=before, after=after, gid=ALICE, data_id=DATA, relay=RELAY, fabricated_ref=FORGED,
                grant_id=FG, credential_digest=CRED, success=True, rejection_code=None, receipt_events=ev,
                timestamp=str(TS), forged=None)


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_forged_tuple_expected_classes(profile):
    result = oracle('check_forged_tuple')(**forged_facts(profile))
    assert result['ok'] is True and result['delivery'] == 'unknown'
    if profile == 'repaired-e':
        assert result['classification'] == 'REPAIR_SUPPORTED' and result['error'] == 'BAD_SIGNATURE'
    else:
        assert result['classification'] == 'SPEC_GAP' and result['error'] is None and result['grantWithoutPbcLog'] is True


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal'])
@pytest.mark.parametrize('mutation', ['deny-all', 'pbc-request-exists', 'pbc-log-added', 'grant-gid', 'grant-ttl',
                                      'grant-recipient', 'event-order', 'access-submitter', 'access-ref', 'count',
                                      'nonce-changed', 'worker-changed', 'prior-grant', 'worker-instantiated-between',
                                      'never-other-message', 'never-other-exit', 'never-one-path', 'empty-export'])
def test_paper_forged_tuple_rejects_false_observations(profile, mutation):
    f = forged_facts(profile)
    if mutation == 'deny-all': f.update(success=False, rejection_code='9', receipt_events=[], after=copy.deepcopy(f['before']))
    if mutation == 'pbc-request-exists':
        for s in ('before', 'after'): f[s]['requests'][FORGED]['status'] = '1'
    if mutation == 'pbc-log-added': f['after']['logs']['pbc'].append(dict(name='LogRecorded', fields={}))
    if mutation == 'grant-gid': f['after']['grants'][FG]['gid'] = '0x'+'b0'*20
    if mutation == 'grant-ttl': f['after']['grants'][FG]['expiresAt'] = str(TS+31)
    if mutation == 'grant-recipient': f['after']['grants'][FG]['recipientKeyHash'] = '0x'+'11'*32
    if mutation == 'event-order': f['receipt_events'].reverse()
    if mutation == 'access-submitter': f['receipt_events'][1]['fields']['submitter'] = '0x'+'55'*20
    if mutation == 'access-ref': f['receipt_events'][1]['fields']['requestRef'] = HONEST
    if mutation == 'count': f['after']['accessLogCount'] = '2'
    if mutation == 'nonce-changed': f['after']['nonces'][0][2] = True
    if mutation == 'worker-changed': f['after']['worker'] = copy.deepcopy(MOVED)
    if mutation == 'worker-instantiated-between': f['after']['worker'] = copy.deepcopy(WORKER)
    if mutation == 'never-other-message': f['before']['worker']['message'] = 'Traceback (most recent call last):\n'
    if mutation == 'never-other-exit':
        for k in ('before', 'after'): f[k]['worker']['exitCode'] = 2
    if mutation == 'never-one-path':
        for k in ('before', 'after'): f[k]['worker']['checkedAbsent'] = f[k]['worker']['checkedAbsent'][:1]
    if mutation == 'empty-export':
        for k in ('before', 'after'): f[k]['worker'] = dict(instantiated=True, log={})
    if mutation == 'prior-grant': f['before']['grants'][FG] = grant(FORGED, TS-5)
    with pytest.raises(ValueError):
        oracle('check_forged_tuple')(**f)


@pytest.mark.parametrize('mutation', ['grant-all', 'wrong-code', 'logs', 'state-changed', 'no-simulation',
                                      'witness-signer', 'decision-changed', 'same-signature', 'no-pbc-request', 'digest-mismatch'])
def test_repaired_forged_tuple_rejects_false_observations(mutation):
    f = forged_facts('repaired-e')
    if mutation == 'grant-all': f.update(success=True, rejection_code=None)
    if mutation == 'wrong-code': f['rejection_code'] = '10'
    if mutation == 'logs': f['receipt_events'] = [dict(name='AccessLog', fields={})]
    if mutation == 'state-changed': f['after']['grants'][HG] = grant(HONEST, TS)
    if mutation == 'no-simulation': f['forged']['honestSimulationGrantId'] = ZERO
    if mutation == 'witness-signer': f['forged']['recoveredSigner'] = WITNESS
    if mutation == 'decision-changed': f['forged']['decisionUnchanged'] = False
    if mutation == 'same-signature': f['forged']['signatureChanged'] = False
    if mutation == 'no-pbc-request':
        for s in ('before', 'after'): f[s]['requests'][HONEST]['status'] = '0'
    if mutation == 'digest-mismatch': f['forged']['signedDigestEqual'] = False  # A1-0064: other digest/domain proves nothing
    with pytest.raises(ValueError):
        oracle('check_forged_tuple')(**f)


# ------------------------------------------------------------ new reference

ORIG, OG = '0x'+'0a'*32, '0x'+'0b'*32
FRESH, NG = '0x'+'0c'*32, '0x'+'0d'*32


def new_reference_facts(profile):
    repaired = profile == 'repaired-e'
    first = events(ORIG, OG, TS, count=1, consumed=repaired, nonce='1' if repaired else '0')
    if repaired:
        requests = {ORIG: dict(status='1', gid=ALICE)}
        before = snapshot({OG: grant(ORIG, TS)}, requests, 1, nonces=[[ALICE, '1', True]], dbc=first)
        return dict(profile=profile, before=before, after=copy.deepcopy(before), gid=ALICE, data_id=DATA, relay=RELAY,
                    original_ref=ORIG, original_grant=OG, replay_ref=ORIG, replay_grant=OG, credential_digest=CRED,
                    identical_calldata=True, success=False, rejection_code='8', receipt_events=[], timestamp=str(TS+3))
    requests = {ORIG: dict(status='1', gid=ALICE), FRESH: dict(status='0')}
    before = snapshot({OG: grant(ORIG, TS), NG: EMPTY}, requests, 1, dbc=first)
    second = events(FRESH, NG, TS+3, count=2)
    after = snapshot({OG: grant(ORIG, TS), NG: grant(FRESH, TS+3)}, requests, 2, dbc=first+second)
    return dict(profile=profile, before=before, after=after, gid=ALICE, data_id=DATA, relay=RELAY,
                original_ref=ORIG, original_grant=OG, replay_ref=FRESH, replay_grant=NG, credential_digest=CRED,
                identical_calldata=False, success=True, rejection_code=None, receipt_events=second, timestamp=str(TS+3))


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_new_reference_expected_classes(profile):
    result = oracle('check_new_reference')(**new_reference_facts(profile))
    assert result['ok'] is True
    if profile == 'repaired-e':
        assert result['classification'] == 'REPAIR_SUPPORTED' and result['error'] == 'REPLAY'
        assert 'grant uniqueness' in result['qualification']
    else:
        assert result['classification'] == 'SPEC_GAP' and result['secondGrant'] == NG


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal'])
@pytest.mark.parametrize('mutation', ['same-reference', 'deny-all', 'first-grant-changed', 'second-gid', 'second-ttl',
                                      'pbc-request', 'pbc-log', 'original-request-changed', 'count', 'no-first-grant'])
def test_paper_new_reference_rejects_false_observations(profile, mutation):
    f = new_reference_facts(profile)
    if mutation == 'same-reference': f.update(replay_ref=ORIG, replay_grant=OG)
    if mutation == 'deny-all': f.update(success=False, rejection_code='8', receipt_events=[], after=copy.deepcopy(f['before']))
    if mutation == 'first-grant-changed': f['after']['grants'][OG]['expiresAt'] = str(TS+99)
    if mutation == 'second-gid': f['after']['grants'][NG]['gid'] = '0x'+'b0'*20
    if mutation == 'second-ttl': f['after']['grants'][NG]['expiresAt'] = str(TS+3+29)
    if mutation == 'pbc-request':
        for s in ('before', 'after'): f[s]['requests'][FRESH]['status'] = '1'
    if mutation == 'pbc-log': f['after']['logs']['pbc'].append(dict(name='LogRecorded', fields={}))
    if mutation == 'original-request-changed': f['after']['requests'][ORIG]['status'] = '2'
    if mutation == 'count': f['after']['accessLogCount'] = '3'
    if mutation == 'no-first-grant': f['before']['grants'][OG] = EMPTY
    with pytest.raises(ValueError):
        oracle('check_new_reference')(**f)


@pytest.mark.parametrize('mutation', ['fresh-signed-request', 'other-grant', 'wrong-code', 'state-changed', 'logs', 'success'])
def test_repaired_new_reference_rejects_false_observations(mutation):
    f = new_reference_facts('repaired-e')
    if mutation == 'fresh-signed-request': f['identical_calldata'] = False
    if mutation == 'other-grant': f['replay_grant'] = NG
    if mutation == 'wrong-code': f['rejection_code'] = '7'
    if mutation == 'state-changed': f['after']['nonces'][0][2] = False
    if mutation == 'logs': f['receipt_events'] = [dict(name='GrantIssued', fields={})]
    if mutation == 'success': f.update(success=True, rejection_code=None)
    with pytest.raises(ValueError):
        oracle('check_new_reference')(**f)


# --------------------------------------------------------------- same nonce

D1, G1, D2, G2 = '0x'+'e1'*32, '0x'+'e2'*32, '0x'+'e3'*32, '0x'+'e4'*32


def same_nonce_facts():
    base = dict(gid=ALICE, nonce='1', dataId=DATA)
    first = dict(request=dict(base, expiresAt=str(TS+30)), digest=D1, grantId=G1, block='40')
    second = dict(request=dict(base, expiresAt=str(TS+29)), digest=D2, grantId=G2, block='41')
    checkpoint = dict(sequence='2', sourceBlockNumber='42')
    decisions = [dict(decision=dict(requestDigest=D1, result='1', stateSequence='2'), dbcBlock='60'),
                 dict(decision=dict(requestDigest=D2, result='1', stateSequence='2'), dbcBlock='60')]
    ev = events(D1, G1, TS+5, count=1, consumed=True, nonce='1', expires=TS+30, recipient='0x'+'ab'*32)
    consume_first = dict(success=True, block='61', grantId=G1, events=ev)
    requests = {D1: dict(status='1'), D2: dict(status='1')}
    held = snapshot({G1: grant(D1, TS+5, recipient='0x'+'ab'*32, expires=TS+30), G2: EMPTY}, requests, 1,
                    nonces=[[ALICE, '1', True]], dbc=ev)
    held.pop('worker')
    return dict(first=first, second=second, checkpoint=checkpoint, decisions=decisions, consume_first=consume_first,
                before_second=held, after_second=copy.deepcopy(held), before_block='61', second_block='62',
                success=False, rejection_code='8', receipt_events=[], worker_before=copy.deepcopy(NEVER),
                worker_after=copy.deepcopy(NEVER))


def test_same_nonce_second_precollected_certificate_is_replay():
    result = oracle('check_same_nonce')(**same_nonce_facts())
    assert result['ok'] is True and result['classification'] == 'REPAIR_SUPPORTED' and result['error'] == 'REPLAY'
    assert result['nonceGuardReached'] is True


@pytest.mark.parametrize('mutation', ['different-nonce', 'different-gid', 'same-expiry', 'same-digest', 'same-grant',
                                      'checkpoint-before-forward', 'decision-after-consume', 'decision-deny',
                                      'decision-digest', 'decision-sequence', 'first-not-consumed', 'first-failed',
                                      'second-granted', 'wrong-code', 'logs', 'state-changed', 'not-adjacent',
                                      'worker-changed', 'nonce-not-recorded', 'worker-instantiated-between'])
def test_same_nonce_rejects_false_or_masked_observations(mutation):
    f = same_nonce_facts()
    if mutation == 'different-nonce': f['second']['request']['nonce'] = '2'
    if mutation == 'different-gid': f['second']['request']['gid'] = '0x'+'b0'*20
    if mutation == 'same-expiry': f['second']['request']['expiresAt'] = f['first']['request']['expiresAt']
    if mutation == 'same-digest': f['second']['digest'] = D1
    if mutation == 'same-grant': f['second']['grantId'] = G1
    if mutation == 'checkpoint-before-forward': f['checkpoint']['sourceBlockNumber'] = '40'
    if mutation == 'decision-after-consume': f['decisions'][1]['dbcBlock'] = '61'
    if mutation == 'decision-deny': f['decisions'][1]['decision']['result'] = '0'
    if mutation == 'decision-digest': f['decisions'][1]['decision']['requestDigest'] = D1
    if mutation == 'decision-sequence': f['decisions'][0]['decision']['stateSequence'] = '1'
    if mutation == 'first-not-consumed': f['before_second']['grants'][G1] = EMPTY
    if mutation == 'first-failed': f['consume_first']['success'] = False
    if mutation == 'second-granted': f['after_second']['grants'][G2] = grant(D2, TS+6)
    if mutation == 'wrong-code': f['rejection_code'] = '7'   # an EXPIRED trial masks the nonce guard
    if mutation == 'logs': f['receipt_events'] = [dict(name='AccessLog', fields={})]
    if mutation == 'state-changed': f['after_second']['accessLogCount'] = '2'
    if mutation == 'not-adjacent': f['before_block'] = '60'
    if mutation == 'worker-changed': f['worker_after'] = copy.deepcopy(MOVED)
    if mutation == 'worker-instantiated-between': f['worker_after'] = copy.deepcopy(WORKER)
    if mutation == 'nonce-not-recorded':
        for s in ('before_second', 'after_second'): f[s]['nonces'][0][2] = False
    with pytest.raises(ValueError):
        oracle('check_same_nonce')(**f)


@pytest.mark.parametrize('worker', ['never-instantiated', 'idle-export'])
@pytest.mark.parametrize('profile', ['paper-strict', 'repaired-e'])
def test_idle_worker_may_be_never_instantiated_or_an_unchanged_idle_export(profile, worker):
    f = forged_facts(profile)
    for k in ('before', 'after'): f[k]['worker'] = copy.deepcopy(NEVER if worker == 'never-instantiated' else WORKER)
    assert oracle('check_forged_tuple')(**f)['ok'] is True
    g = new_reference_facts(profile)
    for k in ('before', 'after'): g[k]['worker'] = copy.deepcopy(NEVER if worker == 'never-instantiated' else WORKER)
    assert oracle('check_new_reference')(**g)['ok'] is True
