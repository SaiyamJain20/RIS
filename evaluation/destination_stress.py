"""Public E01 wrong-destination and expiry-boundary collectors (SL7) for the paper-derived HMBC reconstruction.

Variants follow the frozen catalog steps exactly:
- wrong-destination (REQUEST_ACCESS > SUBSTITUTE_DESTINATION > FORWARD_OR_CONSUME): Alice's request is made
  on a second deployment B (same chain pair and chain ids, other contract addresses; A1-0039) and, in
  repaired-e, B's checkpoint and ONE decision are collected through B's adapter. B's request, certificate
  and records are then submitted at the receiving deployment A without rewriting any signed field:
  repaired consumeDecision (expected WRONG_DESTINATION at DecisionVerifier step 1) or paper policyEnf with
  B's forwarded tuple and records (a chosen completion under compromised-relay stress).
- expiry-boundary (REQUEST_ACCESS > ADVANCE_CLOCK > FORWARD_OR_CONSUME): after the request (and, repaired,
  checkpoint and decision), the DBC clock alone is pinned with evm_setNextBlockTimestamp(r.expiresAt), no
  evm_mine, so the consumption is the next mined block exactly at the request expiry; the mined time is
  verified, not assumed.
No step is a worker operation, so every deployment's worker must stay a verified never-instantiated
record after every catalog step (D49). The caller owns fresh deployments and state, controls, plan ACKs
and source stability. Tested reconstruction results, never HMBC exploits.
"""
import copy
from pathlib import Path

from evaluation.access_artifacts import require
from evaluation.bootstrap import USERS, frozen_validate, strict_json
from evaluation.manifests import now
from evaluation.native import _quantity
from evaluation.oracles.destination import check_expiry_boundary, check_wrong_destination
from evaluation.oracles.provenance import _idle
from evaluation.relay_stress import _Context, _baseline, _grant_id
from evaluation.subject_substitution import _decode, _save

VARIANTS = ('wrong-destination', 'expiry-boundary')
PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')


class _Steps:
    """D49 precondition for every deployment of the row, re-observed after every catalog step."""

    def __init__(self, contexts):
        self.contexts, self.first, self.rows = contexts, {}, []

    def check(self, step, observed=None):
        observed = observed or {}
        for name, ctx in self.contexts.items():
            seen = observed.get(name) or ctx.worker()
            _idle(seen)
            require(seen['instantiated'] is False and self.first.setdefault(name, copy.deepcopy(seen)) == seen,
                    'verified never-instantiated worker ('+name+') after '+step)
        self.rows.append(dict(step=step, worker='never-instantiated (verified)', deployments=sorted(self.contexts)))


def _binding(chain_pbc, chain_dbc):
    return dict(pbcChainId=chain_pbc.chain_id, psc=chain_pbc.contracts['PSC'].address, dbcChainId=chain_dbc.chain_id,
                kssc=chain_dbc.contracts['KSSC'].address)


def _decisions(*contexts):
    return sum(1 for ctx in contexts for row in ctx.provider.exchanges if row['operation'] == 'collect_decision')


def _certificate(ctx, req):
    checkpoint = ctx.checkpoint(req['native'].block_number); collected = ctx.decision(req, checkpoint)
    return checkpoint, collected, dict(decision=collected['result']['decision'], collectedDbcNow=collected['dbcNow'])


def _oracle_request(req, credential_digest):
    r = req['request']
    return dict(digest=req['digest'], sourceChainId=r['sourceChainId'], psc=r['psc'], destinationChainId=r['destinationChainId'],
                kssc=r['kssc'], gid=r['gid'], dataId=r['dataId'], nonce=r['nonce'], expiresAt=r['expiresAt'],
                credentialDigest=credential_digest, timestamp=req['native'].timestamp)


