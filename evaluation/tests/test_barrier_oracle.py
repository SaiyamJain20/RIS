"""Independent E02 revocation-barrier and expired-duty oracle (SL6; frozen rows E02-pre-barrier-revocation-*,
E02-post-barrier-revocation-*, E02-expired-duty-*).

Expectations: frozen catalog rows; pinned ledger (933d2a7): paper ACSC.policyEnf evaluates the relay's
records without any freshness or checkpoint check and grants (TTL +30 s, recipient 0); repaired-e
DecisionVerifier: step 9 request/decision expiry EXPIRED, step 10 checkpoint sequence STALE_STATE, step 13
record freshness EXPIRED. A revocation on the PBC is invisible to the DBC until a new checkpoint is
accepted (pre-barrier window, intentional); after it the older certificate gives STALE_STATE; a duty that
ends before consumption gives EXPIRED from step 13 only if the request, decision and checkpoint are still
live. A31: exactly one collect_decision per request. A1 pre-FREEZE conditions (2026-10-11): post-barrier
STALE_STATE must be the sequence cause of DV line 87 (new checkpoint current at consume, decision not
outliving it, steps 9 and 10a passing); expired-duty EXPIRED must be step 13 (duty end <= consume <
min(decision, request, checkpoint expiry)); pre-barrier consumes on the unchanged first checkpoint.
Synthetic facts only.
"""
import copy
import importlib

import pytest
from eth_utils import keccak

from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_bootstrap import inputs

ZERO = '0x'+'00'*32
NOW = 1791476010
DIGEST, GRANT = '0x'+'d1'*32, '0x'+'d2'*32
ALICE, DATA = '0xc4ff0022e776c3471e39abf6c69ce679440c956d', '0x53ff15331656b9b303d95970634a992ed32268c5d9723c90ddc94ceeb397061e'
H1 = '0x88a358e9636d8c7f121f9beb24cbc9f2fb329c1e'
RK = '0x'+keccak(text='HMBC.recipient-key.alice').hex()
NEVER = dict(instantiated=False, exitCode=1, message='no worker.sqlite in /tmp/p3/b (looked in <dir>/worker/ and in <dir>)\n',
             checkedAbsent=['/tmp/p3/b/worker/worker.sqlite', '/tmp/p3/b/worker.sqlite'])
PROFILES = ['paper-strict', 'paper-minimal', 'repaired-e']
VARIANTS = ['pre-barrier-revocation', 'post-barrier-revocation', 'expired-duty']


def oracle():
    module = importlib.import_module('evaluation.oracles.barrier')
    assert hasattr(module, 'check_barrier_row'), 'barrier oracle missing'
    return module.check_barrier_row


