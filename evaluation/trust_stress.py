"""Public E02 trust-freshness collectors (SL5) for the paper-derived HMBC reconstruction.

Variants follow the frozen catalog steps exactly, on a fresh second deployment (D2):
- wrong-issuer (WRONG_ISSUER_UPDATE): the owner TEST-ONLY producer (ledger/tools/sign_list.sh, A1-0034)
  signs a fresh next-version H2 CRL with the H2 root; an eth_call from the H2 CA-admin (never mined)
  shows the list would be accepted; the H1 CA-admin then submits it and must get UNAUTHORIZED_CALLER.
- signed-list-rollback (INSTALL_NEW_LIST > REPLAY_OLD_LIST > REQUEST_ACCESS): the producer signs H1 CRL
  v2 revoking Alice's certificate serial; the H1 CA-admin installs it, then resubmits the bootstrap's
  own correctly signed H1 CRL v1; Alice then requests access with the CURRENT TMSC.authEpoch (A1-0064).
No step is a worker operation (only prepare_request reaches the adapter), so the D2 worker must stay a
verified never-instantiated record, re-observed after every catalog step (D49). A non-zero producer
exit is a failed trial (sha256 and first line only). The caller owns fresh deployment/state, controls,
plan ACKs and source stability. Results are tested reconstruction results, never HMBC exploits.
"""
import copy
import hashlib
from pathlib import Path

from evaluation.access_artifacts import require, verify_prepared
from evaluation.access_execution import _block, _clock
from evaluation.bootstrap import USERS, frozen_validate, signed_digest, strict_json
from evaluation.manifests import now
from evaluation.native import _quantity
from evaluation.oracles.provenance import _idle
from evaluation.oracles.trust import check_list_rollback, check_wrong_issuer
from evaluation.relay_stress import _Context, _baseline
from evaluation.subject_substitution import _decode, _save

VARIANTS = ('wrong-issuer', 'signed-list-rollback')
PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
# Per-variant producer arguments (fixed by the plan template): (authority, revoked serials).
PRODUCED = {'wrong-issuer': ('H2', []), 'signed-list-rollback': ('H1', ['101'])}
SERIAL = '101'


class _Steps:
    def __init__(self, ctx):
        self.ctx, self.first, self.rows = ctx, None, []

    def check(self, step, observed=None):
        observed = self.ctx.worker() if observed is None else observed
        _idle(observed)
        require(observed['instantiated'] is False and (self.first is None or observed == self.first),
                'verified never-instantiated worker after '+step)
        self.first = self.first or copy.deepcopy(observed)
        self.rows.append(dict(step=step, worker='never-instantiated (verified)'))


def _authority(dep, hid):
    found = [a for a in dep['fixture']['authorities'] if a['id'] == hid]
    require(len(found) == 1 and found[0]['caAdminKeyLabel'] == hid+'-ca-admin' and found[0]['rootKeyLabel'] == hid+'-root',
            'fixture authority '+hid)
    return found[0]


