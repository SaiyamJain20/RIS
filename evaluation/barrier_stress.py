"""Public E02 revocation-barrier and expired-duty collectors (SL6) for the paper-derived HMBC reconstruction.

Variants follow the frozen catalog steps exactly, on a fresh second deployment (D2):
- pre-barrier-revocation (REQUEST_ACCESS > REVOKE_ON_PBC > FORWARD_OR_CONSUME): the owner producer signs
  H1 CRL v2 revoking Alice's serial 101 before the row (read-only signing; the catalog step is the
  install). Repaired-e collects the checkpoint and the ONE decision before the PBC update (A1-0064, A31).
  Then the H1 CA-admin installs the CRL and the relay consumes (repaired) or forwards (paper) with the
  pre-collected inputs.
- post-barrier-revocation: the same plus, repaired-e only, ACCEPT_CHECKPOINT (collect_checkpoint and
  acceptState after the revocation) before consuming the older certificate. Paper profiles have no
  checkpoint barrier: ACCEPT_CHECKPOINT is omitted.
- expired-duty (REQUEST_ACCESS > ADVANCE_CLOCK > FORWARD_OR_CONSUME): setup installs an H1 TempACL v2
  whose Alice OnDuty window ends inside the request lifetime; repaired-e collects the decision while the
  duty is valid; ADVANCE_CLOCK moves only the DBC (evm_setNextBlockTimestamp + evm_mine) to the duty end.
No step is a worker operation, so the D2 worker must stay a verified never-instantiated record after
every catalog step (D49). A non-zero producer exit is a failed trial. The caller owns fresh deployment
and state, controls, plan ACKs and source stability. Tested reconstruction results, never exploits.
"""
import copy
import hashlib
from pathlib import Path

from evaluation.access_artifacts import require
from evaluation.access_execution import _block, _clock
from evaluation.audit_stress import _grant
from evaluation.bootstrap import USERS, frozen_validate, signed_digest, strict_json
from evaluation.manifests import now
from evaluation.native import _quantity
from evaluation.oracles.barrier import check_barrier_row
from evaluation.relay_stress import _Context, _baseline
from evaluation.subject_substitution import _decode, _save
from evaluation.trust_stress import SERIAL, _authority, _mined, _Steps

VARIANTS = ('pre-barrier-revocation', 'post-barrier-revocation', 'expired-duty')
PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
DUTY_MARGIN = 25          # seconds from the producer's PBC clock to the duty end (bounded 25..600 in e1)


def _produce(ctx, sign_list, purpose, deployment_bytes, until_in=None):
    pbc, dep = ctx.pbc, ctx.dep
    answer = sign_list(purpose, until_in)
    require(isinstance(answer, dict) and set(answer) == {'exitCode', 'output'} and type(answer['exitCode']) is int
            and isinstance(answer['output'], bytes), 'signed-list producer command record')
    digest = hashlib.sha256(answer['output']).hexdigest()
    if answer['exitCode'] != 0:
        first = answer['output'].split(b'\n', 1)[0].decode('utf-8', 'replace')[:240]
        _save(ctx.output, 'sign-list-refusal', dict(exitCode=answer['exitCode'], outputSha256=digest, firstLine=first,
                                                    note='failed trial: non-zero producer exit; output kept only as sha256 and first line'))
        raise ValueError('Owner signed-list producer exited '+str(answer['exitCode'])+' (failed trial; output sha256 '+digest+')')
    doc = strict_json(answer['output']); h1 = _authority(dep, 'H1'); p = dep['chains']['pbc']
    crl = purpose == 'revoke-alice'
    require(isinstance(doc, dict) and set(doc) == {'schemaVersion', 'producer', 'testOnly', 'binding', 'item'}
            and doc['schemaVersion'] == 'hmbc-ledger-signed-list/v0' and doc['testOnly'] is True, 'TEST-ONLY signed-list artifact')
    b = doc['binding']
    require(b.get('pbcChainId') == pbc.chain_id == p['chainId'] and b.get('tmsc') == p['contracts']['TMSC'] and b.get('rsc') == p['contracts']['RSC']
            and b.get('deploymentSha256') == hashlib.sha256(deployment_bytes).hexdigest() and b.get('profile') == dep['profileEnum'],
            'producer bound to this deployment')
    item = doc['item']; body = item['list']
    kind, call, state = (('RevocationList', 'TMSC.updateRevocationList', 'revocationListState') if crl
                         else ('TemporalAcl', 'TMSC.updateTemporalAcl', 'temporalAclState'))
    require(set(item) == {'kind', 'call', 'submitterRole', 'submitter', 'list', 'signature', 'signer'} and item['kind'] == kind
            and item['call'] == call and item['submitterRole'] == 'H1-ca-admin' and item['submitter'] == h1['caAdmins'][0]
            and item['signer'] == h1['root'] and body['authority'] == h1['root'], 'producer item for the plan purpose')
    current = pbc.read('TMSC', state, h1['root'])[0]
    require(current['published'] is True and body['version'] == str(int(current['version'])+1), 'producer default next version')
    if crl:
        require(body['revokedSerials'] == [SERIAL], 'CRL revokes Alice serial 101 only')
    else:
        t = int(b['blockTimestamp'])
        require(len(body['entries']) == 1 and body['entries'][0]['gid'] == ctx.user['gid']
                and int(body['entries'][0]['validFrom']) == t-60 and int(body['entries'][0]['validUntil']) == t+int(until_in),
                'TempACL: one Alice OnDuty window [t-60, t+untilIn]')
    listed = signed_digest(kind, body, item['signature'], h1['root'], p['chainId'], p['contracts']['TMSC'])
    _save(ctx.output, 'signed-list', dict(doc, outputSha256=digest, contentDigest=listed, purpose=purpose,
                                          label='TEST-ONLY owner producer output (A1-0034); no key material'))
    return item


