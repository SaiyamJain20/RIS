"""Independent E02 trust-freshness oracles (SL5) for the paper-derived HMBC reconstruction.

Expectations: frozen rows E02-wrong-issuer-* and E02-signed-list-rollback-*, SPEC4/E02 and the pinned
ledger (933d2a7) TMSC: _authorizeUpdate checks a known authority, then an issuer-scoped CA-admin caller
(UNAUTHORIZED_CALLER 16, TMSC.sol:181; baseline in every profile, D-record N-1, not a repair), then the
issuer root signature (not paper-minimal); _checkFreshness runs only in repaired-e (a version not
strictly above the current one, or an expired list: STALE_ANCHOR 5, TMSC.sol:189-192). Paper profiles
treat the latest appended list as current, so replaying the older signed CRL starts a new generation
without the revocation (SPEC_GAP). A credential revoked in the current generation gives REVOKED (19);
PSC.requestAccess then emits AccessDenied without a request record. Tested reconstruction results;
an authorized issuer-scoped administrator is the actor, so nothing here is an HMBC exploit.
"""
import copy

from evaluation.access_artifacts import require
from evaluation.bootstrap import signed_digest
from evaluation.oracles.provenance import _idle

PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
_STATE = ('anchors', 'authEpoch', 'revoked', 'credentials', 'logs')


def _state(snapshot):
    return {k: copy.deepcopy(snapshot[k]) for k in _STATE}


def _worker(*snapshots):
    first = snapshots[0]['worker']; _idle(first)
    require(first.get('instantiated') is False and all(s['worker'] == first for s in snapshots),
            'verified never-instantiated worker, unchanged (no SL5 step is a worker operation)')


def _signed_list(item, *, authority, digest, pbc_chain_id, tmsc):
    """A RevocationList item signed by the authority root under the evaluator's own EIP-712 encoder (HMBCTrust, PBC TMSC)."""
    require(isinstance(item, dict) and item.get('kind') == 'RevocationList' and item.get('call') == 'TMSC.updateRevocationList'
            and item.get('signer') == authority and item['list'].get('authority') == authority, 'revocation list item for the authority')
    require(signed_digest('RevocationList', item['list'], item['signature'], authority, pbc_chain_id, tmsc) == digest,
            'list signature recovers to the authority root (own EIP-712 encoder)')
    return item['list']


def _update_event(events, *, authority, body, generation, digest, epoch):
    require([e['name'] for e in events] == ['LogRecorded', 'TrustAnchorUpdated'], 'trust update log then anchor event')
    log, event = events[0]['fields'], events[1]['fields']
    require(log['kind'] == '2', 'LSC TRUST_UPDATE log')
    require(all(event[k] == v for k, v in dict(authority=authority, kind='1', version=body['version'], validUntil=body['validUntil'],
                                               generation=generation, contentDigest=digest, authEpoch=epoch).items()),
            'TrustAnchorUpdated binds authority, version, generation, digest and authEpoch')


def _request_logged(request, replayed):
    """REQUEST_ACCESS carries the current authEpoch (A1-0064) and is logged before validation (V-A5)."""
    events = request['events']
    require(request['authEpoch'] == replayed['authEpoch'], 'request carries the current authEpoch')
    require(len(events) == 2 and events[0]['name'] == 'LogRecorded' and events[0]['fields']['kind'] == '3'
            and events[0]['fields']['subject'] == request['digest'], 'request logged before validation')


def check_wrong_issuer(*, profile, before, after, item, item_digest, authority, membership, simulated_generation,
                       success, rejection_code, receipt_events, pbc_chain_id, tmsc):
    """An H1 CA-admin submits a valid H2 list: rejected UNAUTHORIZED_CALLER in every profile, nothing changes."""
    require(profile in PROFILES, 'E reconstruction profile')
    _worker(before, after)
    body = _signed_list(item, authority=authority, digest=item_digest, pbc_chain_id=pbc_chain_id, tmsc=tmsc)
    anchor = before['anchors'][authority]
    require(anchor['published'] is True and body['version'] == str(int(anchor['version'])+1),
            'fresh next-version list (only the caller is wrong)')
    require(membership == dict(wrongAdmin=False, rightAdmin=True), 'H1 admin is not, H2 admin is, an H2 CA-admin')
    require(simulated_generation == str(int(anchor['generation'])+1), 'the same call from the H2 admin would be accepted (eth_call only)')
    require(success is False and rejection_code == '16' and receipt_events == [], 'mined Rejected(UNAUTHORIZED_CALLER) without events')
    require(_state(after) == _state(before), 'anchors, authEpoch, revocations, credentials and logs unchanged')
    return dict(ok=True, classification='SUPPORTED', error='UNAUTHORIZED_CALLER', outcome='REJECT', delivery='unknown',
                qualification='issuer-scoped CA-admin caller restriction (TMSC.sol:181) holds in every profile; baseline '
                              'behaviour (D-record N-1), not a repair; tested reconstruction result')