def _produce(ctx, sign_list, variant, deployment_bytes):
    """Run the owner signed-list producer once and check its artifact before any use."""
    pbc, dep = ctx.pbc, ctx.dep
    answer = sign_list(variant)
    require(isinstance(answer, dict) and set(answer) == {'exitCode', 'output'} and type(answer['exitCode']) is int
            and isinstance(answer['output'], bytes), 'signed-list producer command record')
    digest = hashlib.sha256(answer['output']).hexdigest()
    if answer['exitCode'] != 0:
        first = answer['output'].split(b'\n', 1)[0].decode('utf-8', 'replace')[:240]
        _save(ctx.output, 'sign-list-refusal', dict(exitCode=answer['exitCode'], outputSha256=digest, firstLine=first,
                                                    note='failed trial: non-zero producer exit; output kept only as sha256 and first line'))
        raise ValueError('Owner signed-list producer exited '+str(answer['exitCode'])+' (failed trial; output sha256 '+digest+')')
    doc = strict_json(answer['output'])
    hid, revoked = PRODUCED[variant]; auth = _authority(dep, hid)
    p = dep['chains']['pbc']
    require(isinstance(doc, dict) and set(doc) == {'schemaVersion', 'producer', 'testOnly', 'binding', 'item'}
            and doc['schemaVersion'] == 'hmbc-ledger-signed-list/v0' and doc['testOnly'] is True, 'TEST-ONLY signed-list artifact')
    b = doc['binding']
    require(b.get('pbcChainId') == pbc.chain_id == p['chainId'] and b.get('tmsc') == p['contracts']['TMSC'] and b.get('rsc') == p['contracts']['RSC']
            and b.get('deploymentSha256') == hashlib.sha256(deployment_bytes).hexdigest() and b.get('profile') == dep['profileEnum'],
            'producer bound to this deployment')
    item = doc['item']
    require(set(item) == {'kind', 'call', 'submitterRole', 'submitter', 'list', 'signature', 'signer'} and item['kind'] == 'RevocationList'
            and item['call'] == 'TMSC.updateRevocationList' and item['submitterRole'] == hid+'-ca-admin' and item['submitter'] == auth['caAdmins'][0]
            and item['signer'] == auth['root'] and item['list']['authority'] == auth['root'] and item['list']['revokedSerials'] == revoked,
            'producer item for the plan variant')
    current = pbc.read('TMSC', 'revocationListState', auth['root'])[0]
    require(current['published'] is True and item['list']['version'] == str(int(current['version'])+1), 'producer default next version')
    listed = signed_digest('RevocationList', item['list'], item['signature'], auth['root'], p['chainId'], p['contracts']['TMSC'])
    _save(ctx.output, 'signed-list', dict(doc, outputSha256=digest, contentDigest=listed,
                                          label='TEST-ONLY owner producer output (A1-0034); no key material'))
    return item, listed


def _snapshot(ctx, steps, name, roots, step=None):
    pbc, dbc, user = ctx.pbc, ctx.dbc, ctx.user
    with pbc.read_group(tuple(pbc.contracts)) as proxy:
        at = str(_quantity(proxy.block['timestamp']))
        anchors = {r: proxy.read('TMSC', 'revocationListState', r)[0] for r in roots}
        epoch = proxy.read('TMSC', 'authEpoch')[0]
        revoked = {SERIAL: proxy.read('TMSC', 'isRevoked', roots[0], SERIAL)[0]}
        code, records = proxy.read('TMSC', 'checkCredentials', user['gid'], user['bundle'], at)
        logs_pbc = _decode(pbc, proxy.logs())
    with dbc.read_group(tuple(dbc.contracts)) as domain:
        logs_dbc = _decode(dbc, domain.logs())
    payload = dict(anchors=anchors, authEpoch=epoch, revoked=revoked, credentials=dict(code=code, records=records),
                   logs=dict(pbc=logs_pbc, dbc=logs_dbc), worker=ctx.worker(), credentialTime=at)
    _save(ctx.output, name+'-blocks', dict(pbc=proxy.block, dbc=domain.block)); _save(ctx.output, name, payload)
    if step: steps.check(step, payload['worker'])
    return payload


def _mined(ctx, chain, native, sender, role, method, args):
    tx_hash = native.receipt['transactionHash']
    tx = chain.rpc.call('eth_getTransactionByHash', [tx_hash])
    require(tx is not None and tx['hash'] == tx_hash and tx['input'] == chain.contracts[role].calldata(method, *args)
            and tx['to'] == chain.contracts[role].address and tx['from'] == sender and tx['blockHash'] == native.block_hash
            and int(tx['blockNumber'], 16) == int(native.block_number), 'mined call identity/sender/calldata/block')
    return tx