def _trust_view(ctx):
    pbc, user = ctx.pbc, ctx.user
    h1 = _authority(ctx.dep, 'H1')['root']; block = pbc.latest_block()
    code, _ = pbc.read('TMSC', 'checkCredentials', user['gid'], user['bundle'], str(_quantity(block['timestamp'])), block=block)
    return dict(revoked=pbc.read('TMSC', 'isRevoked', h1, SERIAL, block=block)[0], credentialsCode=code,
                authEpoch=pbc.read('TMSC', 'authEpoch', block=block)[0])


def _install(ctx, item, label):
    pbc = ctx.pbc; h1 = _authority(ctx.dep, 'H1')
    method = 'updateRevocationList' if item['kind'] == 'RevocationList' else 'updateTemporalAcl'
    args = [item['list'], item['signature']]
    native = pbc.submit('H1-ca-admin', 'TMSC', method, *args)
    _save(ctx.output, label, _mined(ctx, pbc, native, h1['caAdmins'][0], 'TMSC', method, args))
    require(native.success is True, 'owner list installed')
    return native


def _decisions(ctx):
    return sum(1 for row in ctx.provider.exchanges if row['operation'] == 'collect_decision')


def _row(ctx, variant, sign_list, deployment_bytes):
    pbc, dbc, dep, user = ctx.pbc, ctx.dbc, ctx.dep, ctx.user
    repaired = dep['profile'] == 'repaired-e'; expired = variant == 'expired-duty'
    steps = _Steps(ctx); steps.check('baseline')
    clock = revocation = None; checkpoints = []; decision = None; collected = None
    if expired:
        latest = int(_quantity(pbc.latest_block()['timestamp'])); pending = int(_clock(pbc))
        until_in = str(max(0, pending-latest)+DUTY_MARGIN)
        duty = _produce(ctx, sign_list, 'short-duty', deployment_bytes, until_in)
        _install(ctx, duty, 'duty-transaction')
        steps.check('INSTALL_SHORT_DUTY')
        duty_end = int(duty['list']['entries'][0]['validUntil'])
    else:
        crl = _produce(ctx, sign_list, 'revoke-alice', deployment_bytes)
    req = ctx.request()
    if repaired:
        cp1 = ctx.checkpoint(req['native'].block_number); checkpoints.append(cp1)
        collected = ctx.decision(req, cp1)
        decision = dict(decision=collected['result']['decision'], collectedDbcNow=collected['dbcNow'],
                        collectedPbcBlock=str(_quantity(pbc.latest_block()['number'])))
    steps.check('REQUEST_ACCESS')
    keys = dict(grants=[req['grantId']], refs=[req['digest']], nonces=[(user['gid'], '1')])
    if not expired:
        before_view = _trust_view(ctx)
        installed = _install(ctx, crl, 'revocation-transaction')
        revocation = dict(timestamp=installed.timestamp, blockNumber=str(installed.block_number), success=installed.success,
                          before=before_view, after=_trust_view(ctx))
        steps.check('REVOKE_ON_PBC')
        if repaired and variant == 'post-barrier-revocation':
            checkpoints.append(ctx.checkpoint(req['native'].block_number))
            steps.check('ACCEPT_CHECKPOINT')
        before = ctx.snapshot('before', **keys)
    else:
        before = ctx.snapshot('before', **keys)
        dbc_before = int(_clock(dbc)); target = max(int(_quantity(dbc.latest_block()['timestamp']))+1, duty_end)
        dbc.rpc.call('evm_setNextBlockTimestamp', [target]); dbc.rpc.call('evm_mine')
        clock = dict(dutyEnd=str(duty_end), dbcBefore=str(dbc_before), advancedTo=str(int(_quantity(dbc.latest_block()['timestamp']))),
                     note='ADVANCE_CLOCK: only the DBC clock moved (A1-0039)')
        steps.check('ADVANCE_CLOCK')
    current = None
    if repaired:   # A1: the checkpoint current at consumption (first one for pre/expired, the post-revocation one for post)
        exists, current = dbc.read('KSSC', 'currentCheckpoint')
        require(exists is True, 'a DBC checkpoint is current at consumption')
    forwarded = dict(pbcRequestId=req['digest'], gid=req['request']['gid'], dataId=req['request']['dataId'], action='1')
    if repaired:
        result = collected['result']
        args = [req['request'], {k: copy.deepcopy(result[k]) for k in ('decision', 'signatures')}, result['credentialRecords']]
        method, expect = 'consumeDecision', variant == 'pre-barrier-revocation'
    else:
        args = [forwarded, req['records']]; method, expect = 'policyEnf', True
    _save(ctx.output, 'public-call', dict(method=method, arguments=args))
    native = dbc.submit('relay', 'ACSC', method, *args, expect_success=expect)
    _save(ctx.output, 'stress-transaction', ctx.mined(dbc, native, 'ACSC', method, args))
    code = None if native.success else dbc.rejection_code(native)
    events = _decode(dbc, native.receipt['logs'])
    after = ctx.snapshot('after', **keys)
    steps.check('FORWARD_OR_CONSUME', after['worker'])
    request = dict(digest=req['digest'], grantId=req['grantId'], gid=user['gid'], dataId=req['request']['dataId'], nonce='1',
                   recipientKeyHash=req['request']['recipientKeyHash'], timestamp=req['native'].timestamp, expiresAt=req['request']['expiresAt'],
                   authEpoch=req['request']['authEpoch'], records=req['records'], credentialDigest=before['requests'][req['digest']]['credentialDigest'],
                   pbcBlockNumber=str(req['native'].block_number))
    timeline = dict(requestTimestamp=request['timestamp'], requestExpiresAt=request['expiresAt'], consumeTimestamp=native.timestamp,
                    revocationTimestamp=revocation['timestamp'] if revocation else None, dutyEnd=clock['dutyEnd'] if clock else None,
                    decisionExpiresAt=decision['decision']['expiresAt'] if decision else None,
                    checkpointExpiresAt=[c['expiresAt'] for c in checkpoints])
    _save(ctx.output, 'timeline', timeline)
    facts = dict(request=request, decision=decision, checkpoints=checkpoints, revocation=revocation, clock=clock, current_checkpoint=current)
    _save(ctx.output, 'facts', facts)
    proof = check_barrier_row(profile=dep['profile'], variant=variant, before=before, after=after, success=native.success, rejection_code=code,
                              consume_events=events, consume_timestamp=native.timestamp, decision_collections=_decisions(ctx), relay=ctx.relay,
                              **facts)
    return dict(proof, workerSteps=steps.rows, timeline=timeline, decisionCollections=_decisions(ctx))


