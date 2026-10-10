"""Public E03 audit-stress collectors (SL3) for the paper-derived HMBC reconstruction.

Variants follow the frozen catalog steps exactly:
- dropped-outcome (REQUEST_ACCESS > FORWARD_OR_CONSUME > RELEASE > DROP_OUTCOME): the record
  commitments are registered (encrypt_record, which instantiates the worker as RELEASE needs),
  the grant is issued, ONE production release is made strictly before grant expiry, and no
  outcome is reported; the PBC request must stay PENDING (FORWARDED).
- fabricated-outcome (REQUEST_ACCESS > FABRICATE_OUTCOME): the configured relay reports an outcome
  for the logged request with no DBC grant. Repaired-e additionally asks the honest witness to
  attest the (absent) grant, which must be refused (NOT_COMMITTED); no worker operation occurs.
The caller owns fresh deployment/state, controls, plan ACKs and source stability. Configured-relay
stress is outside A01; results are never HMBC exploits.
"""
import copy
from pathlib import Path

from eth_utils import keccak

from evaluation.access_artifacts import require
from evaluation.access_execution import _clock, _commitments, _fingerprint
from evaluation.bootstrap import USERS, frozen_validate, strict_json
from evaluation.manifests import now
from evaluation.oracles.audit import check_dropped_outcome, check_fabricated_outcome
from evaluation.relay_stress import _Context, _baseline
from evaluation.subject_substitution import _decode, _save

PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
VARIANTS = ('dropped-outcome', 'fabricated-outcome')
# Fixed synthetic outcome digest for the fabricated report: reproducible, never a real response.
FABRICATED_OUTCOME = '0x'+keccak(text='HMBC.E03.fabricated-outcome.v1').hex()


def _grant(ctx, req):
    dbc, dep = ctx.dbc, ctx.dep
    if dep['profile'] == 'repaired-e':
        checkpoint = ctx.checkpoint(req['native'].block_number); collected = ctx.decision(req, checkpoint)
        result = collected['result']
        args = [req['request'], {k: copy.deepcopy(result[k]) for k in ('decision', 'signatures')}, result['credentialRecords']]
        method = 'consumeDecision'
    else:
        args = [dict(pbcRequestId=req['digest'], gid=req['request']['gid'], dataId=req['request']['dataId'], action='1'), req['records']]
        method = 'policyEnf'
    native = dbc.submit('relay', 'ACSC', method, *args)
    ctx.mined(dbc, native, 'ACSC', method, args)
    grants = [e['fields'] for e in _decode(dbc, native.receipt['logs']) if e['name'] == 'GrantIssued']
    require(len(grants) == 1 and grants[0]['grantId'] == req['grantId'], 'one allowed grant for the request')
    _save(ctx.output, 'grant-transaction', dict(method=method, arguments=args, transactionHash=native.receipt['transactionHash']))
    return native


def _dropped(ctx, record, policy):
    pbc, dbc, dep, user = ctx.pbc, ctx.dbc, ctx.dep, ctx.user
    policy_digest, ciphertext_digest = _commitments(record, policy)
    encrypted = ctx.provider.call('encrypt_record', dict(record=record, policy=policy, keyEpoch='0'))
    require(encrypted['dataId'] == record['dataId'] and encrypted['policyDigest'] == policy_digest
            and encrypted['ciphertextDigest'] == ciphertext_digest, 'symbolic record commitments')
    req = ctx.request(); granted = _grant(ctx, req)
    gid = user['gid']; keys = dict(grants=[req['grantId']], refs=[req['digest']], nonces=[(gid, '1')])
    before = ctx.snapshot('before-release', **keys)
    grant = before['grants'][req['grantId']]
    paper = dep['profile'] != 'repaired-e'
    registered = pbc.read('RSC', 'recipientKeyHash', gid)[0]
    require(registered == '0x'+keccak(text='HMBC.recipient-key.alice').hex(), 'registered PBC recipient key (A35)')
    require(int(_clock(dbc)) < int(grant['expiresAt']), 'release attempted inside the original grant lifetime')
    response = ctx.provider.call('release', dict(grantId=req['grantId']))
    dbc_now = _clock(dbc)
    after = ctx.snapshot('after-release', **keys)
    timeline = dict(requestTimestamp=req['native'].timestamp, requestExpiresAt=req['request']['expiresAt'],
                    grantTimestamp=granted.timestamp, grantExpiresAt=grant['expiresAt'], releaseDbcClock=dbc_now,
                    marginSeconds=int(grant['expiresAt'])-int(dbc_now), recipientSource='RSC registered key (D35/A38)' if paper
                    else 'signed request recipient in the grant')
    _save(ctx.output, 'timeline', timeline)
    proof = check_dropped_outcome(profile=dep['profile'], before=before, after=after, request_digest=req['digest'], grant_id=req['grantId'],
                                  gid=gid, data_id=record['dataId'], expected_recipient=registered, ciphertext_digest=ciphertext_digest,
                                  response=response, dbc_now=dbc_now, fingerprint=_fingerprint(dep))
    return dict(proof, timeline=timeline)