def check_list_rollback(*, profile, initial, installed, replayed, new_item, new_digest, old_item, old_digest, install_success,
                        install_events, replay_success, replay_code, replay_events, replay_timestamp, request, alice, serial,
                        pbc_chain_id, tmsc):
    """Install CRL v2 revoking Alice, replay the bootstrap CRL v1, then Alice requests access with the current authEpoch."""
    require(profile in PROFILES, 'E reconstruction profile')
    _worker(initial, installed, replayed)
    authority = old_item['signer']
    old = _signed_list(old_item, authority=authority, digest=old_digest, pbc_chain_id=pbc_chain_id, tmsc=tmsc)
    new = _signed_list(new_item, authority=authority, digest=new_digest, pbc_chain_id=pbc_chain_id, tmsc=tmsc)
    a0, a1, a2 = (s['anchors'][authority] for s in (initial, installed, replayed))
    g0, e0 = int(a0['generation']), int(initial['authEpoch'])
    # The replayed list is the old, correctly signed bootstrap list, still within its validity.
    require(a0['published'] is True and old['version'] == a0['version'] and a0['contentDigest'] == old_digest
            and serial not in old['revokedSerials'], 'old list is the installed bootstrap list and does not revoke')
    require(int(old['validUntil']) > int(replay_timestamp), 'old list still valid at replay (only version order can reject)')
    require(initial['revoked'] == {serial: False} and initial['credentials']['code'] == '0', 'Alice valid before the new list')
    # INSTALL_NEW_LIST
    require(new['version'] == str(int(old['version'])+1) and new['revokedSerials'] == [serial], 'new list: next version, revokes Alice')
    require(install_success is True, 'new list accepted')
    _update_event(install_events, authority=authority, body=new, generation=str(g0+1), digest=new_digest, epoch=str(e0+1))
    require(a1 == dict(a1, published=True, version=new['version'], validUntil=new['validUntil'], generation=str(g0+1), contentDigest=new_digest)
            and installed['authEpoch'] == str(e0+1) and installed['revoked'] == {serial: True}
            and installed['credentials'] == dict(code='19', records=[]), 'v2 installed: Alice REVOKED')
    require(installed['logs']['pbc'] == initial['logs']['pbc']+install_events and installed['logs']['dbc'] == initial['logs']['dbc'],
            'only the install delta')
    events = request['events']
    if profile != 'repaired-e':
        require(replay_success is True and replay_code is None, 'paper accepts the older appended list')
        _update_event(replay_events, authority=authority, body=old, generation=str(g0+2), digest=old_digest, epoch=str(e0+2))
        require(a2 == dict(a2, published=True, version=old['version'], validUntil=old['validUntil'], generation=str(g0+2),
                           contentDigest=old_digest) and replayed['authEpoch'] == str(e0+2) and replayed['revoked'] == {serial: False}
                and replayed['credentials']['code'] == '0', 'v1 current again: Alice no longer revoked (rollback)')
        require(replayed['logs']['pbc'] == installed['logs']['pbc']+replay_events and replayed['logs']['dbc'] == installed['logs']['dbc'],
                'only the replay delta')
        _request_logged(request, replayed)
        forwarded = events[1]
        require(forwarded['name'] == 'AccessForwarded' and forwarded['fields']['requestDigest'] == request['digest']
                and forwarded['fields']['gid'] == alice and request['state']['status'] == '1', 'Alice request forwarded')
        rows = [r for r in forwarded['fields']['verifiedAttributes'] if r['kind'] == '1' and r['serial'] == serial and r['issuer'] == authority]
        require(len(rows) == 1 and rows[0]['anchorVersion'] == old['version'], 'credential verified against the rolled-back CRL version')
        return dict(ok=True, classification='SPEC_GAP', error=None, outcome='ACCEPT', delivery='unknown', rolledBack=True,
                    qualification='paper profiles treat the latest appended list as current: an authorized issuer-scoped admin '
                                  'replaying the older correctly signed CRL removes a revocation; reconstruction specification gap')
    require(replay_success is False and replay_code == '5' and replay_events == [], 'mined Rejected(STALE_ANCHOR) without events')
    require(_state(replayed) == _state(installed), 'v2 retained: anchors, authEpoch, revocation, credentials and logs unchanged')
    _request_logged(request, replayed)
    denied = events[1]
    require(denied['name'] == 'AccessDenied' and denied['fields'] == dict(requestDigest=request['digest'], claimedGid=alice, code='19',
                                                                          requestLogId=events[0]['fields']['logId'])
            and request['state']['status'] == '0' and request['denialCount'] == '1', 'Alice request denied REVOKED under v2')
    return dict(ok=True, classification='REPAIR_SUPPORTED', error='STALE_ANCHOR', outcome='REJECT', delivery='unknown', rolledBack=False,
                qualification='repaired-e requires strictly increasing list versions (TMSC.sol:189-190); the replay is rejected '
                              'and v2 retained, so the revoked credential stays revoked')
