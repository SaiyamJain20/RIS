"""Public E01 relay-stress collectors (SL2) for the paper-derived HMBC reconstruction.

Variants follow the frozen catalog steps exactly:
- forged-tuple: paper FABRICATE_TUPLE (relay policyEnf with a fresh reference and
  valid credential records, no PBC request/log); repaired-e honest request and
  certificate whose signature is replaced by a non-witness (TEST-ONLY relay key)
  signature, preceded by an eth_call simulation of the honest certificate.
- new-reference-replay: paper second policyEnf of the same verified tuple under a
  fresh reference; repaired-e re-consumption of the original signed request and
  certificate.
- same-nonce-distinct-digests (repaired-e): two same-(gid, nonce) requests, one
  checkpoint, both certificates before consumption, consume first then second;
  pre/post states are read at explicit historical blocks afterwards (D-5c).
The caller owns fresh deployment/state, controls, plan ACKs and source stability.
Compromised-relay stress is outside A01; results are never HMBC exploits.
"""
import copy
from pathlib import Path

from eth_abi import encode
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from evaluation.access_artifacts import require, verify_checkpoint, verify_decision, verify_prepared
from evaluation.access_execution import _Adapter, _block, _clock, _event, _fingerprint, _source
from evaluation.bootstrap import USERS, _frozen, frozen_validate, signed_digest, strict_json
from evaluation.chain import _owned_signer
from evaluation.evm import _hex
from evaluation.manifests import now
from evaluation.native import _quantity
from evaluation.oracles.provenance import check_forged_tuple, check_new_reference, check_same_nonce
from evaluation.subject_substitution import _decode, _save
from evaluation.vectors import credential_digest
from evaluation.worker_evidence import WorkerLog

PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
VARIANTS = {'forged-tuple': PROFILES, 'new-reference-replay': PROFILES, 'same-nonce-distinct-digests': ('repaired-e',)}
# Fixed synthetic relay references: reproducible, and distinct from every signed digest.
FORGED_REF = '0x'+keccak(text='HMBC.E01.forged-tuple.pbcRequestId.v1').hex()
FRESH_REF = '0x'+keccak(text='HMBC.E01.new-reference.pbcRequestId.v1').hex()


def _grant_id(dep, ref):
    dbc = dep['chains']['dbc']
    return '0x'+keccak(encode(['bytes32', 'address', 'uint256'], [_hex(ref, 32), dbc['contracts']['KSSC'], int(dbc['chainId'])])).hex()


def _relay_decision_signature(dep, decision):
    """Non-witness (TEST-ONLY relay) EIP-712 AccessDecision signature; no witness key is used.

    Returns (signature, digest). The digest is recovered under the same frozen
    template and DBC/KSSC domain used to verify the honest witness signature.
    """
    vectors = _frozen('vectors/eip712-agent1.json')['vectors']
    typed = copy.deepcopy(next(v['typedData'] for v in vectors if v['name'] == 'AccessDecision'))
    dbc = dep['chains']['dbc']
    typed['domain'].update(chainId=dbc['chainId'], verifyingContract=dbc['contracts']['KSSC'])
    typed['message'] = decision
    signature = '0x'+_owned_signer('relay').sign_message(encode_typed_data(full_message=typed)).signature.hex()
    digest = signed_digest('AccessDecision', decision, signature, dep['fixture']['relay']['address'], dbc['chainId'], dbc['contracts']['KSSC'])
    return signature, digest