def _consume(ctx, req, collected, repaired, *, expect_success):
    dbc = ctx.dbc
    if repaired:
        result = collected['result']
        args = [req['request'], {k: copy.deepcopy(result[k]) for k in ('decision', 'signatures')}, result['credentialRecords']]
        method = 'consumeDecision'
    else:
        args = [dict(pbcRequestId=req['digest'], gid=req['request']['gid'], dataId=req['request']['dataId'], action='1'), req['records']]
        method = 'policyEnf'
    _save(ctx.output, 'public-call', dict(method=method, arguments=args, signedFieldsRewritten=False))
    native = dbc.submit('relay', 'ACSC', method, *args, expect_success=expect_success)
    _save(ctx.output, 'stress-transaction', ctx.mined(dbc, native, 'ACSC', method, args))
    return native, (None if native.success else dbc.rejection_code(native))


def _wrong_destination(a, b):
    repaired = a.dep['profile'] == 'repaired-e'
    steps = _Steps(dict(A=a, B=b)); steps.check('baseline')
    req = b.request()
    checkpoint = collected = decision = None
    if repaired:
        checkpoint, collected, decision = _certificate(b, req)
    steps.check('REQUEST_ACCESS')
    receiver, source = _binding(a.pbc, a.dbc), _binding(b.pbc, b.dbc)
    grant_a, grant_b = _grant_id(a.dep, req['digest']), req['grantId']
    _save(a.output, 'substitution', dict(request={k: req['request'][k] for k in ('sourceChainId', 'psc', 'destinationChainId', 'kssc', 'gid',
                                                                                'dataId', 'nonce', 'expiresAt')},
                                         requestDigest=req['digest'], receiver=receiver, source=source, receiverGrantId=grant_a,
                                         sourceGrantId=grant_b, signedFieldsRewritten=False,
                                         note='SUBSTITUTE_DESTINATION: B\'s signed request/certificate/records submitted at A unchanged'))
    steps.check('SUBSTITUTE_DESTINATION')
    gid = a.user['gid']
    before_a = a.snapshot('before', grants=[grant_a], refs=[req['digest']], nonces=[(gid, '1')])
    before_b = b.snapshot('before', grants=[grant_b], refs=[req['digest']], nonces=[(gid, '1')])
    native, code = _consume(a, req, collected, repaired, expect_success=not repaired)
    events = _decode(a.dbc, native.receipt['logs'])
    after_a = a.snapshot('after', grants=[grant_a], refs=[req['digest']], nonces=[(gid, '1')])
    after_b = b.snapshot('after', grants=[grant_b], refs=[req['digest']], nonces=[(gid, '1')])
    steps.check('FORWARD_OR_CONSUME', dict(A=after_a['worker'], B=after_b['worker']))
    request = _oracle_request(req, before_b['requests'][req['digest']]['credentialDigest'])
    timeline = dict(requestTimestamp=request['timestamp'], requestExpiresAt=request['expiresAt'], consumeTimestamp=native.timestamp,
                    decisionExpiresAt=decision['decision']['expiresAt'] if decision else None)
    _save(a.output, 'timeline', timeline)
    collections = _decisions(a, b)
    proof = check_wrong_destination(profile=a.dep['profile'], request=request, receiver=receiver, source=source, grant_id_a=grant_a,
                                    grant_id_b=grant_b, before_a=before_a, after_a=after_a, before_b=before_b, after_b=after_b,
                                    decision=decision, checkpoint=checkpoint, success=native.success, rejection_code=code,
                                    consume_events=events, consume_timestamp=native.timestamp, decision_collections=collections,
                                    relay=a.relay)
    return dict(proof, workerSteps=steps.rows, timeline=timeline, decisionCollections=collections, receiver=receiver, source=source)