def _fabricated(ctx):
    pbc, dep, user = ctx.pbc, ctx.dep, ctx.user
    gid = user['gid']
    req = ctx.request()
    keys = dict(grants=[req['grantId']], refs=[req['digest']], nonces=[(gid, '1')])
    args = [req['digest'], req['grantId'], FABRICATED_OUTCOME]
    _save(ctx.output, 'public-call', dict(method='reportOutcome', arguments=args))
    before = ctx.snapshot('before', **keys)
    repaired = dep['profile'] == 'repaired-e'
    native = pbc.submit('relay', 'PSC', 'reportOutcome', *args, expect_success=not repaired)
    _save(ctx.output, 'stress-transaction', ctx.mined(pbc, native, 'PSC', 'reportOutcome', args))
    code = pbc.rejection_code(native) if repaired else None
    events = _decode(pbc, native.receipt['logs'])
    attestation = None
    if repaired:
        answer = ctx.provider.response('attest_grant', dict(grantId=req['grantId']))
        attestation = dict(ok=answer['ok'], error=None if answer['ok'] else answer['error']['code'])
        _save(ctx.output, 'attestation', attestation)
    after = ctx.snapshot('after', **keys)
    timeline = dict(requestTimestamp=req['native'].timestamp, requestExpiresAt=req['request']['expiresAt'], stressTimestamp=native.timestamp)
    _save(ctx.output, 'timeline', timeline)
    proof = check_fabricated_outcome(profile=dep['profile'], before=before, after=after, request_digest=req['digest'],
                                     grant_id=req['grantId'], outcome_digest=FABRICATED_OUTCOME, relay=ctx.relay, success=native.success,
                                     rejection_code=code, receipt_events=events, attestation=attestation)
    return dict(proof, timeline=timeline)


def execute_audit_stress(pbc, dbc, adapter, *, deployment_bytes, user_label, user, record, policy, variant, worker_snapshot, output):
    """Run one frozen SL3 audit-stress row on a fresh deployment."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None, variant=variant, delivery='unknown',
                  scope='C-E2 SL3 audit stress; separate controls, plan ACKs and gate apply')
    try:
        dep = strict_json(deployment_bytes); frozen_validate('LedgerDeployment', dep)
        require(variant in VARIANTS and dep['profile'] in PROFILES, 'frozen catalog variant/profile')
        require(dep['interfaceVersion'] == 'v1' and dep['mutations'] == '0', 'baseline deployment')
        require(user_label == 'alice' and user['gid'] == USERS['alice'], 'registered Alice stress subject')
        frozen_validate('CredentialBundle', user['bundle'])
        _baseline(pbc, dbc, dep, user, record, policy)
        ctx = _Context(pbc, dbc, adapter, dep, user, record, worker_snapshot, output)
        proof = _dropped(ctx, record, policy) if variant == 'dropped-outcome' else _fabricated(ctx)
        result.update(proof)
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); _save(output, 'result', result)
