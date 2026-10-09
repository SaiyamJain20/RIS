"""C-E1 access through public ABIs and the frozen JSON-lines boundary.

The caller owns pinned services, bootstrap, snapshots, dependency/tool hashes and
exact integration FREEZE ACKs. This executes one independently specified control;
it does not start services, pass an RQ gate, or authenticate an RPC provider.
"""
import copy
import hashlib
import json
from pathlib import Path

from eth_abi import encode
from eth_utils import keccak

from evaluation.access_artifacts import require, verify_prepared, verify_checkpoint, verify_decision
from evaluation.bootstrap import USERS, frozen_validate, signed_digest, strict_json
from evaluation.evm import _hex
from evaluation.manifests import now
from evaluation.native import _quantity
from evaluation.oracles.access import evaluate
from evaluation.vectors import credential_digest
from evaluation.worker_evidence import WorkerLog

ZERO = '0x'+'00'*32
RESPONSE = {op: ''.join(word.title() for word in op.split('_'))+'Response'
            for op in ('prepare_request', 'collect_checkpoint', 'collect_decision', 'encrypt_record',
                       'release', 'finish_decryption', 'attest_grant')}


def _block(native):
    return dict(number=hex(int(native.block_number)), hash=native.block_hash)


def _clock(chain):
    return str(_quantity(chain.rpc.call('eth_getBlockByNumber', ['pending', False])['timestamp']))


def _source(chain, number, block_hash):
    block = chain.rpc.call('eth_getBlockByNumber', [hex(int(number)), False])
    require(block is not None and str(_quantity(block['number'])) == number and block['hash'] == block_hash, 'observed source identity')
    return block


def _event(native, contract, name):
    matches = [e for e in native.decoded(contract) if e['name'] == name]
    require(len(matches) == 1, name+' exact event count')
    return matches[0]


def _normalized(native, chain, role):
    def reader(contract, method, *args):
        require(contract is chain.contracts[role], 'normalizer contract')
        return chain.observe(role, method, *args, block=_block(native))
    return native.normalized(chain.contracts[role], role, view_reader=reader)


def _fingerprint(deployment):
    chains = deployment['chains']
    fields = {name: [chains[name]['chainId'], *[chains[name]['contracts'][r] for r in roles]]
              for name, roles in [('pbc', ('PSC', 'RSC')), ('dbc', ('KSSC', 'ACSC'))]}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def _commitments(record, policy):
    frozen_validate('SymbolicRecord', record); frozen_validate('SymbolicPolicy', policy)
    clauses = [[(_hex(q['role'], 32), int(q['kind']), int(q['issuerMode'])) for q in clause] for clause in policy['clauses']]
    pd = keccak(encode(['(bytes32,uint8,uint8)[][]'], [clauses]))
    cd = keccak(encode(['bytes32', 'bytes32', 'address', 'bytes32', 'bytes32', 'uint64'],
                      [keccak(text='HMBCSymbolicRecord/v1'), _hex(record['dataId'], 32), record['owner'], _hex(record['payloadDigest'], 32), pd, 0]))
    return '0x'+pd.hex(), '0x'+cd.hex()


class _Adapter:
    def __init__(self, process, deployment, output):
        self.process = process; self.deployment = deployment; self.output = output; self.exchanges = []

    def call(self, operation, inputs):
        response = self.response(operation, inputs)
        require(response['ok'] is True, 'adapter '+operation+' success')
        return response['result']

    def response(self, operation, inputs):
        """Exchange and validate one frozen operation; return the full response.

        Used directly only where a schema-valid refusal is the expected
        observation (subject completion with the original key reference).
        """
        request = dict(schemaVersion='v1', operation=operation, input=inputs, deploymentManifest=self.deployment)
        frozen_validate('AdapterRequest', request)
        started = now()
        response = self.process.exchange(request)
        row = dict(operation=operation, startedAt=started, endedAt=now(),
                   requestSha256=hashlib.sha256(json.dumps(request, separators=(',', ':')).encode()).hexdigest(),
                   responseCanonicalSha256=hashlib.sha256(json.dumps(response, separators=(',', ':')).encode()).hexdigest(),
                   response=None, validationFailure=None)
        self.exchanges.append(row)
        try:
            frozen_validate(RESPONSE[operation], response)
        except ValueError as error:
            row['validationFailure'] = type(error).__name__
            (self.output/'exchanges.json').write_text(json.dumps(self.exchanges, indent=2)+'\n')
            raise
        row['response'] = copy.deepcopy(response)
        if response['ok'] is False:
            row['response']['error'] = {'code': response['error']['code']}
        # Keep capability bytes only in process memory. Raw transport digests are
        # separately retained by JsonLinesProcess; this digest is canonical JSON.
        result = row['response'].get('result')
        if isinstance(result, dict) and isinstance(result.get('responseEnvelope'), dict):
            envelope = result['responseEnvelope']
            token = envelope.pop('token', None)
            if isinstance(token, str):
                envelope['tokenSha256'] = hashlib.sha256(token.encode()).hexdigest()
        (self.output/'exchanges.json').write_text(json.dumps(self.exchanges, indent=2)+'\n')
        return response