def _expiry_boundary(a):
    pbc, dbc = a.pbc, a.dbc; repaired = a.dep['profile'] == 'repaired-e'
    steps = _Steps(dict(A=a)); steps.check('baseline')
    req = a.request()
    checkpoint = collected = decision = None
    if repaired:
        checkpoint, collected, decision = _certificate(a, req)
    steps.check('REQUEST_ACCESS')
    gid = a.user['gid']; keys = dict(grants=[req['grantId']], refs=[req['digest']], nonces=[(gid, '1')])
    before = a.snapshot('before', **keys)
    expires = int(req['request']['expiresAt']); latest = int(_quantity(dbc.latest_block()['timestamp']))
    require(latest < expires, 'DBC clock below the request expiry before ADVANCE_CLOCK')
    dbc.rpc.call('evm_setNextBlockTimestamp', [expires])     # DBC only; no evm_mine: the consumption is the next mined block
    clock = dict(dbcBefore=str(latest), target=str(expires), note='ADVANCE_CLOCK: evm_setNextBlockTimestamp(r.expiresAt) on the DBC only')
    steps.check('ADVANCE_CLOCK')
    native, code = _consume(a, req, collected, repaired, expect_success=not repaired)
    events = _decode(dbc, native.receipt['logs'])
    after = a.snapshot('after', **keys)
    steps.check('FORWARD_OR_CONSUME', dict(A=after['worker']))
    request = _oracle_request(req, before['requests'][req['digest']]['credentialDigest'])
    timeline = dict(requestTimestamp=request['timestamp'], requestExpiresAt=request['expiresAt'], consumeTimestamp=native.timestamp,
                    dbcBefore=clock['dbcBefore'], decisionExpiresAt=decision['decision']['expiresAt'] if decision else None,
                    checkpointExpiresAt=checkpoint['expiresAt'] if checkpoint else None)
    _save(a.output, 'timeline', timeline)
    collections = _decisions(a)
    proof = check_expiry_boundary(profile=a.dep['profile'], request=request, grant_id=req['grantId'], before=before, after=after,
                                  decision=decision, checkpoint=checkpoint, clock=clock, success=native.success, rejection_code=code,
                                  consume_events=events, consume_timestamp=native.timestamp, decision_collections=collections,
                                  relay=a.relay)
    return dict(proof, workerSteps=steps.rows, timeline=timeline, decisionCollections=collections, clock=clock)


def execute_destination_stress(pbc, dbc, adapter, *, deployment_bytes, user_label, user, record, policy, variant, worker_snapshot,
                               source, output):
    """Run one frozen SL7 row on fresh deployment(s)."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None, variant=variant, delivery='unknown',
                  scope='C-E2 SL7 wrong destination and expiry boundary; separate controls, plan ACKs and gate apply')
    try:
        dep = strict_json(deployment_bytes); frozen_validate('LedgerDeployment', dep)
        require(variant in VARIANTS and dep['profile'] in PROFILES, 'frozen catalog variant/profile')
        require(dep['interfaceVersion'] == 'v1' and dep['mutations'] == '0', 'baseline deployment')
        require((source is not None) == (variant == 'wrong-destination'), 'a source deployment B exactly for wrong destination')
        require(user_label == 'alice' and user['gid'] == USERS['alice'], 'registered Alice subject')
        frozen_validate('CredentialBundle', user['bundle'])
        if source is not None:
            src = strict_json(source['deployment_bytes']); frozen_validate('LedgerDeployment', src)
            require(src['interfaceVersion'] == 'v1' and src['profile'] == dep['profile'] and src['mutations'] == '0'
                    and source['user']['gid'] == user['gid'], 'source deployment B baseline')
            require(all(src['chains'][n]['chainId'] == dep['chains'][n]['chainId'] for n in ('pbc', 'dbc'))
                    and all(not set(src['chains'][n]['contracts'].values()) & set(dep['chains'][n]['contracts'].values()) for n in ('pbc', 'dbc')),
                    'B is a second deployment on the same chain pair (same chain ids, other contract addresses)')
        _baseline(pbc, dbc, dep, user, record, policy)
        a = _Context(pbc, dbc, adapter, dep, user, record, worker_snapshot, output)
        if source is not None:
            _baseline(source['pbc'], source['dbc'], src, source['user'], record, policy)
            (output/'source').mkdir()
            b = _Context(source['pbc'], source['dbc'], source['adapter'], src, source['user'], record, source['worker_snapshot'], output/'source')
            result.update(_wrong_destination(a, b))
        else:
            result.update(_expiry_boundary(a))
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); _save(output, 'result', result)
