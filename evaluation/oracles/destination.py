"""Independent E01 wrong-destination and expiry-boundary oracles (SL7) for the paper-derived HMBC reconstruction.

Expectations: frozen rows E01-wrong-destination-* and E01-expiry-boundary-*, SPEC4/E01 and the pinned
ledger (933d2a7). Repaired-e DecisionVerifier: step 1 (line 60) rejects a request whose source chain/PSC is
not this deployment's, step 2 (lines 61-64) one whose destination chain/KSSC is not this deployment's, both
WRONG_DESTINATION; step 9 (line 74) rejects now >= decision or request expiry, EXPIRED. Paper
ACSC.policyEnf (ACSC.sol:140-167) receives neither the destination binding nor the signed request expiry and
fills the grant expiry as block + grantTtl (line 154). A1 pre-FREEZE conditions (2026-10-11 ~13:20 IST): the
firing step is recorded; this row cannot kill MUT_NO_DESTINATION_BINDING (step 1 still fires); the boundary
consumption is exactly at the request expiry with the decision expiry equal to it and the checkpoint above
it. Compromised-relay stress is outside A01: paper results are specification gaps, never HMBC exploits.
"""
import copy

from evaluation.access_artifacts import require
from evaluation.oracles.provenance import _idle

ZERO = '0x'+'00'*32
PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
_NATIVE = ('grants', 'requests', 'accessLogCount', 'nonces', 'logs')


def _native(snapshot):
    return {k: copy.deepcopy(snapshot[k]) for k in _NATIVE}


def _workers(*pairs):
    for before, after in pairs:
        _idle(before['worker'])
        require(before['worker'].get('instantiated') is False and after['worker'] == before['worker'],
                'verified never-instantiated worker, unchanged (no SL7 step is a worker operation)')


def _paper_grant(before, after, *, digest, grant_id, request, ts, events, relay):
    require([e['name'] for e in events] == ['GrantIssued', 'AccessLog'], 'grant then access log')
    issued, logged = events[0]['fields'], events[1]['fields']
    require(issued == dict(grantId=grant_id, requestDigest=digest, gid=request['gid'], dataId=request['dataId'], keyEpoch='0',
                           expiresAt=str(ts+30), recipientKeyHash=ZERO, nonceConsumed=False, nonce='0'),
            'paper GrantIssued: relay reference, recipient 0, expiry block + grantTtl (ACSC.sol:154), no nonce')
    require(logged == dict(accessLogId=str(int(before['accessLogCount'])+1), requestRef=digest, gid=request['gid'], dataId=request['dataId'],
                           allowed=True, code='0', credentialDigest=request['credentialDigest'], grantId=grant_id, submitter=relay),
            'paper AccessLog: allowed, request credential digest, relay submitter')
    expected = _native(before)
    expected['grants'][grant_id] = dict(exists=True, allowed=True, requestDigest=digest, dataId=request['dataId'], gid=request['gid'],
                                        keyEpoch='0', expiresAt=str(ts+30), recipientKeyHash=ZERO, issuedAt=str(ts))
    expected['accessLogCount'] = logged['accessLogId']; expected['logs']['dbc'] = expected['logs']['dbc']+copy.deepcopy(events)
    require(_native(after) == expected, 'only the paper grant delta')


def _decision(decision, checkpoint, request, collections):
    d = decision['decision']
    require(collections == 1, 'exactly one collect_decision for the request (A31)')
    require(d['requestDigest'] == request['digest'] and d['result'] == '1' and d['credentialDigest'] == request['credentialDigest']
            and d['stateSequence'] == checkpoint['sequence'], 'honest ALLOW certificate on the current checkpoint')
    require(int(decision['collectedDbcNow']) < int(d['expiresAt']), 'decision live when collected')
    return d