class _Context:
    def __init__(self, pbc, dbc, adapter, dep, user, record, worker_snapshot, output):
        self.pbc, self.dbc, self.dep, self.user, self.record = pbc, dbc, dep, user, record
        self.worker_snapshot, self.output = worker_snapshot, output
        self.provider = _Adapter(adapter, dep, output)
        self.relay = dep['fixture']['relay']['address']
        self.recipient = '0x'+keccak(text='HMBC.recipient-key.alice').hex()

    def mined(self, chain, native, role, method, args):
        tx_hash = native.receipt['transactionHash']
        tx = chain.rpc.call('eth_getTransactionByHash', [tx_hash])
        require(tx is not None and tx['hash'] == tx_hash and tx['input'] == chain.contracts[role].calldata(method, *args)
                and tx['to'] == chain.contracts[role].address and tx['from'] == self.relay
                and tx['blockHash'] == native.block_hash and int(tx['blockNumber'], 16) == int(native.block_number),
                'relay mined call identity/calldata/block')
        return tx

    def worker(self):
        """Normalize the runner's worker observation (e1.observe_worker_export).

        A verified never-instantiated record is kept explicitly; an export is parsed and
        checked against the deployment fingerprint. No worker operation is performed.
        """
        observed = self.worker_snapshot()
        require(isinstance(observed, dict) and type(observed.get('instantiated')) is bool, 'worker observation')
        if observed['instantiated'] is False:
            require(set(observed) == {'instantiated', 'exitCode', 'message', 'checkedAbsent'}, 'never-instantiated worker record')
            return copy.deepcopy(observed)
        require(set(observed) == {'instantiated', 'export'}, 'worker export record')
        payload = strict_json(observed['export']); WorkerLog(payload, fingerprint=_fingerprint(self.dep))
        return dict(instantiated=True, log=payload)

    def snapshot(self, name, *, grants, refs, nonces, block=None, worker=True):
        pbc, dbc = self.pbc, self.dbc
        with dbc.read_group(tuple(dbc.contracts), block=None if block is None else block['dbc']) as domain:
            grant_rows = {g: domain.read('KSSC', 'grantDetails', g)[0] for g in grants}
            nonce_rows = [[gid, n, domain.read('KSSC', 'nonceConsumed', gid, n)[0]] for gid, n in nonces]
            count = domain.read('ACSC', 'accessLogCount')[0]
            logs_dbc = _decode(dbc, domain.logs())
        with pbc.read_group(tuple(pbc.contracts), block=None if block is None else block['pbc']) as proxy:
            requests = {r: proxy.read('PSC', 'getRequest', r)[0] for r in refs}
            logs_pbc = _decode(pbc, proxy.logs())
        payload = dict(grants=grant_rows, requests=requests, accessLogCount=count, nonces=nonce_rows,
                       logs=dict(pbc=logs_pbc, dbc=logs_dbc))
        if worker:
            payload['worker'] = self.worker()
        _save(self.output, name+'-blocks', dict(pbc=proxy.block, dbc=domain.block)); _save(self.output, name, payload)
        return payload

    def request(self, *, nonce='1', expires=None):
        pbc, dbc, dep, user = self.pbc, self.dbc, self.dep, self.user
        request = dict(sourceChainId=pbc.chain_id, destinationChainId=dbc.chain_id, psc=pbc.contracts['PSC'].address,
                       kssc=dbc.contracts['KSSC'].address, gid=user['gid'], dataId=self.record['dataId'], action='1',
                       policyVersion='1', authEpoch=pbc.read('TMSC', 'authEpoch')[0], keyEpoch='0', nonce=nonce,
                       expiresAt=expires or str(int(_clock(pbc))+30), recipientKeyHash=self.recipient)
        prepared = self.provider.call('prepare_request', dict(request=request, signingKeyRef='keyref:user:alice'))
        digest = verify_prepared(prepared, request=request, deployment=dep)
        require(pbc.read('PSC', 'getRequest', digest)[0]['status'] == '0', 'fresh PBC request')
        args = [request, prepared['signature'], user['bundle']]
        native = pbc.submit('relay', 'PSC', 'requestAccess', *args)
        require(native.success is True, 'native request status')
        self.mined(pbc, native, 'PSC', 'requestAccess', args)
        forward = _event(native, pbc.contracts['PSC'], 'AccessForwarded'); log = _event(native, pbc.contracts['LSC'], 'LogRecorded')
        require(int(log['logIndex']) < int(forward['logIndex']), 'request log before forward')
        state = pbc.read('PSC', 'getRequest', digest, block=_block(native))[0]
        require(state['status'] == '1' and state['outcomeLogId'] == '0' and state['requestLogId'] == forward['fields']['requestLogId']
                and all(state[k] == request[k] for k in ('gid', 'dataId', 'destinationChainId', 'kssc', 'expiresAt')), 'PBC forwarded state')
        code, records = pbc.read('TMSC', 'checkCredentials', request['gid'], user['bundle'], native.timestamp, block=_block(native))
        frozen_validate('CredentialRecords', records)
        f = forward['fields']
        require(code == '0' and f['requestDigest'] == digest and f['verifiedAttributes'] == records
                and f['credentialDigest'] == state['credentialDigest'] == credential_digest(records), 'PBC credential/event join')
        return dict(request=request, prepared=prepared, digest=digest, native=native, records=records, grantId=_grant_id(dep, digest))

    def checkpoint(self, request_block_number):
        pbc, dbc, dep = self.pbc, self.dbc, self.dep
        offered = self.provider.call('collect_checkpoint', {})
        cp = offered['checkpoint']; source = _source(pbc, cp['sourceBlockNumber'], cp['sourceBlockHash'])
        checkpoint = verify_checkpoint(offered, deployment=dep, source_block=source,
            auth_epoch=pbc.read('TMSC', 'authEpoch', block=source)[0], policy_version=pbc.read('PSC', 'policyVersion', block=source)[0],
            dbc_now=_clock(dbc), current_checkpoint=dbc.read('KSSC', 'currentCheckpoint'), request_block_number=request_block_number)
        accepted = dbc.submit('relay', 'KSSC', 'acceptState', checkpoint, offered['signatures'])
        self.accepted = accepted
        expected = {k: checkpoint[k] for k in ('sequence', 'authEpoch', 'policyVersion', 'keyEpoch', 'witnessSetVersion',
                                               'sourceBlockNumber', 'sourceBlockHash', 'expiresAt')}
        require(accepted.success is True and _event(accepted, dbc.contracts['KSSC'], 'StateAccepted')['fields'] == expected
                and dbc.read('KSSC', 'currentCheckpoint', block=_block(accepted)) == [True, checkpoint], 'checkpoint acceptance join')
        return checkpoint

    def decision(self, req, checkpoint):
        pbc, dbc, dep, user = self.pbc, self.dbc, self.dep, self.user
        request = req['request']
        offered = self.provider.call('collect_decision', dict(requestDigest=req['digest']))
        dbc_block = str(_quantity(dbc.latest_block()['number'])); dbc_now = _clock(dbc)
        require(dbc.read('KSSC', 'currentCheckpoint') == [True, checkpoint], 'current checkpoint stability')
        source = _source(pbc, checkpoint['sourceBlockNumber'], checkpoint['sourceBlockHash'])
        code, records = pbc.read('TMSC', 'checkCredentials', request['gid'], user['bundle'], str(_quantity(source['timestamp'])), block=source)
        decision = verify_decision(offered, request=request, request_digest=req['digest'], deployment=dep, checkpoint=checkpoint,
            source_block=source, dbc_now=dbc_now, pbc_now=_clock(pbc), request_block_number=req['native'].block_number,
            native_records=records, credentials_code=code, policy_allowed=dbc.read('ACSC', 'evaluate', request['dataId'], records)[0],
            nonce_consumed=dbc.read('KSSC', 'nonceConsumed', request['gid'], request['nonce'])[0])
        require(decision['decision']['result'] == '1', 'honest ALLOW certificate for registered Alice')
        return dict(result=decision, dbcBlock=dbc_block, dbcNow=dbc_now)


