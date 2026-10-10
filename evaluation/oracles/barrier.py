"""Independent E02 revocation-barrier and expired-duty oracle (SL6) for the paper-derived HMBC reconstruction.

Expectations: frozen rows E02-pre-barrier-revocation-*, E02-post-barrier-revocation-*, E02-expired-duty-*,
SPEC4/E02 and the pinned ledger (933d2a7). Paper ACSC.policyEnf (ACSC.sol:140-167) evaluates the relay's
records without checkpoint or freshness checks and grants (recipient 0, TTL +30 s). Repaired-e
DecisionVerifier (DecisionVerifier.sol:52-96): step 9 request/decision expiry EXPIRED, step 10 checkpoint
fresh and same sequence STALE_STATE, step 11 authEpoch STALE_STATE, step 13 every record valid at now
EXPIRED. A PBC revocation reaches the DBC only through a newly accepted checkpoint: before it the older
certificate is accepted (an intentional, measured window), after it STALE_STATE. A31 is runner
discipline: exactly one collect_decision per request. A1 pre-FREEZE conditions (2026-10-11): the post-
barrier STALE_STATE must be the sequence cause of DV line 87 (new checkpoint current at consumption,
decision not outliving it, steps 9 and 10a passing); the expired-duty EXPIRED must be step 13 (duty end
<= consumption < min(decision, request, checkpoint expiry)); pre-barrier consumes on the unchanged first
checkpoint. Tested reconstruction results, never exploits.
"""
import copy

from evaluation.access_artifacts import require
from evaluation.oracles.provenance import _idle

ZERO = '0x'+'00'*32
PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
VARIANTS = ('pre-barrier-revocation', 'post-barrier-revocation', 'expired-duty')
_NATIVE = ('grants', 'requests', 'accessLogCount', 'nonces', 'logs')


def _native(snapshot):
    return {k: copy.deepcopy(snapshot[k]) for k in _NATIVE}


def _grant_delta(before, after, request, grant, events, relay, *, nonce_consumed):
    g = request['grantId']; digest = request['digest']
    require([e['name'] for e in events] == ['GrantIssued', 'AccessLog'], 'grant then access log')
    issued, logged = events[0]['fields'], events[1]['fields']
    require(issued == dict(grantId=g, requestDigest=digest, gid=request['gid'], dataId=request['dataId'], keyEpoch='0',
                           expiresAt=grant['expiresAt'], recipientKeyHash=grant['recipientKeyHash'], nonceConsumed=nonce_consumed,
                           nonce=request['nonce'] if nonce_consumed else '0'), 'exact GrantIssued')
    require(logged == dict(accessLogId=str(int(before['accessLogCount'])+1), requestRef=digest, gid=request['gid'], dataId=request['dataId'],
                           allowed=True, code='0', credentialDigest=request['credentialDigest'], grantId=g, submitter=relay),
            'exact AccessLog (allowed, request credential digest, relay)')
    expected = _native(before)
    expected['grants'][g] = grant; expected['accessLogCount'] = logged['accessLogId']
    expected['logs']['dbc'] = expected['logs']['dbc']+copy.deepcopy(events)
    if nonce_consumed:
        expected['nonces'] = [[gid, n, True if (gid, n) == (request['gid'], request['nonce']) else used] for gid, n, used in expected['nonces']]
    require(_native(after) == expected, 'only the grant delta')


