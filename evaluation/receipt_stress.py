"""Public E03 receipt-control collectors (SL4) for the paper-derived HMBC reconstruction.

Repaired-e only. Each row follows the frozen supplement steps exactly, on its own fresh forwarded
request and actual allowed grant:
- REQUEST_ACCESS > FORWARD_OR_CONSUME (checkpoint, honest ALLOW certificate, consumeDecision);
- ATTEST_GRANT: the production witness attests the real grant (honest receipt), before any report;
- receipt-binding-control: RESIGN_RECEIPT_FIELD via the pinned TEST-ONLY deviating witness
  (S2-0007/A1-0064; A40 deliberate deviation), at the honest receipt's DBC block, checked three ways
  before use; any non-zero exit is a failed trial (output kept only as sha256 and first line);
- receipt-signature-control: ALTER_RECEIPT_KEEP_SIGNATURE, one bound field changed with the same
  deterministic value, honest signature kept, no tool;
- receipt-binding-positive: the honest receipt unchanged;
- REPORT_OUTCOME: relay PSC.reportAttestedOutcome(digest, fixed synthetic outcome digest, receipt, sigs).
No step is a worker operation: the worker database must stay verified never-instantiated, and that
precondition is re-observed after every catalog step (D49). The caller owns fresh deployment/state,
controls, plan ACKs and source stability.
"""
import copy
import hashlib
from pathlib import Path

from eth_utils import keccak

from evaluation.access_artifacts import require
from evaluation.access_execution import _clock, _source
from evaluation.audit_stress import _grant
from evaluation.bootstrap import USERS, frozen_validate, signed_digest, strict_json
from evaluation.manifests import now
from evaluation.oracles.provenance import _idle
from evaluation.oracles.receipt import A40_LABEL, STEP, VARIANTS, check_deviation_artifact, check_receipt_row, deviation_value
from evaluation.relay_stress import _Context, _baseline
from evaluation.subject_substitution import _decode, _save

# Fixed synthetic outcome digest for every report: reproducible, never a real response.
RECEIPT_OUTCOME = '0x'+keccak(text='HMBC.E03.receipt-control-outcome.v1').hex()


def _psc_spec(pbc):
    spec = pbc.contracts['PSC']._function('reportAttestedOutcome')['inputs'][2]
    require(spec['type'] == 'tuple' and [c['name'] for c in spec['components']] == [
        'requestDigest', 'grantId', 'gid', 'dataId', 'keyEpoch', 'grantExpiresAt', 'witnessSetVersion', 'dbcChainId', 'kssc',
        'dbcBlockNumber', 'dbcBlockHash'], 'pinned GrantReceipt ABI tuple')
    return spec


def _deviate(ctx, deviate, grant_id, field, honest, witness):
    at_block = honest['receipt']['dbcBlockNumber']
    answer = deviate(grant_id, field, at_block)
    require(isinstance(answer, dict) and set(answer) == {'exitCode', 'output'} and type(answer['exitCode']) is int
            and isinstance(answer['output'], bytes), 'deviating witness command record')
    digest = hashlib.sha256(answer['output']).hexdigest()
    if answer['exitCode'] != 0:
        first = answer['output'].split(b'\n', 1)[0].decode('utf-8', 'replace')[:240]
        _save(ctx.output, 'deviation-refusal', dict(exitCode=answer['exitCode'], outputSha256=digest, firstLine=first,
                                                    note='failed trial (S2-0007): non-zero exit; output kept only as sha256 and first line'))
        raise ValueError('TEST-ONLY deviating witness exited '+str(answer['exitCode'])+' (failed trial; output sha256 '+digest+')')
    lines = answer['output'].split(b'\n')
    require(len(lines) == 2 and lines[1] == b'' and lines[0], 'deviating witness printed exactly one JSON line')
    artifact = check_deviation_artifact(strict_json(lines[0]), honest_receipt=honest['receipt'], field=field, witness=witness,
                                        pbc_chain_id=ctx.pbc.chain_id, psc=ctx.pbc.contracts['PSC'].address)
    _save(ctx.output, 'deviation', dict(artifact, label=A40_LABEL, outputSha256=digest, atBlock=at_block))
    return artifact