def _baseline(pbc, dbc, dep, user, record, policy):
    for chain, name in ((pbc, 'pbc'), (dbc, 'dbc')):
        manifest = dep['chains'][name]
        require(chain.chain_id == manifest['chainId']
                and all(chain.contracts[r].address == a for r, a in manifest['contracts'].items()), 'executor deployment')
    for chain, roles in ((pbc, ('TMSC', 'PSC')), (dbc, ('ACSC', 'KSSC'))):
        block = chain.latest_block()
        for role in roles:
            require(chain.read(role, 'profile', block=block) == [dep['profileEnum']]
                    and chain.read(role, 'mutations', block=block) == ['0'], 'native baseline profile')
    relay = dep['fixture']['relay']['address']
    require(pbc.read('PSC', 'relay') == [relay], 'PBC relay')
    if dep['profile'] == 'repaired-e':
        ws = dep['fixture']['witnessSet']
        require(ws['version'] == '1' and ws['threshold'] == '1' and len(ws['witnesses']) == 1, 'single E witness')
        for chain, role in ((pbc, 'PSC'), (dbc, 'KSSC')):
            block = chain.latest_block()
            require(chain.read(role, 'witnesses', block=block) == [ws['witnesses']] and chain.read(role, 'threshold', block=block) == ['1']
                    and chain.read(role, 'witnessSetVersion', block=block) == ['1'], 'native witness configuration')
    else:
        require(dbc.read('ACSC', 'pscRelay') == [relay], 'DBC relay')
    pb = pbc.latest_block()
    require(pbc.read('RSC', 'isRegistered', user['gid'], block=pb) == [True]
            and pbc.read('RSC', 'recipientKeyHash', user['gid'], block=pb) == ['0x'+keccak(text='HMBC.recipient-key.alice').hex()],
            'registered Alice and recipient')
    entry = dbc.read('ACSC', 'dataEntry', record['dataId'])[0]
    require(entry['exists'] is True and entry['owner'] == record['owner']
            and dbc.read('ACSC', 'policy', entry['policyId']) == [policy['clauses']], 'registered record/policy')