def check_barrier_row(*, profile, variant, request, decision, checkpoints, revocation, clock, before, after, success, rejection_code,
                      consume_events, consume_timestamp, decision_collections, relay, current_checkpoint):
    """Classify one SL6 row from authenticated snapshots and the mined consumption."""
    require(profile in PROFILES and variant in VARIANTS, 'frozen SL6 row')
    repaired, expired, post = profile == 'repaired-e', variant == 'expired-duty', variant == 'post-barrier-revocation'
    _idle(before['worker'])
    require(before['worker'].get('instantiated') is False and after['worker'] == before['worker'],
            'verified never-instantiated worker, unchanged (no SL6 step is a worker operation)')
    digest, g, ts = request['digest'], request['grantId'], int(consume_timestamp)
    state = before['requests'][digest]
    require(state['status'] == '1' and state['outcomeLogId'] == '0', 'forwarded request before consumption')
    require(before['grants'][g]['exists'] is False and [request['gid'], request['nonce'], False] in before['nonces'], 'no grant, nonce unused')
    require(ts < int(request['expiresAt']), 'consumption strictly before request expiry')
    timing = dict(consumeTimestamp=str(ts), requestExpiresAt=request['expiresAt'])
    # A31 runner discipline and the certificate collected before the PBC update.
    if repaired:
        d = decision['decision']; cp1 = checkpoints[0]
        require(decision_collections == 1, 'exactly one collect_decision for the request (A31)')
        require(d['requestDigest'] == digest and d['result'] == '1' and d['credentialDigest'] == request['credentialDigest']
                and d['stateSequence'] == cp1['sequence'] and cp1['authEpoch'] == request['authEpoch'], 'honest ALLOW on the first checkpoint')
        require(int(decision['collectedDbcNow']) < int(d['expiresAt']), 'decision live when collected')
        require(current_checkpoint == checkpoints[-1], 'the last accepted checkpoint is the one current at consumption')
        require(ts < int(d['expiresAt']) and ts < int(current_checkpoint['expiresAt']),
                'decision and current checkpoint live at consumption (DecisionVerifier steps 9 and 10a pass)')
        timing.update(decisionExpiresAt=d['expiresAt'], checkpointExpiresAt=current_checkpoint['expiresAt'],
                      decisionSequence=d['stateSequence'], currentSequence=current_checkpoint['sequence'])
    else:
        require(decision is None and checkpoints == [] and decision_collections == 0, 'paper profiles have no certificate or checkpoint')
    if expired:
        duty = [r for r in request['records'] if r['kind'] == '2']
        end = int(clock['dutyEnd'])
        require(len(duty) == 1 and int(duty[0]['validUntil']) == end, 'forwarded duty record ends at the duty end')
        timing['dutyEnd'] = clock['dutyEnd']
        require(int(request['timestamp']) < end, 'duty valid at the PBC decision')
        require(int(clock['dbcBefore']) < end <= int(clock['advancedTo']) and ts >= end, 'only the DBC clock moved past the duty end')
        if repaired:
            require(int(decision['collectedDbcNow']) < end, 'decision collected while the duty was valid (A1-0064)')
            require(len(checkpoints) == 1 and ts < min(int(d['expiresAt']), int(request['expiresAt']), int(cp1['expiresAt'])),
                    'duty end <= consumption < min(decision, request, checkpoint expiry): EXPIRED can only be step 13')
    else:
        rv = revocation
        require(rv['success'] is True and rv['before'] == dict(revoked=False, credentialsCode='0', authEpoch=request['authEpoch'])
                and rv['after'] == dict(revoked=True, credentialsCode='19', authEpoch=str(int(request['authEpoch'])+1)),
                'Alice revoked on the PBC (REVOKED 19, authEpoch + 1)')
        require(int(rv['timestamp']) <= ts, 'consumption after the PBC revocation')
        if repaired:
            require(int(decision['collectedPbcBlock']) < int(rv['blockNumber']), 'certificate collected before the PBC update, never re-collected')
            require(int(cp1['sourceBlockNumber']) < int(rv['blockNumber']), 'first checkpoint predates the revocation')
            if post:
                require(len(checkpoints) == 2, 'ACCEPT_CHECKPOINT after the revocation')
                cp2 = checkpoints[1]
                require(cp2['sequence'] == str(int(cp1['sequence'])+1) and cp2['authEpoch'] == rv['after']['authEpoch']
                        and int(cp2['sourceBlockNumber']) >= int(rv['blockNumber']), 'new checkpoint carries the revocation (sequence + 1, new authEpoch)')
                require(d['stateSequence'] == cp1['sequence'] != cp2['sequence'] and int(d['expiresAt']) <= int(cp2['expiresAt']),
                        'DV line 87 sequence cause only: older sequence, decision not outliving the new checkpoint')
            else:
                require(len(checkpoints) == 1, 'no new checkpoint accepted before consumption (REVOKE_ON_PBC before consume)')
    if not repaired:
        require(success is True and rejection_code is None, 'paper policyEnf grants')
        grant = dict(exists=True, allowed=True, requestDigest=digest, dataId=request['dataId'], gid=request['gid'], keyEpoch='0',
                     expiresAt=str(ts+30), recipientKeyHash=ZERO, issuedAt=str(ts))
        _grant_delta(before, after, request, grant, consume_events, relay, nonce_consumed=False)
        return dict(ok=True, classification='SPEC_GAP', error=None, outcome='ACCEPT', delivery='unknown', timing=timing,
                    qualification=('paper DBC grants on request-time records after the PBC revocation; no checkpoint barrier exists'
                                   if not expired else 'paper DBC grants with a duty record already expired at consumption; no record '
                                   'freshness check') + '; configured relay forwards the request-time records; specification gap')
    if variant == 'pre-barrier-revocation':
        require(success is True and rejection_code is None, 'older certificate accepted before the revoking checkpoint')
        grant = dict(exists=True, allowed=True, requestDigest=digest, dataId=request['dataId'], gid=request['gid'], keyEpoch='0',
                     expiresAt=str(min(int(d['expiresAt']), int(request['expiresAt']))), recipientKeyHash=request['recipientKeyHash'],
                     issuedAt=str(ts))
        _grant_delta(before, after, request, grant, consume_events, relay, nonce_consumed=True)
        return dict(ok=True, classification='REPAIR_SUPPORTED', error=None, outcome='ACCEPT', delivery='unknown', timing=timing,
                    windowSeconds=ts-int(revocation['timestamp']),
                    qualification='intentional pre-barrier window: the DBC accepts a previously approved unexpired certificate until it '
                                  'accepts the revoking checkpoint; not instantaneous revocation')
    code = '6' if post else '7'
    require(success is False and rejection_code == code and consume_events == [],
            'mined Rejected('+('STALE_STATE' if post else 'EXPIRED')+') without events')
    require(_native(after) == _native(before), 'no grant, nonce, count or log change')
    cause = dict(staleCause='sequence') if post else dict(expiredStep=13)
    return dict(ok=True, classification='REPAIR_SUPPORTED', error='STALE_STATE' if post else 'EXPIRED', outcome='REJECT', delivery='unknown',
                timing=timing, **cause,
                qualification='older certificate rejected after the revoking checkpoint (DecisionVerifier step 10)' if post else
                'expired duty record rejected at consumption (DecisionVerifier step 13) while request, decision and checkpoint were live')