def _wrong_issuer(ctx, sign_list, deployment_bytes):
    pbc, dep = ctx.pbc, ctx.dep
    h1, h2 = _authority(dep, 'H1'), _authority(dep, 'H2')
    steps = _Steps(ctx); steps.check('baseline')
    item, digest = _produce(ctx, sign_list, 'wrong-issuer', deployment_bytes)
    before = _snapshot(ctx, steps, 'before', [h1['root'], h2['root']])
    membership = dict(wrongAdmin=pbc.read('TMSC', 'isCaAdmin', h2['root'], h1['caAdmins'][0])[0],
                      rightAdmin=pbc.read('TMSC', 'isCaAdmin', h2['root'], h2['caAdmins'][0])[0])
    args = [item['list'], item['signature']]
    tmsc = pbc.contracts['TMSC']; latest = pbc.latest_block()
    try:
        raw = pbc.rpc.call('eth_call', [{'from': h2['caAdmins'][0], 'to': tmsc.address, 'data': tmsc.calldata('updateRevocationList', *args)},
                                        latest['number']])
    except RuntimeError as error:
        raise ValueError('Public trust right-admin simulation failed') from error
    simulated = tmsc.decode_return('updateRevocationList', raw)[0]
    _save(ctx.output, 'right-admin-simulation', dict(generation=simulated, sender=h2['caAdmins'][0], block=latest, mined=False,
                                                    note='eth_call only: the same list from the H2 CA-admin would be accepted'))
    _save(ctx.output, 'public-call', dict(method='updateRevocationList', signerRole='H1-ca-admin', arguments=args))
    native = pbc.submit('H1-ca-admin', 'TMSC', 'updateRevocationList', *args, expect_success=False)
    _save(ctx.output, 'stress-transaction', _mined(ctx, pbc, native, h1['caAdmins'][0], 'TMSC', 'updateRevocationList', args))
    code = pbc.rejection_code(native); events = _decode(pbc, native.receipt['logs'])
    after = _snapshot(ctx, steps, 'after', [h1['root'], h2['root']], 'WRONG_ISSUER_UPDATE')
    proof = check_wrong_issuer(profile=dep['profile'], before=before, after=after, item=item, item_digest=digest, authority=h2['root'],
                               membership=membership, simulated_generation=simulated, success=native.success, rejection_code=code,
                               receipt_events=events, pbc_chain_id=pbc.chain_id, tmsc=tmsc.address)
    return dict(proof, workerSteps=steps.rows, timeline=dict(stressTimestamp=native.timestamp))


def _request(ctx):
    """REQUEST_ACCESS by Alice with the CURRENT TMSC.authEpoch (A1-0064); the PBC may forward or deny."""
    pbc, dbc, dep, user = ctx.pbc, ctx.dbc, ctx.dep, ctx.user
    epoch = pbc.read('TMSC', 'authEpoch')[0]
    request = dict(sourceChainId=pbc.chain_id, destinationChainId=dbc.chain_id, psc=pbc.contracts['PSC'].address,
                   kssc=dbc.contracts['KSSC'].address, gid=user['gid'], dataId=ctx.record['dataId'], action='1', policyVersion='1',
                   authEpoch=epoch, keyEpoch='0', nonce='1', expiresAt=str(int(_clock(pbc))+30), recipientKeyHash=ctx.recipient)
    prepared = ctx.provider.call('prepare_request', dict(request=request, signingKeyRef='keyref:user:alice'))
    digest = verify_prepared(prepared, request=request, deployment=dep)
    require(pbc.read('PSC', 'getRequest', digest)[0]['status'] == '0', 'fresh PBC request')
    args = [request, prepared['signature'], user['bundle']]
    native = pbc.submit('relay', 'PSC', 'requestAccess', *args)
    ctx.mined(pbc, native, 'PSC', 'requestAccess', args)
    observed = dict(digest=digest, authEpoch=epoch, request=request, events=_decode(pbc, native.receipt['logs']),
                    state=pbc.read('PSC', 'getRequest', digest, block=_block(native))[0],
                    denialCount=pbc.read('PSC', 'denialCount', digest, block=_block(native))[0],
                    epochAtRequestBlock=pbc.read('TMSC', 'authEpoch', block=_block(native))[0],
                    transactionHash=native.receipt['transactionHash'], timestamp=native.timestamp)
    require(observed['epochAtRequestBlock'] == epoch, 'authEpoch unchanged up to the request block')
    _save(ctx.output, 'request', observed)
    return observed