def _forged_tuple(ctx):
    pbc, dbc, dep, user = ctx.pbc, ctx.dbc, ctx.dep, ctx.user
    gid, data = user['gid'], ctx.record['dataId']
    if dep['profile'] != 'repaired-e':
        ref = FORGED_REF; grant = _grant_id(dep, ref)
        pb = pbc.latest_block()
        code, records = pbc.read('TMSC', 'checkCredentials', gid, user['bundle'], str(_quantity(pb['timestamp'])), block=pb)
        frozen_validate('CredentialRecords', records)
        require(code == '0' and bool(records) and dbc.read('ACSC', 'evaluate', data, records) == [True], 'valid public credential records')
        args = [dict(pbcRequestId=ref, gid=gid, dataId=data, action='1'), records]
        _save(ctx.output, 'public-call', dict(method='policyEnf', arguments=args, credentialBlock=pb))
        before = ctx.snapshot('before', grants=[grant], refs=[ref], nonces=[(gid, '1')])
        native = dbc.submit('relay', 'ACSC', 'policyEnf', *args)
        _save(ctx.output, 'stress-transaction', ctx.mined(dbc, native, 'ACSC', 'policyEnf', args))
        events = _decode(dbc, native.receipt['logs'])
        after = ctx.snapshot('after', grants=[grant], refs=[ref], nonces=[(gid, '1')])
        proof = check_forged_tuple(profile=dep['profile'], before=before, after=after, gid=gid, data_id=data, relay=ctx.relay,
                                   fabricated_ref=ref, grant_id=grant, credential_digest=credential_digest(records), success=native.success,
                                   rejection_code=None, receipt_events=events, timestamp=native.timestamp, forged=None)
        return dict(proof, timeline=_timeline(ctx, stress=native))
    req = ctx.request(); checkpoint = ctx.checkpoint(req['native'].block_number); collected = ctx.decision(req, checkpoint)
    result = collected['result']; records = result['credentialRecords']
    honest = {k: copy.deepcopy(result[k]) for k in ('decision', 'signatures')}
    dbc_dep = dep['chains']['dbc']; witness = dep['fixture']['witnessSet']['witnesses'][0]
    honest_digest = signed_digest('AccessDecision', result['decision'], honest['signatures'][0], witness,
                                  dbc_dep['chainId'], dbc_dep['contracts']['KSSC'])
    forged_signature, forged_digest = _relay_decision_signature(dep, result['decision'])
    forged = dict(decision=copy.deepcopy(result['decision']), signatures=[forged_signature])
    honest_args = [req['request'], honest, records]; forged_args = [req['request'], forged, records]
    _save(ctx.output, 'public-call', dict(method='consumeDecision', honestArguments=honest_args, forgedArguments=forged_args))
    before = ctx.snapshot('before', grants=[req['grantId']], refs=[req['digest']], nonces=[(gid, '1')])
    acsc = dbc.contracts['ACSC']; latest = dbc.latest_block()
    try:
        raw = dbc.rpc.call('eth_call', [{'from': ctx.relay, 'to': acsc.address, 'data': acsc.calldata('consumeDecision', *honest_args)},
                                        latest['number']])
    except RuntimeError as error:
        raise ValueError('Public access honest certificate simulation failed') from error
    simulated = acsc.decode_return('consumeDecision', raw)[0]
    native = dbc.submit('relay', 'ACSC', 'consumeDecision', *forged_args, expect_success=False)
    _save(ctx.output, 'stress-transaction', ctx.mined(dbc, native, 'ACSC', 'consumeDecision', forged_args))
    code = dbc.rejection_code(native); events = _decode(dbc, native.receipt['logs'])
    after = ctx.snapshot('after', grants=[req['grantId']], refs=[req['digest']], nonces=[(gid, '1')])
    facts = dict(honestSimulationGrantId=simulated, simulationBlock=latest, simulation='eth_call only; never mined',
                 recoveredSigner=ctx.relay, witnesses=dep['fixture']['witnessSet']['witnesses'],
                 decisionUnchanged=forged['decision'] == honest['decision'], signatureChanged=forged['signatures'] != honest['signatures'],
                 honestSigner=witness, honestDigest=honest_digest, forgedDigest=forged_digest,
                 signedDigestEqual=honest_digest == forged_digest,
                 domain=dict(chainId=dbc_dep['chainId'], verifyingContract=dbc_dep['contracts']['KSSC']),
                 honestSignatures=honest['signatures'], forgedSignatures=forged['signatures'])
    _save(ctx.output, 'forged-certificate', facts)
    proof = check_forged_tuple(profile=dep['profile'], before=before, after=after, gid=gid, data_id=data, relay=ctx.relay,
                               fabricated_ref=req['digest'], grant_id=req['grantId'], credential_digest=credential_digest(records),
                               success=native.success, rejection_code=code, receipt_events=events, timestamp=native.timestamp,
                               forged={k: facts[k] for k in ('honestSimulationGrantId', 'recoveredSigner', 'witnesses',
                                                             'decisionUnchanged', 'signatureChanged', 'signedDigestEqual')})
    return dict(proof, timeline=_timeline(ctx, req=req, stress=native))