def facts(artifacts, profile, variant):
    dep = artifacts[0]; relay = dep['fixture']['relay']['address']
    repaired, expired, post = profile == 'repaired-e', variant == 'expired-duty', variant == 'post-barrier-revocation'
    duty_end = str(NOW+25) if expired else '1791642157'
    records = [dict(issuer=H1, role='0x'+keccak(text='HMBC.role.Doctor').hex(), kind='1', serial='101', anchorVersion='1', validUntil='1791699757'),
               dict(issuer=H1, role='0x'+keccak(text='HMBC.role.OnDuty').hex(), kind='2', serial='0', anchorVersion='2' if expired else '1',
                    validUntil=duty_end)]
    cd = '0x'+'cd'*32
    request = dict(digest=DIGEST, grantId=GRANT, gid=ALICE, dataId=DATA, nonce='1', recipientKeyHash=RK, timestamp=str(NOW+3),
                   expiresAt=str(NOW+33), authEpoch='5', records=records, credentialDigest=cd, pbcBlockNumber='312')
    cp1 = dict(sequence='1', authEpoch='5', sourceBlockNumber='312', expiresAt=str(NOW+65))
    decision = dict(decision=dict(requestDigest=DIGEST, result='1', credentialDigest=cd, stateSequence='1', expiresAt=str(NOW+33)),
                    collectedDbcNow=str(NOW+5), collectedPbcBlock='312') if repaired else None
    checkpoints = ([cp1]+([dict(sequence='2', authEpoch='6', sourceBlockNumber='316', expiresAt=str(NOW+70))] if post else [])) if repaired else []
    revocation = None if expired else dict(timestamp=str(NOW+7), blockNumber='315', success=True,
                                           before=dict(revoked=False, credentialsCode='0', authEpoch='5'),
                                           after=dict(revoked=True, credentialsCode='19', authEpoch='6'))
    clock = dict(dutyEnd=duty_end, dbcBefore=str(NOW+6), advancedTo=duty_end) if expired else None
    consume = str(NOW+26) if expired else str(NOW+9)
    state = dict(status='1', gid=ALICE, dataId=DATA, outcomeLogId='0')
    absent = dict(exists=False, allowed=False, requestDigest=ZERO, dataId=ZERO, gid='0x'+'00'*20, keyEpoch='0', expiresAt='0',
                  recipientKeyHash=ZERO, issuedAt='0')
    before = dict(grants={GRANT: absent}, requests={DIGEST: state}, accessLogCount='0', nonces=[[ALICE, '1', False]],
                  logs=dict(pbc=[dict(name='AccessForwarded', fields={})], dbc=[dict(name='StateAccepted', fields={})]), worker=copy.deepcopy(NEVER))
    after = copy.deepcopy(before); success, code, events = True, None, []
    if not repaired:
        grant = dict(exists=True, allowed=True, requestDigest=DIGEST, dataId=DATA, gid=ALICE, keyEpoch='0', expiresAt=str(int(consume)+30),
                     recipientKeyHash=ZERO, issuedAt=consume)
        events = [dict(name='GrantIssued', fields=dict(grantId=GRANT, requestDigest=DIGEST, gid=ALICE, dataId=DATA, keyEpoch='0',
                                                       expiresAt=grant['expiresAt'], recipientKeyHash=ZERO, nonceConsumed=False, nonce='0')),
                  dict(name='AccessLog', fields=dict(accessLogId='1', requestRef=DIGEST, gid=ALICE, dataId=DATA, allowed=True, code='0',
                                                     credentialDigest=cd, grantId=GRANT, submitter=relay))]
    elif variant == 'pre-barrier-revocation':
        expiry = str(min(int(decision['decision']['expiresAt']), int(request['expiresAt'])))
        grant = dict(exists=True, allowed=True, requestDigest=DIGEST, dataId=DATA, gid=ALICE, keyEpoch='0', expiresAt=expiry,
                     recipientKeyHash=RK, issuedAt=consume)
        events = [dict(name='GrantIssued', fields=dict(grantId=GRANT, requestDigest=DIGEST, gid=ALICE, dataId=DATA, keyEpoch='0', expiresAt=expiry,
                                                       recipientKeyHash=RK, nonceConsumed=True, nonce='1')),
                  dict(name='AccessLog', fields=dict(accessLogId='1', requestRef=DIGEST, gid=ALICE, dataId=DATA, allowed=True, code='0',
                                                     credentialDigest=cd, grantId=GRANT, submitter=relay))]
        after['nonces'] = [[ALICE, '1', True]]
    else:
        success, code = False, '7' if expired else '6'
    if events:
        after['grants'][GRANT] = grant; after['accessLogCount'] = '1'; after['logs']['dbc'] += copy.deepcopy(events)
    current = copy.deepcopy(checkpoints[-1]) if repaired else None
    return dict(profile=profile, variant=variant, request=request, decision=decision, checkpoints=checkpoints, revocation=revocation,
                clock=clock, before=before, after=after, success=success, rejection_code=code, consume_events=events,
                consume_timestamp=consume, decision_collections=1 if repaired else 0, relay=relay, current_checkpoint=current)


EXPECTED = {**{(p, v): ('SPEC_GAP', None, 'ACCEPT') for p in PROFILES[:2] for v in VARIANTS},
            ('repaired-e', 'pre-barrier-revocation'): ('REPAIR_SUPPORTED', None, 'ACCEPT'),
            ('repaired-e', 'post-barrier-revocation'): ('REPAIR_SUPPORTED', 'STALE_STATE', 'REJECT'),
            ('repaired-e', 'expired-duty'): ('REPAIR_SUPPORTED', 'EXPIRED', 'REJECT')}