def _rollback(ctx, sign_list, deployment_bytes, bootstrap):
    pbc, dep, user = ctx.pbc, ctx.dep, ctx.user
    h1, h2 = _authority(dep, 'H1'), _authority(dep, 'H2')
    cert = bootstrap['users']['alice']['certificate']['cert']
    require(cert['issuer'] == h1['root'] and cert['serial'] == SERIAL and cert['gid'] == user['gid'], 'Alice H1 certificate serial 101')
    old = [t for t in bootstrap['trustLists'] if t['kind'] == 'RevocationList' and t['signer'] == h1['root']]
    require(len(old) == 1 and old[0]['submitterRole'] == 'H1-ca-admin', 'one bootstrap H1 CRL')
    old = copy.deepcopy(old[0]); p = dep['chains']['pbc']
    old_digest = signed_digest('RevocationList', old['list'], old['signature'], h1['root'], p['chainId'], p['contracts']['TMSC'])
    _save(ctx.output, 'old-list', dict(item=old, contentDigest=old_digest, source='bootstrap-checked trustLists (installed at bootstrap)'))
    steps = _Steps(ctx); steps.check('baseline')
    initial = _snapshot(ctx, steps, 'initial', [h1['root'], h2['root']])
    new, new_digest = _produce(ctx, sign_list, 'signed-list-rollback', deployment_bytes)
    install_args = [new['list'], new['signature']]
    installed_tx = pbc.submit('H1-ca-admin', 'TMSC', 'updateRevocationList', *install_args)
    _save(ctx.output, 'install-transaction', _mined(ctx, pbc, installed_tx, h1['caAdmins'][0], 'TMSC', 'updateRevocationList', install_args))
    install_events = _decode(pbc, installed_tx.receipt['logs'])
    installed = _snapshot(ctx, steps, 'installed', [h1['root'], h2['root']], 'INSTALL_NEW_LIST')
    paper = dep['profile'] != 'repaired-e'
    replay_args = [old['list'], old['signature']]
    _save(ctx.output, 'public-call', dict(method='updateRevocationList', signerRole='H1-ca-admin', arguments=replay_args,
                                          note='REPLAY_OLD_LIST: the bootstrap H1 CRL, byte-for-byte'))
    replay = pbc.submit('H1-ca-admin', 'TMSC', 'updateRevocationList', *replay_args, expect_success=paper)
    _save(ctx.output, 'stress-transaction', _mined(ctx, pbc, replay, h1['caAdmins'][0], 'TMSC', 'updateRevocationList', replay_args))
    replay_code = None if paper else pbc.rejection_code(replay)
    replay_events = _decode(pbc, replay.receipt['logs'])
    replayed = _snapshot(ctx, steps, 'replayed', [h1['root'], h2['root']], 'REPLAY_OLD_LIST')
    request = _request(ctx)
    steps.check('REQUEST_ACCESS')
    timeline = dict(installTimestamp=installed_tx.timestamp, replayTimestamp=replay.timestamp, requestTimestamp=request['timestamp'],
                    oldListValidUntil=old['list']['validUntil'], newListValidUntil=new['list']['validUntil'])
    _save(ctx.output, 'timeline', timeline)
    proof = check_list_rollback(profile=dep['profile'], initial=initial, installed=installed, replayed=replayed, new_item=new,
                                new_digest=new_digest, old_item=old, old_digest=old_digest, install_success=installed_tx.success,
                                install_events=install_events, replay_success=replay.success, replay_code=replay_code,
                                replay_events=replay_events, replay_timestamp=replay.timestamp, request=request, alice=user['gid'],
                                serial=SERIAL, pbc_chain_id=pbc.chain_id, tmsc=pbc.contracts['TMSC'].address)
    return dict(proof, workerSteps=steps.rows, timeline=timeline)


def execute_trust_stress(pbc, dbc, adapter, *, deployment_bytes, bootstrap, user_label, user, record, policy, variant,
                         worker_snapshot, sign_list, output):
    """Run one frozen SL5 trust-freshness row on a fresh deployment."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None, variant=variant, delivery='unknown',
                  scope='C-E2 SL5 trust freshness; separate controls, plan ACKs and gate apply')
    try:
        dep = strict_json(deployment_bytes); frozen_validate('LedgerDeployment', dep)
        require(variant in VARIANTS and dep['profile'] in PROFILES, 'frozen catalog variant/profile')
        require(dep['interfaceVersion'] == 'v1' and dep['mutations'] == '0', 'baseline deployment')
        require(user_label == 'alice' and user['gid'] == USERS['alice'], 'registered Alice subject')
        require(callable(sign_list) and callable(worker_snapshot), 'runner producer and worker observation callables')
        frozen_validate('CredentialBundle', user['bundle'])
        _baseline(pbc, dbc, dep, user, record, policy)
        ctx = _Context(pbc, dbc, adapter, dep, user, record, worker_snapshot, output)
        proof = _wrong_issuer(ctx, sign_list, deployment_bytes) if variant == 'wrong-issuer' else _rollback(ctx, sign_list, deployment_bytes, bootstrap)
        result.update(proof)
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); _save(output, 'result', result)