def _timeline(ctx, *, req=None, stress):
    """Chain timestamps against the 30 s request lifetime (A1-0064); paper tuples carry no expiry."""
    row = dict(stressTimestamp=stress.timestamp, stressBlock=stress.block_number)
    if req is not None:
        row.update(requestTimestamp=req['native'].timestamp, requestExpiresAt=req['request']['expiresAt'],
                   marginSeconds=int(req['request']['expiresAt'])-int(stress.timestamp))
    _save(ctx.output, 'timeline', row)
    return row


def _new_reference(ctx):
    pbc, dbc, dep, user = ctx.pbc, ctx.dbc, ctx.dep, ctx.user
    gid, data = user['gid'], ctx.record['dataId']
    req = ctx.request()
    if dep['profile'] != 'repaired-e':
        records = req['records']
        first_args = [dict(pbcRequestId=req['digest'], gid=gid, dataId=data, action='1'), records]
        first = dbc.submit('relay', 'ACSC', 'policyEnf', *first_args)
        ctx.mined(dbc, first, 'ACSC', 'policyEnf', first_args)
        require([e['fields']['grantId'] for e in _decode(dbc, first.receipt['logs']) if e['name'] == 'GrantIssued'] == [req['grantId']],
                'original forwarded tuple granted')
        ref = FRESH_REF; replay_grant = _grant_id(dep, ref)
        args = [dict(first_args[0], pbcRequestId=ref), records]
        _save(ctx.output, 'public-call', dict(method='policyEnf', original=first_args, replay=args))
        refs, grants = [req['digest'], ref], [req['grantId'], replay_grant]
        before = ctx.snapshot('before', grants=grants, refs=refs, nonces=[(gid, '1')])
        native = dbc.submit('relay', 'ACSC', 'policyEnf', *args)
        tx = ctx.mined(dbc, native, 'ACSC', 'policyEnf', args); _save(ctx.output, 'stress-transaction', tx)
        events = _decode(dbc, native.receipt['logs'])
        after = ctx.snapshot('after', grants=grants, refs=refs, nonces=[(gid, '1')])
        proof = check_new_reference(profile=dep['profile'], before=before, after=after, gid=gid, data_id=data, relay=ctx.relay,
                                    original_ref=req['digest'], original_grant=req['grantId'], replay_ref=ref, replay_grant=replay_grant,
                                    credential_digest=credential_digest(records), identical_calldata=False, success=native.success,
                                    rejection_code=None, receipt_events=events, timestamp=native.timestamp)
        return dict(proof, timeline=_timeline(ctx, req=req, stress=native))
    checkpoint = ctx.checkpoint(req['native'].block_number); collected = ctx.decision(req, checkpoint)
    result = collected['result']; records = result['credentialRecords']
    args = [req['request'], {k: copy.deepcopy(result[k]) for k in ('decision', 'signatures')}, records]
    first = dbc.submit('relay', 'ACSC', 'consumeDecision', *args)
    first_tx = ctx.mined(dbc, first, 'ACSC', 'consumeDecision', args)
    require([e['fields']['grantId'] for e in _decode(dbc, first.receipt['logs']) if e['name'] == 'GrantIssued'] == [req['grantId']],
            'original certificate granted')
    _save(ctx.output, 'public-call', dict(method='consumeDecision', arguments=args, originalTransaction=first_tx))
    before = ctx.snapshot('before', grants=[req['grantId']], refs=[req['digest']], nonces=[(gid, '1')])
    native = dbc.submit('relay', 'ACSC', 'consumeDecision', *args, expect_success=False)
    tx = ctx.mined(dbc, native, 'ACSC', 'consumeDecision', args); _save(ctx.output, 'stress-transaction', tx)
    code = dbc.rejection_code(native); events = _decode(dbc, native.receipt['logs'])
    after = ctx.snapshot('after', grants=[req['grantId']], refs=[req['digest']], nonces=[(gid, '1')])
    proof = check_new_reference(profile=dep['profile'], before=before, after=after, gid=gid, data_id=data, relay=ctx.relay,
                                original_ref=req['digest'], original_grant=req['grantId'], replay_ref=req['digest'],
                                replay_grant=req['grantId'], credential_digest=credential_digest(records),
                                identical_calldata=tx['input'] == first_tx['input'] and tx['hash'] != first_tx['hash'],
                                success=native.success, rejection_code=code, receipt_events=events, timestamp=native.timestamp)
    return dict(proof, timeline=_timeline(ctx, req=req, stress=native))