@pytest.mark.parametrize('profile', PROFILES)
@pytest.mark.parametrize('variant', VARIANTS)
def test_expected_classes(artifacts, profile, variant):
    f = facts(artifacts, profile, variant)
    result = oracle()(**f)
    assert result['ok'] and result['delivery'] == 'unknown'
    assert (result['classification'], result['error'], result['outcome']) == EXPECTED[(profile, variant)]
    timing = result['timing']; assert timing['consumeTimestamp'] == f['consume_timestamp'] and timing['requestExpiresAt'] == f['request']['expiresAt']
    if profile == 'repaired-e':
        assert timing['decisionExpiresAt'] == f['decision']['decision']['expiresAt'] and timing['checkpointExpiresAt'] == f['checkpoints'][-1]['expiresAt']
    if variant == 'expired-duty':
        assert timing['dutyEnd'] == f['clock']['dutyEnd']
    if (profile, variant) == ('repaired-e', 'post-barrier-revocation'):
        assert timing['decisionSequence'] == '1' and timing['currentSequence'] == '2' and result['staleCause'] == 'sequence'
    if (profile, variant) == ('repaired-e', 'expired-duty'):
        assert result['expiredStep'] == 13


COMMON = ['worker-changed', 'request-not-forwarded', 'grant-existed']
PAPER = ['rejected', 'grant-other-expiry', 'state-unchanged', 'decision-present', 'consume-before-revocation-or-duty']
REPAIRED = {'pre-barrier-revocation': ['rejected', 'two-decisions', 'recollected-after-revocation', 'checkpoint-after-revocation',
                                       'not-revoked', 'grant-other-expiry', 'nonce-unconsumed'],
            'post-barrier-revocation': ['accepted', 'other-code', 'two-decisions', 'recollected-after-revocation', 'cp2-same-sequence',
                                        'cp2-old-epoch', 'cp2-before-revocation', 'state-changed', 'no-second-checkpoint',
                                        'cp2-not-current', 'decision-outlives-cp2', 'consume-after-cp2-expiry', 'consume-after-decision-expiry',
                                        'consume-after-request-expiry'],
            'expired-duty': ['accepted', 'other-code', 'two-decisions', 'decision-after-duty', 'consume-after-request-expiry',
                             'consume-after-decision-expiry', 'consume-after-checkpoint-expiry', 'consume-before-duty-end', 'clock-not-advanced',
                             'state-changed', 'request-after-duty', 'checkpoint-changed']}
REPAIRED['pre-barrier-revocation'] += ['new-checkpoint-before-consume', 'epoch-mismatch']