def execute_access(pbc, dbc, adapter, *, deployment_bytes, user_label, user, record, policy,
                   expected_allow, worker_snapshot, output, recovery_point=None, duplicate_outcome=False, nonce_replay=False, subject_substitution=None,
                   subject_completion=False):
    """Run Alice ALLOW or registered Bob POLICY_DENIED against checked evidence.

    `worker_snapshot` executes the pinned owner's read-only exporter and returns
    raw bytes, with command/hash evidence retained by the caller. `adapter` is the
    owned JsonLinesProcess. Raw receipts/views and transport hashes are retained
    by their public executors. Tokens never enter the result or exchange files.
    """
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None, scope='C-E1 single control; not an RQ gate',
                  adapterMode='symbolic', observed=None, oracle=None, delivery='unknown')
    try:
        require(recovery_point in (None, 'after_intent', 'after_send'), 'explicit recovery point')
        require(type(duplicate_outcome) is bool and (not duplicate_outcome or expected_allow is True), 'duplicate probe after allow only')
        require(type(nonce_replay) is bool and (not nonce_replay or
                (expected_allow is True and recovery_point is None and not duplicate_outcome)), 'isolated nonce replay after allow')
        if subject_substitution is not None:
            frozen_validate('Address', subject_substitution)
            require(expected_allow is True and subject_substitution != user['gid']
                    and recovery_point is None and not duplicate_outcome and not nonce_replay,
                    'isolated pre-release subject stress')
        require(type(subject_completion) is bool and (not subject_completion or (
                subject_substitution is not None and subject_substitution in USERS.values())), 'subject completion follows registered-subject stress')
        if recovery_point is not None:
            result['scope'] = 'C-E2 logical crash/retry control; not an RQ gate'
        dep = strict_json(deployment_bytes); frozen_validate('LedgerDeployment', dep)
        require(dep['interfaceVersion'] == 'v1' and dep['mutations'] == '0'
                and dep['profile'] in ('paper-strict', 'paper-minimal', 'repaired-e'), 'baseline deployment')
        require(not subject_completion or dep['profile'] != 'repaired-e', 'repaired subject stress ends at rejection; no release')
        require(user_label in USERS and user['gid'] == USERS[user_label]
                and expected_allow is (user_label == 'alice'), 'independent E1 actor expectation')
        frozen_validate('CredentialBundle', user['bundle'])
        recipient = '0x'+keccak(text='HMBC.recipient-key.'+user_label).hex()
        require(user['recipientKeyHash'] == recipient, 'fixture recipient')
        repaired = dep['profile'] == 'repaired-e'
        for chain, name in ((pbc, 'pbc'), (dbc, 'dbc')):
            manifest = dep['chains'][name]
            require(chain.chain_id == manifest['chainId']
                    and all(chain.contracts[r].address == a for r, a in manifest['contracts'].items()), 'executor deployment')
        for chain, roles in ((pbc, ('TMSC', 'PSC')), (dbc, ('ACSC', 'KSSC'))):
            block = chain.latest_block()
            for role in roles:
                require(chain.read(role, 'profile', block=block) == [dep['profileEnum']]
                        and chain.read(role, 'mutations', block=block) == ['0'], 'native baseline profile')
        require(pbc.read('PSC', 'relay') == [dep['fixture']['relay']['address']], 'PBC relay')
        if not repaired:
            require(dbc.read('ACSC', 'pscRelay') == [dep['fixture']['relay']['address']], 'DBC relay')
        if repaired:
            ws = dep['fixture']['witnessSet']
            require(ws['version'] == '1' and ws['threshold'] == '1' and len(ws['witnesses']) == 1, 'single E witness')
            for chain, role in ((pbc, 'PSC'), (dbc, 'KSSC')):
                block = chain.latest_block()
                require(chain.read(role, 'witnesses', block=block) == [ws['witnesses']]
                        and chain.read(role, 'threshold', block=block) == ['1']
                        and chain.read(role, 'witnessSetVersion', block=block) == ['1'], 'native witness configuration')
        pb = pbc.latest_block()
        require(pbc.read('RSC', 'isRegistered', user['gid'], block=pb) == [True]
                and pbc.read('RSC', 'recipientKeyHash', user['gid'], block=pb) == [recipient], 'registered actor/recipient')
        entry = dbc.read('ACSC', 'dataEntry', record['dataId'])[0]
        require(entry['exists'] is True and entry['owner'] == record['owner']
                and dbc.read('ACSC', 'policy', entry['policyId']) == [policy['clauses']], 'registered record/policy')
        pd, cd = _commitments(record, policy)
        provider = _Adapter(adapter, dep, output)
        encrypted = provider.call('encrypt_record', dict(record=record, policy=policy, keyEpoch='0'))
        require(encrypted['dataId'] == record['dataId'] and encrypted['policyDigest'] == pd
                and encrypted['ciphertextDigest'] == cd, 'symbolic record commitments')
        fingerprint = _fingerprint(dep)

        def worker(name):
            raw = worker_snapshot(); payload = strict_json(raw)
            checked = WorkerLog(payload, fingerprint=fingerprint)
            (output/(name+'.json')).write_bytes(raw)
            return payload, checked

        before_worker, _ = worker('worker-before')
        now_pbc = _clock(pbc)
        request = dict(sourceChainId=pbc.chain_id, destinationChainId=dbc.chain_id,
                       psc=pbc.contracts['PSC'].address, kssc=dbc.contracts['KSSC'].address,
                       gid=user['gid'], dataId=record['dataId'], action='1', policyVersion='1',
                       authEpoch=pbc.read('TMSC', 'authEpoch')[0], keyEpoch='0', nonce='1',
                       expiresAt=str(int(now_pbc)+30), recipientKeyHash=recipient)
        prepared = provider.call('prepare_request', dict(request=request, signingKeyRef='keyref:user:'+user_label))
        digest = verify_prepared(prepared, request=request, deployment=dep)
        require(pbc.read('PSC', 'getRequest', digest)[0]['status'] == '0', 'fresh PBC request')
        gid = '0x'+keccak(encode(['bytes32', 'address', 'uint256'], [_hex(digest, 32), request['kssc'], int(dbc.chain_id)])).hex()
        before_grant = dbc.read('KSSC', 'grantDetails', gid)[0]
        before_nonce = dbc.read('KSSC', 'nonceConsumed', request['gid'], request['nonce'])[0]
        require(before_grant['exists'] is False and before_nonce is False, 'fresh grant/nonce')
        native_request = pbc.submit('relay', 'PSC', 'requestAccess', request, prepared['signature'], user['bundle'])
        require(native_request.success is True, 'native request status')
        forward = _event(native_request, pbc.contracts['PSC'], 'AccessForwarded')
        request_log = _event(native_request, pbc.contracts['LSC'], 'LogRecorded')
        require(int(request_log['logIndex']) < int(forward['logIndex']), 'request log before forward')
        record_state = pbc.read('PSC', 'getRequest', digest, block=_block(native_request))[0]
        require(record_state['status'] == '1' and record_state['decidedAt'] == native_request.timestamp
                and record_state['requestLogId'] == forward['fields']['requestLogId']
                and record_state['outcomeLogId'] == '0'
                and all(record_state[k] == request[k] for k in ('gid', 'dataId', 'destinationChainId', 'kssc', 'expiresAt')), 'PBC forwarded state')
        code, records = pbc.read('TMSC', 'checkCredentials', request['gid'], user['bundle'], native_request.timestamp, block=_block(native_request))
        frozen_validate('CredentialRecords', records)
        f = forward['fields']
        require(code == '0' and f['requestDigest'] == digest and f['verifiedAttributes'] == records
                and f['credentialDigest'] == record_state['credentialDigest'] == credential_digest(records)
                and all(f[k] == request[k] for k in ('gid', 'dataId', 'destinationChainId', 'kssc', 'expiresAt')), 'PBC historical credential/event join')
        events = _normalized(native_request, pbc, 'LSC')+_normalized(native_request, pbc, 'PSC')
        require([e['type'] for e in events] == ['REQUEST_LOGGED', 'PBC_DECIDED'], 'request trace')
        decision = None
        if repaired:
            offered = provider.call('collect_checkpoint', {})
            cp = offered['checkpoint']; source = _source(pbc, cp['sourceBlockNumber'], cp['sourceBlockHash'])
            checkpoint = verify_checkpoint(offered, deployment=dep, source_block=source,
                                           auth_epoch=pbc.read('TMSC', 'authEpoch', block=source)[0],
                                           policy_version=pbc.read('PSC', 'policyVersion', block=source)[0], dbc_now=_clock(dbc),
                                           current_checkpoint=dbc.read('KSSC', 'currentCheckpoint'), request_block_number=native_request.block_number)
            accepted = dbc.submit('relay', 'KSSC', 'acceptState', checkpoint, offered['signatures'])
            expected_cp_event = {k: checkpoint[k] for k in ('sequence', 'authEpoch', 'policyVersion', 'keyEpoch', 'witnessSetVersion',
                                                           'sourceBlockNumber', 'sourceBlockHash', 'expiresAt')}
            require(accepted.success is True and _event(accepted, dbc.contracts['KSSC'], 'StateAccepted')['fields'] == expected_cp_event
                    and dbc.read('KSSC', 'currentCheckpoint', block=_block(accepted)) == [True, checkpoint], 'checkpoint acceptance native join')
            offered = provider.call('collect_decision', dict(requestDigest=digest))
            current = dbc.read('KSSC', 'currentCheckpoint'); require(current == [True, checkpoint], 'current checkpoint stability')
            source = _source(pbc, checkpoint['sourceBlockNumber'], checkpoint['sourceBlockHash'])
            code, historical_records = pbc.read('TMSC', 'checkCredentials', request['gid'], user['bundle'], str(_quantity(source['timestamp'])), block=source)
            decision = verify_decision(offered, request=request, request_digest=digest, deployment=dep, checkpoint=checkpoint,
                                       source_block=source, dbc_now=_clock(dbc), pbc_now=_clock(pbc), request_block_number=native_request.block_number,
                                       native_records=historical_records, credentials_code=code,
                                       policy_allowed=dbc.read('ACSC', 'evaluate', request['dataId'], historical_records)[0],
                                       nonce_consumed=dbc.read('KSSC', 'nonceConsumed', request['gid'], request['nonce'])[0])
            require(decision['decision']['result'] == ('1' if expected_allow else '0'), 'expected witness decision')
            records = decision['credentialRecords']
            grant_method = 'consumeDecision'
            grant_arguments = (request, {k: decision[k] for k in ('decision', 'signatures')}, records)
        else:
            require(dbc.read('ACSC', 'evaluate', request['dataId'], records) == [expected_allow], 'expected native policy')
            grant_method = 'policyEnf'
            grant_arguments = (dict(pbcRequestId=digest, gid=request['gid'], dataId=request['dataId'], action='1'), records)
        if subject_substitution is not None:
            from evaluation.subject_substitution import collect_subject_substitution, execute_subject_completion
            forwarded = dict(pbcRequestId=digest, gid=request['gid'], dataId=request['dataId'], action=request['action'])
            proof, pre_release = collect_subject_substitution(pbc, dbc, deployment=dep, request=request, prepared=prepared,
                original_native=native_request, original_bundle=user['bundle'], forwarded=forwarded, records=records, decision=decision,
                target_gid=subject_substitution, grant_id=gid, worker_snapshot=worker_snapshot,
                output=output/'subject-substitution')
            result.update(ok=proof['ok'], scope='C-E2 subject pre-release stage; full case and gate incomplete',
                          subjectSubstitution=proof, delivery='unknown')
            if subject_completion:
                target_label = next(label for label, value in USERS.items() if value == subject_substitution)
                completion = execute_subject_completion(pbc, dbc, provider, deployment=dep, pre_release=pre_release,
                    ciphertext_digest=cd, original_label=user_label, target_label=target_label,
                    worker_snapshot=worker_snapshot, output=output/'subject-completion')
                result.update(ok=proof['ok'] and completion['ok'], subjectCompletion=completion,
                              scope='C-E2 subject pre-release and paper completion stages; separate controls and gate apply')
            return result
        native_dbc = dbc.submit('relay', 'ACSC', grant_method, *grant_arguments)
        require(native_dbc.success is True, 'native policy status')
        access = _event(native_dbc, dbc.contracts['ACSC'], 'AccessLog')['fields']
        expected_access = dict(requestRef=digest, gid=request['gid'], dataId=request['dataId'], allowed=expected_allow,
                               code='0' if expected_allow else '9', credentialDigest=credential_digest(records), grantId=gid if expected_allow else ZERO,
                               submitter=dep['fixture']['relay']['address'])
        require(all(access[k] == v for k, v in expected_access.items()), 'native access log reason/bindings')
        grant = dbc.read('KSSC', 'grantDetails', gid, block=_block(native_dbc))[0]
        nonce = dbc.read('KSSC', 'nonceConsumed', request['gid'], request['nonce'], block=_block(native_dbc))[0]
        ledger_checks = {}
        native_events = _normalized(native_dbc, dbc, 'KSSC')
        if not expected_allow:
            require(grant == before_grant and nonce is before_nonce and not native_events, 'denial grant/nonce rollback')
            require(pbc.read('PSC', 'getRequest', digest)[0] == record_state, 'denial remains pending')
            after_worker, _ = worker('worker-after')
            require(after_worker == before_worker, 'denial no worker release')
            ledger_checks = dict(DBC_POLICY_DENIAL_LOGGED=True, NONCE_UNCHANGED=True)
        else:
            expiry = min(int(request['expiresAt']), int(decision['decision']['expiresAt'])) if repaired else int(native_dbc.timestamp)+30
            expected_grant = dict(exists=True, allowed=True, requestDigest=digest, dataId=request['dataId'], gid=request['gid'], keyEpoch='0',
                                  expiresAt=str(expiry), recipientKeyHash=recipient if repaired else ZERO, issuedAt=native_dbc.timestamp)
            require(grant == expected_grant and nonce is repaired and int(native_dbc.timestamp) < expiry, 'native grant/nonce/expiry')
            ge = _event(native_dbc, dbc.contracts['KSSC'], 'GrantIssued')['fields']
            expected_ge = dict(grantId=gid, requestDigest=digest, gid=request['gid'], dataId=request['dataId'], keyEpoch='0',
                               expiresAt=str(expiry), recipientKeyHash=recipient if repaired else ZERO, nonceConsumed=repaired, nonce=request['nonce'] if repaired else '0')
            require(ge == expected_ge and len(native_events) == 1, 'grant event/state join')
            events += native_events
            if nonce_replay:
                from evaluation.request_replay import execute_request_replay
                execute_request_replay(pbc, dbc, deployment=dep, request=request, grant_id=gid,
                                       method=grant_method, arguments=grant_arguments, original_grant=native_dbc,
                                       worker_snapshot=worker_snapshot, output=output/'nonce-replay')
            require(int(_clock(dbc)) < expiry and pbc.read('RSC', 'recipientKeyHash', request['gid']) == [recipient], 'release live grant/recipient')
            response = provider.call('release', dict(grantId=gid))
            require(all(response[k] == v for k, v in dict(requestDigest=digest, grantId=gid, dataId=request['dataId'],
                                                         keyEpoch='0', ciphertextDigest=cd, recipientKeyHash=recipient).items()), 'release native/record binding')
            after_worker, checked = worker('worker-after')
            row = checked.check_response(response); worker_events = checked.events_for(gid)
            expected_worker_events = ['RELEASE_INTENT', 'RELEASE_SENT']+(['RELEASE_SENT'] if recovery_point == 'after_send' else [])
            expected_attempts = 2 if recovery_point == 'after_send' else 1
            require(row['gid'] == request['gid'] and row['grantExpiresAt'] == grant['expiresAt']
                    and int(grant['issuedAt']) <= int(row['createdAt']) < expiry
                    and [e['type'] for e in worker_events] == expected_worker_events
                    and row['sendAttempts'] == expected_attempts and row['completedAttempts'] == 1
                    and all(int(grant['issuedAt']) <= int(e['timestamp']) <= int(_clock(dbc)) and int(e['timestamp']) < expiry for e in worker_events),
                    'worker native expiry/time/attempt join')
            require(after_worker['events'] == before_worker['events']+worker_events
                    and len(after_worker['releases']) == len(before_worker['releases'])+1
                    and all(r in after_worker['releases'] for r in before_worker['releases']), 'worker exact delta')
            events += worker_events
            finished = provider.call('finish_decryption', dict(response=response, userKeyRef='keyref:user:'+user_label))
            require(finished['decryptable'] is True and finished['dataId'] == request['dataId']
                    and finished['ciphertextDigest'] == cd, 'symbolic completion')
            outcome_digest = '0x'+keccak(json.dumps(response, sort_keys=True, separators=(',', ':')).encode()).hex()
            if repaired:
                attested = provider.call('attest_grant', dict(grantId=gid)); receipt = attested['receipt']
                signed_digest('GrantReceipt', receipt, attested['signatures'][0], dep['fixture']['witnessSet']['witnesses'][0], pbc.chain_id, request['psc'])
                receipt_block = _source(dbc, receipt['dbcBlockNumber'], receipt['dbcBlockHash'])
                require(dbc.read('KSSC', 'grantDetails', gid, block=receipt_block) == [grant], 'attested native grant')
                require(all(receipt[k] == v for k, v in dict(requestDigest=digest, grantId=gid, gid=request['gid'], dataId=request['dataId'],
                                                            keyEpoch='0', grantExpiresAt=grant['expiresAt'], witnessSetVersion='1',
                                                            dbcChainId=dbc.chain_id, kssc=request['kssc']).items()), 'attested receipt joins')
                outcome_method = 'reportAttestedOutcome'
                outcome_arguments = (digest, outcome_digest, receipt, attested['signatures'])
                outcome = pbc.submit('relay', 'PSC', outcome_method, *outcome_arguments)
                event_name = 'AttestedOutcomeRecorded'
            else:
                outcome_method = 'reportOutcome'
                outcome_arguments = (digest, gid, outcome_digest)
                outcome = pbc.submit('relay', 'PSC', outcome_method, *outcome_arguments); event_name = 'OutcomeRecorded'
            oe = _event(outcome, pbc.contracts['PSC'], event_name)['fields']
            require(outcome.success is True and oe['requestDigest'] == digest and oe['grantId'] == gid
                    and oe['outcomeDigest'] == outcome_digest, 'outcome native event')
            events += _normalized(outcome, pbc, 'PSC')
        observed = dict(adapterMode='symbolic', events=events, error=None if expected_allow else 'POLICY_DENIED', ledgerChecks=ledger_checks)
        fixture = dict(requestDigest=digest, grantId=gid, gid=request['gid'], dataId=request['dataId'], kssc=request['kssc'],
                       destinationChainId=dbc.chain_id, recipientKeyHash=recipient if repaired else ZERO, keyEpoch='0')
        # Crash mechanics in a chosen completion cannot establish unspecified
        # paper durability. Keep the frozen paper-crash classification unproved.
        classification = 'REPAIR_SUPPORTED' if repaired else ('BLOCKED' if recovery_point is not None else 'SUPPORTED')
        scenario = dict(adapterMode='symbolic', fixture=fixture, expectedError=observed['error'], expectedClass=classification,
                        expectedEvents=['REQUEST_LOGGED', 'PBC_DECIDED']+(['DBC_AUTHORIZED', 'RELEASE_INTENT', 'RELEASE_SENT', 'OUTCOME_RECORDED'] if expected_allow else []),
                        expectedLedgerChecks=list(ledger_checks))
        oracle = evaluate(scenario, observed); require(oracle['ok'], 'independent oracle')
        if duplicate_outcome:
            from evaluation.duplicate_outcome import execute_duplicate_outcome
            execute_duplicate_outcome(pbc, dbc, deployment=dep, grant_id=gid, method=outcome_method,
                                      arguments=outcome_arguments, original_outcome=outcome,
                                      worker_snapshot=worker_snapshot, output=output/'duplicate-outcome')
        result.update(ok=True, observed=observed, oracle=oracle)
        return result
    except Exception as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now()
        (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