def execute_barrier_stress(pbc, dbc, adapter, *, deployment_bytes, bootstrap, user_label, user, record, policy, variant,
                           worker_snapshot, sign_list, output):
    """Run one frozen SL6 row on a fresh deployment."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None, variant=variant, delivery='unknown',
                  scope='C-E2 SL6 revocation barrier and expired duty; separate controls, plan ACKs and gate apply')
    try:
        dep = strict_json(deployment_bytes); frozen_validate('LedgerDeployment', dep)
        require(variant in VARIANTS and dep['profile'] in PROFILES, 'frozen catalog variant/profile')
        require(dep['interfaceVersion'] == 'v1' and dep['mutations'] == '0', 'baseline deployment')
        require(user_label == 'alice' and user['gid'] == USERS['alice'], 'registered Alice subject')
        require(callable(sign_list) and callable(worker_snapshot), 'runner producer and worker observation callables')
        cert = bootstrap['users']['alice']['certificate']['cert']
        require(cert['serial'] == SERIAL and cert['gid'] == user['gid'], 'Alice H1 certificate serial 101')
        frozen_validate('CredentialBundle', user['bundle'])
        _baseline(pbc, dbc, dep, user, record, policy)
        ctx = _Context(pbc, dbc, adapter, dep, user, record, worker_snapshot, output)
        result.update(_row(ctx, variant, sign_list, deployment_bytes))
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); _save(output, 'result', result)