def _same_nonce(ctx):
    pbc, dbc, dep, user = ctx.pbc, ctx.dbc, ctx.dep, ctx.user
    gid = user['gid']
    worker_before = ctx.worker(); _save(ctx.output, 'worker-before', worker_before)
    first = ctx.request(nonce='1')
    second = ctx.request(nonce='1', expires=str(int(first['request']['expiresAt'])-1))
    require(first['digest'] != second['digest'], 'distinct request digests')
    checkpoint = ctx.checkpoint(second['native'].block_number)
    decisions = [ctx.decision(first, checkpoint), ctx.decision(second, checkpoint)]
    args = [[r['request'], {k: copy.deepcopy(d['result'][k]) for k in ('decision', 'signatures')}, d['result']['credentialRecords']]
            for r, d in zip((first, second), decisions)]
    _save(ctx.output, 'public-call', dict(method='consumeDecision', first=args[0], second=args[1]))
    consumed = dbc.submit('relay', 'ACSC', 'consumeDecision', *args[0])
    ctx.mined(dbc, consumed, 'ACSC', 'consumeDecision', args[0])
    first_events = _decode(dbc, consumed.receipt['logs'])
    native = dbc.submit('relay', 'ACSC', 'consumeDecision', *args[1], expect_success=False)
    _save(ctx.output, 'stress-transaction', ctx.mined(dbc, native, 'ACSC', 'consumeDecision', args[1]))
    code = dbc.rejection_code(native); events = _decode(dbc, native.receipt['logs'])
    # Historical views at fixed blocks are immutable; read them after the time-bound
    # consumptions instead of inside the 30 s request lifetime (A1-0061 D-5c).
    pbc_block = str(_quantity(pbc.latest_block()['number'])); before_block = str(int(native.block_number)-1)
    keys = dict(grants=[first['grantId'], second['grantId']], refs=[first['digest'], second['digest']], nonces=[(gid, '1')], worker=False)
    before_second = ctx.snapshot('before-second', block=dict(pbc=pbc_block, dbc=before_block), **keys)
    after_second = ctx.snapshot('after-second', block=dict(pbc=pbc_block, dbc=native.block_number), **keys)
    worker_after = ctx.worker(); _save(ctx.output, 'worker-after', worker_after)
    expiries = [int(first['request']['expiresAt']), int(second['request']['expiresAt'])]
    timeline = dict(firstRequestTimestamp=first['native'].timestamp, secondRequestTimestamp=second['native'].timestamp,
                    checkpointTimestamp=ctx.accepted.timestamp, checkpointExpiresAt=checkpoint['expiresAt'],
                    decisionCollectedAtDbcBlocks=[d['dbcBlock'] for d in decisions], decisionDbcClock=[d['dbcNow'] for d in decisions],
                    decisionExpiresAt=[d['result']['decision']['expiresAt'] for d in decisions],
                    firstConsumeTimestamp=consumed.timestamp, secondConsumeTimestamp=native.timestamp,
                    firstExpiresAt=str(expiries[0]), secondExpiresAt=str(expiries[1]), marginSeconds=min(expiries)-int(native.timestamp))
    _save(ctx.output, 'timeline', timeline)
    proof = check_same_nonce(
        first=dict(request=first['request'], digest=first['digest'], grantId=first['grantId'], block=first['native'].block_number),
        second=dict(request=second['request'], digest=second['digest'], grantId=second['grantId'], block=second['native'].block_number),
        checkpoint=checkpoint, decisions=[dict(decision=d['result']['decision'], dbcBlock=d['dbcBlock']) for d in decisions],
        consume_first=dict(success=consumed.success, block=consumed.block_number, grantId=first['grantId'], events=first_events),
        before_second=before_second, after_second=after_second, before_block=before_block, second_block=native.block_number,
        success=native.success, rejection_code=code, receipt_events=events, worker_before=worker_before, worker_after=worker_after)
    return dict(proof, timeline=timeline)


def execute_relay_stress(pbc, dbc, adapter, *, deployment_bytes, user_label, user, record, policy, variant, worker_snapshot, output):
    """Run one frozen SL2 relay-stress row on a fresh deployment; no release or outcome."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None, variant=variant, delivery='unknown',
                  scope='C-E2 SL2 relay stress; separate controls, plan ACKs and gate apply')
    try:
        dep = strict_json(deployment_bytes); frozen_validate('LedgerDeployment', dep)
        require(variant in VARIANTS and dep['profile'] in VARIANTS[variant], 'frozen catalog variant/profile')
        require(dep['interfaceVersion'] == 'v1' and dep['mutations'] == '0', 'baseline deployment')
        require(user_label == 'alice' and user['gid'] == USERS['alice'], 'registered Alice stress subject')
        frozen_validate('CredentialBundle', user['bundle'])
        _baseline(pbc, dbc, dep, user, record, policy)
        ctx = _Context(pbc, dbc, adapter, dep, user, record, worker_snapshot, output)
        proof = {'forged-tuple': _forged_tuple, 'new-reference-replay': _new_reference,
                 'same-nonce-distinct-digests': _same_nonce}[variant](ctx)
        result.update(proof)
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); _save(output, 'result', result)