def _receipt(ctx, variant, field, deviate):
    pbc, dbc, dep, user = ctx.pbc, ctx.dbc, ctx.dep, ctx.user
    witness = dep['fixture']['witnessSet']['witnesses'][0]; psc = pbc.contracts['PSC'].address
    spec = _psc_spec(pbc)
    steps = []; first = []

    def precondition(step, observed=None):
        observed = ctx.worker() if observed is None else observed
        _idle(observed)
        require(observed['instantiated'] is False and (not first or observed == first[0]),
                'verified never-instantiated worker after '+step)
        first[:1] = first[:1] or [copy.deepcopy(observed)]
        steps.append(dict(step=step, worker='never-instantiated (verified)'))

    precondition('baseline')
    req = ctx.request()
    precondition('REQUEST_ACCESS')
    granted = _grant(ctx, req)
    grant = dbc.read('KSSC', 'grantDetails', req['grantId'])[0]
    require(grant['exists'] is True and grant['allowed'] is True and grant['requestDigest'] == req['digest'], 'actual allowed grant')
    precondition('FORWARD_OR_CONSUME')
    # ATTEST_GRANT: honest production witness, before any report on this request (witness.py refuses after an outcome).
    attested = ctx.provider.call('attest_grant', dict(grantId=req['grantId']))
    honest = dict(receipt=copy.deepcopy(attested['receipt']), signatures=copy.deepcopy(attested['signatures']))
    receipt = honest['receipt']
    require(len(honest['signatures']) == 1, 'one honest witness signature (E threshold 1)')
    signed_digest('GrantReceipt', receipt, honest['signatures'][0], witness, pbc.chain_id, psc)
    receipt_block = _source(dbc, receipt['dbcBlockNumber'], receipt['dbcBlockHash'])
    require(dbc.read('KSSC', 'grantDetails', req['grantId'], block=receipt_block) == [grant], 'attested native grant at the receipt block')
    request = req['request']
    require(all(receipt[k] == v for k, v in dict(requestDigest=req['digest'], grantId=req['grantId'], gid=request['gid'],
                                                 dataId=request['dataId'], keyEpoch='0', grantExpiresAt=grant['expiresAt'],
                                                 witnessSetVersion='1', dbcChainId=dbc.chain_id, kssc=request['kssc']).items()),
            'honest receipt joins request and grant')
    _save(ctx.output, 'honest-receipt', honest)
    precondition('ATTEST_GRANT')
    deviation = None
    if variant == 'receipt-binding-control':
        deviation = _deviate(ctx, deviate, req['grantId'], field, honest, witness)
        submitted = dict(receipt=copy.deepcopy(deviation['receipt']), signatures=copy.deepcopy(deviation['signatures']))
    elif variant == 'receipt-signature-control':
        altered = dict(receipt, **{field: deviation_value(field, receipt[field])})
        submitted = dict(receipt=altered, signatures=copy.deepcopy(honest['signatures']))
        _save(ctx.output, 'altered-receipt', dict(submitted, field=field, original=receipt[field],
                                                  label='ALTER_RECEIPT_KEEP_SIGNATURE: one bound field changed, honest signature kept; no tool'))
    else:
        submitted = copy.deepcopy(honest)
    gid = user['gid']; keys = dict(grants=[req['grantId']], refs=[req['digest']], nonces=[(gid, '1')])
    args = [req['digest'], RECEIPT_OUTCOME, submitted['receipt'], submitted['signatures']]
    _save(ctx.output, 'public-call', dict(method='reportAttestedOutcome', arguments=args))
    before = ctx.snapshot('before', **keys)
    if STEP[variant]: precondition(STEP[variant], before['worker'])
    positive = variant == 'receipt-binding-positive'
    native = pbc.submit('relay', 'PSC', 'reportAttestedOutcome', *args, expect_success=positive)
    _save(ctx.output, 'stress-transaction', ctx.mined(pbc, native, 'PSC', 'reportAttestedOutcome', args))
    code = None if positive else pbc.rejection_code(native)
    events = _decode(pbc, native.receipt['logs'])
    after = ctx.snapshot('after', **keys)
    precondition('REPORT_OUTCOME', after['worker'])
    timeline = dict(requestTimestamp=req['native'].timestamp, requestExpiresAt=request['expiresAt'], grantTimestamp=granted.timestamp,
                    grantExpiresAt=grant['expiresAt'], receiptDbcBlock=receipt['dbcBlockNumber'], reportTimestamp=native.timestamp,
                    reportDbcClock=_clock(dbc), reportAfterGrantExpiry=int(_clock(dbc)) >= int(grant['expiresAt']),
                    note='late reconciliation is allowed by PSC (no report deadline); recorded, not required')
    _save(ctx.output, 'timeline', timeline)
    proof = check_receipt_row(variant=variant, field=field, before=before, after=after, request_digest=req['digest'],
                              grant_id=req['grantId'], honest=honest, submitted=submitted, deviation=None if deviation is None
                              else {k: deviation[k] for k in ('schemaVersion', 'testOnly', 'deviation', 'receipt', 'signatures')},
                              success=native.success, rejection_code=code, receipt_events=events, outcome_digest=RECEIPT_OUTCOME,
                              relay=ctx.relay, witness=witness, pbc_chain_id=pbc.chain_id, psc=psc, receipt_spec=spec)
    return dict(proof, timeline=timeline, workerSteps=steps)


def execute_receipt_stress(pbc, dbc, adapter, *, deployment_bytes, user_label, user, record, policy, variant, field,
                           worker_snapshot, deviate, output):
    """Run one frozen SL4 receipt-control row on a fresh repaired-e deployment."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None, variant=variant, field=field, delivery='unknown',
                  scope='C-E2 SL4 receipt controls (repaired-e); separate controls, plan ACKs and gate apply')
    try:
        dep = strict_json(deployment_bytes); frozen_validate('LedgerDeployment', dep)
        require(variant in VARIANTS and field in VARIANTS[variant] and dep['profile'] == 'repaired-e', 'frozen SL4 receipt row/profile')
        require(dep['interfaceVersion'] == 'v1' and dep['mutations'] == '0', 'baseline deployment')
        require(user_label == 'alice' and user['gid'] == USERS['alice'], 'registered Alice subject')
        require(callable(deviate) and callable(worker_snapshot), 'runner deviation and worker observation callables')
        frozen_validate('CredentialBundle', user['bundle'])
        _baseline(pbc, dbc, dep, user, record, policy)
        ctx = _Context(pbc, dbc, adapter, dep, user, record, worker_snapshot, output)
        result.update(_receipt(ctx, variant, field, deviate))
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); _save(output, 'result', result)