def mutate(f, mutation):
    if mutation == 'worker-changed': f['after']['worker'] = dict(instantiated=True, log=dict(events=[], releases=[]))
    if mutation == 'request-not-forwarded': f['before']['requests'][DIGEST]['status'] = '0'
    if mutation == 'grant-existed': f['before']['grants'][GRANT] = dict(f['before']['grants'][GRANT], exists=True, allowed=True)
    if mutation == 'rejected': f.update(success=False, rejection_code='9', consume_events=[], after=copy.deepcopy(f['before']))
    if mutation == 'accepted':
        f.update(success=True, rejection_code=None)
    if mutation == 'other-code': f['rejection_code'] = '6' if f['rejection_code'] == '7' else '7'
    if mutation == 'grant-other-expiry':
        e = f['consume_events'][0]['fields']; e['expiresAt'] = str(int(e['expiresAt'])+1)
    if mutation == 'state-unchanged': f['after'] = copy.deepcopy(f['before'])
    if mutation == 'state-changed': f['after']['nonces'] = [[ALICE, '1', True]]
    if mutation == 'nonce-unconsumed': f['after']['nonces'] = [[ALICE, '1', False]]
    if mutation == 'decision-present': f['decision'] = dict(decision=dict(requestDigest=DIGEST), collectedDbcNow='0', collectedPbcBlock='0')
    if mutation == 'consume-before-revocation-or-duty':
        if f['revocation']: f['revocation']['timestamp'] = str(int(f['consume_timestamp'])+1)
        else: f['consume_timestamp'] = str(int(f['clock']['dutyEnd'])-1)
    if mutation == 'two-decisions': f['decision_collections'] = 2
    if mutation == 'recollected-after-revocation': f['decision']['collectedPbcBlock'] = f['revocation']['blockNumber']
    if mutation == 'checkpoint-after-revocation': f['checkpoints'][0]['sourceBlockNumber'] = f['revocation']['blockNumber']
    if mutation == 'not-revoked': f['revocation']['after'] = dict(f['revocation']['after'], revoked=False, credentialsCode='0')
    if mutation == 'cp2-same-sequence': f['checkpoints'][1]['sequence'] = f['checkpoints'][0]['sequence']
    if mutation == 'cp2-old-epoch': f['checkpoints'][1]['authEpoch'] = f['checkpoints'][0]['authEpoch']
    if mutation == 'cp2-before-revocation': f['checkpoints'][1]['sourceBlockNumber'] = str(int(f['revocation']['blockNumber'])-1)
    if mutation == 'no-second-checkpoint': f['checkpoints'] = f['checkpoints'][:1]
    if mutation == 'decision-after-duty': f['decision']['collectedDbcNow'] = f['clock']['dutyEnd']
    if mutation == 'consume-after-request-expiry': f['consume_timestamp'] = f['request']['expiresAt']
    if mutation == 'consume-after-decision-expiry':
        f['decision']['decision']['expiresAt'] = str(int(f['consume_timestamp']))
    if mutation == 'consume-before-duty-end': f['consume_timestamp'] = str(int(f['clock']['dutyEnd'])-1)
    if mutation == 'clock-not-advanced': f['clock']['advancedTo'] = str(int(f['clock']['dutyEnd'])-1)
    if mutation == 'request-after-duty': f['request']['timestamp'] = f['clock']['dutyEnd']
    if mutation in ('checkpoint-after-revocation', 'cp2-same-sequence', 'cp2-old-epoch', 'cp2-before-revocation', 'no-second-checkpoint'):
        f['current_checkpoint'] = copy.deepcopy(f['checkpoints'][-1])   # a consistent world: the mutated checkpoint is the current one
    if mutation == 'cp2-not-current': f['current_checkpoint'] = copy.deepcopy(f['checkpoints'][0])
    if mutation == 'decision-outlives-cp2': f['checkpoints'][1]['expiresAt'] = str(int(f['decision']['decision']['expiresAt'])-1); f['current_checkpoint'] = copy.deepcopy(f['checkpoints'][1])
    if mutation == 'consume-after-cp2-expiry':
        f['checkpoints'][1]['expiresAt'] = f['consume_timestamp']; f['current_checkpoint'] = copy.deepcopy(f['checkpoints'][1])
    if mutation == 'consume-after-checkpoint-expiry':
        f['checkpoints'][0]['expiresAt'] = f['consume_timestamp']; f['current_checkpoint'] = copy.deepcopy(f['checkpoints'][0])
    if mutation == 'checkpoint-changed': f['current_checkpoint'] = dict(f['checkpoints'][0], sequence='2')
    if mutation == 'new-checkpoint-before-consume': f['current_checkpoint'] = dict(f['checkpoints'][0], sequence='2', authEpoch='6')
    if mutation == 'epoch-mismatch': f['checkpoints'][0]['authEpoch'] = '4'; f['current_checkpoint'] = copy.deepcopy(f['checkpoints'][0])
    return f


@pytest.mark.parametrize('profile', PROFILES[:2])
@pytest.mark.parametrize('variant', VARIANTS)
@pytest.mark.parametrize('mutation', COMMON+PAPER)
def test_paper_rows_refuse_false_observations(artifacts, profile, variant, mutation):
    with pytest.raises(ValueError):
        oracle()(**mutate(facts(artifacts, profile, variant), mutation))


@pytest.mark.parametrize('variant,mutation', [(v, m) for v in VARIANTS for m in COMMON+REPAIRED[v]])
def test_repaired_rows_refuse_false_observations(artifacts, variant, mutation):
    with pytest.raises(ValueError):
        oracle()(**mutate(facts(artifacts, 'repaired-e', variant), mutation))