def check_wrong_destination(*, profile, request, receiver, source, grant_id_a, grant_id_b, before_a, after_a, before_b, after_b,
                            decision, checkpoint, success, rejection_code, consume_events, consume_timestamp, decision_collections, relay):
    """B's valid request/certificate submitted at A without rewriting its signed fields."""
    require(profile in PROFILES, 'E reconstruction profile')
    _workers((before_a, after_a), (before_b, after_b))
    fields = ('sourceChainId', 'psc', 'destinationChainId', 'kssc')
    require([request[k] for k in fields] == [source['pbcChainId'], source['psc'], source['dbcChainId'], source['kssc']],
            'the request is a valid request for deployment B')
    require(source['psc'] != receiver['psc'] and source['kssc'] != receiver['kssc'], 'B is a different deployment than the receiver A')
    step1 = request['sourceChainId'] != receiver['pbcChainId'] or request['psc'] != receiver['psc']
    step2 = request['destinationChainId'] != receiver['dbcChainId'] or request['kssc'] != receiver['kssc']
    require(step1, 'DecisionVerifier step 1 (line 60) mismatch: B source chain/PSC is not A')
    digest = request['digest']
    require(before_a['requests'][digest]['status'] == '0' and after_a['requests'][digest]['status'] == '0', 'A PBC has no such request')
    require(before_a['grants'][grant_id_a]['exists'] is False, 'no grant at A before')
    require(before_b['requests'][digest]['status'] == '1' and before_b['grants'][grant_id_b]['exists'] is False
            and _native(after_b) == _native(before_b), 'source deployment B untouched: request forwarded, no grant, nonce unchanged')
    ts = int(consume_timestamp)
    require(ts < int(request['expiresAt']), 'submission before the request expiry')
    if profile == 'repaired-e':
        _decision(decision, checkpoint, request, decision_collections)
        require(success is False and rejection_code == '3' and consume_events == [], 'mined Rejected(WRONG_DESTINATION) without events')
        require(_native(after_a) == _native(before_a), 'no grant, nonce, count or log change at A')
        return dict(ok=True, classification='REPAIR_SUPPORTED', error='WRONG_DESTINATION', outcome='REJECT', delivery='unknown',
                    firingStep=1, step2Mismatch=step2, killsNoDestinationBindingMutant=False,
                    qualification='receiver rejects at DecisionVerifier step 1 (source chain/PSC) before grant state; step 2 (destination '
                                  'KSSC) also mismatches; this row cannot kill MUT_NO_DESTINATION_BINDING because step 1 still fires')
    require(decision is None and checkpoint is None and decision_collections == 0, 'paper profiles have no certificate')
    require(success is True and rejection_code is None, 'paper policyEnf at A grants')
    _paper_grant(before_a, after_a, digest=digest, grant_id=grant_id_a, request=request, ts=ts, events=consume_events, relay=relay)
    return dict(ok=True, classification='SPEC_GAP', error=None, outcome='ACCEPT', delivery='unknown', receiverHasRequest=False,
                qualification='chosen completion under compromised-relay stress: A grants on B\'s forwarded tuple and records although A\'s '
                              'PBC has no such request (forwarded tuples omit the destination binding); specification gap, not an exploit')


def check_expiry_boundary(*, profile, request, grant_id, before, after, decision, checkpoint, clock, success, rejection_code,
                          consume_events, consume_timestamp, decision_collections, relay):
    """Consumption mined exactly at the signed request expiry (DBC clock pinned)."""
    require(profile in PROFILES, 'E reconstruction profile')
    _workers((before, after))
    digest, e, ts = request['digest'], int(request['expiresAt']), int(consume_timestamp)
    require(before['requests'][digest]['status'] == '1' and before['grants'][grant_id]['exists'] is False, 'forwarded request, no grant')
    require(int(clock['dbcBefore']) < e and int(clock['target']) == e and ts == e,
            'DBC-only clock pinned: the consumption block timestamp equals request expiresAt exactly')
    timing = dict(consumeTimestamp=str(ts), requestExpiresAt=request['expiresAt'])
    if profile == 'repaired-e':
        d = _decision(decision, checkpoint, request, decision_collections)
        require(int(d['expiresAt']) == e and int(checkpoint['expiresAt']) > e,
                'd.expiresAt == r.expiresAt and cp.expiresAt > r.expiresAt (neither checkpoint nor DBC-now cap is lower)')
        require(success is False and rejection_code == '7' and consume_events == [], 'mined Rejected(EXPIRED) without events')
        require(_native(after) == _native(before), 'no grant, nonce, count or log change')
        timing.update(decisionExpiresAt=d['expiresAt'], checkpointExpiresAt=checkpoint['expiresAt'])
        return dict(ok=True, classification='REPAIR_SUPPORTED', error='EXPIRED', outcome='REJECT', delivery='unknown', firingStep=9,
                    timing=timing, qualification='DecisionVerifier step 9 (line 74) uses >=, so a consumption exactly at the request '
                                                 'expiry is rejected; tested reconstruction result')
    require(decision is None and checkpoint is None and decision_collections == 0, 'paper profiles have no certificate')
    require(success is True and rejection_code is None, 'paper policyEnf grants at the request expiry')
    _paper_grant(before, after, digest=digest, grant_id=grant_id, request=request, ts=ts, events=consume_events, relay=relay)
    timing['grantExpiresAt'] = str(ts+30)
    return dict(ok=True, classification='SPEC_GAP', error=None, outcome='ACCEPT', delivery='unknown', timing=timing,
                qualification='forwarded paper tuples omit the signed request expiry: the DBC grants at DBC time == request expiresAt and '
                              'fills the grant expiry as block + grantTtl (30 s); specification gap')
