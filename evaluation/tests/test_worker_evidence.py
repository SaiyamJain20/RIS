"""Hand-written redacted worker snapshots: sensitivity, never live evidence.

These catch accepting foreign deployment logs, fabricated aggregate counts,
send-before-intent and changing the cached capability/recipient bindings.
"""
import copy
import importlib

import pytest

FP = 'ab'*32
REQUEST = '0x'+'11'*32
GRANT = '0x'+'22'*32
GID = '0x'+'33'*20
DATA = '0x'+'44'*32
CIPHER = '0x'+'55'*32
RECIPIENT = '0x'+'66'*32
# Keccak-256 of the literal 32-byte zero test capability, not an issued token.
TOKEN_DIGEST = '0x290decd9548b62a8d60345a988386fc84ba6bc95484008f6362f93160ef3e563'


def snapshot():
    identity = dict(requestDigest=REQUEST, grantId=GRANT, gid=GID, dataId=DATA)
    return {'schemaVersion':'hmbc-worker-log/v0','adapterMode':'symbolic',
            'deploymentFingerprint':FP,'note':'attempted send; unknown delivery',
            'events':[dict(type='RELEASE_INTENT', timestamp='100', **identity),
                      dict(type='RELEASE_SENT', timestamp='101', **identity)],
            'releases':[dict(ciphertextDigest=CIPHER, recipientKeyHash=RECIPIENT,
                             keyEpoch='0', tokenDigest=TOKEN_DIGEST, grantExpiresAt='130',
                             createdAt='100', delivery='unknown', sendAttempts=1,
                             completedAttempts=1, **identity)],
            'counts':{'releaseIntentCount':'1','releaseSentCount':'1'}}


def log(payload=None):
    try: module = importlib.import_module('evaluation.worker_evidence')
    except ModuleNotFoundError: pytest.fail('Independent C-E1 worker evidence checks are absent')
    return module.WorkerLog(snapshot() if payload is None else payload, fingerprint=FP)


def response():
    return dict(schemaVersion='v1', adapterMode='symbolic', requestDigest=REQUEST,
                grantId=GRANT, dataId=DATA, ciphertextDigest=CIPHER,
                recipientKeyHash=RECIPIENT, keyEpoch='0',
                responseEnvelope={'kind':'symbolic-partial/v1','token':'0x'+'00'*32})


def test_checked_snapshot_preserves_attempts_and_delivery_uncertainty():
    original=snapshot(); observed=log(original)
    assert observed.events_for(GRANT)==original['events']
    assert observed.check_response(response())['delivery']=='unknown'
    original['events'].clear()
    assert len(observed.events_for(GRANT))==2


def test_empty_snapshot_is_no_release_and_cannot_authorize_a_response():
    p=snapshot();p['events']=[];p['releases']=[]
    p['counts']={'releaseIntentCount':'0','releaseSentCount':'0'}
    observed=log(p);assert observed.events_for(GRANT)==[]
    with pytest.raises(ValueError):observed.check_response(response())


@pytest.mark.parametrize('change',['fingerprint','mode','count','send-count','bool-count',
                                  'completed','event-binding','order','duplicate-intent',
                                  'duplicate-grant','unknown-event','raw-token','expiry','timestamp'])
def test_inconsistent_or_unredacted_snapshot_is_refused(change):
    p=snapshot();r=p['releases'][0]
    if change=='fingerprint':p['deploymentFingerprint']='cd'*32
    if change=='mode':p['adapterMode']='abe-real'
    if change=='count':p['counts']['releaseSentCount']='2'
    if change=='send-count':r['sendAttempts']=2
    if change=='bool-count':r['sendAttempts']=True
    if change=='completed':r['completedAttempts']=2
    if change=='event-binding':p['events'][1]['gid']='0x'+'77'*20
    if change=='order':p['events'].reverse()
    if change=='duplicate-intent':p['events'].append(copy.deepcopy(p['events'][0]))
    if change=='duplicate-grant':p['releases'].append(copy.deepcopy(r))
    if change=='unknown-event':p['events'][1]['type']='DELIVERED'
    if change=='raw-token':r['token']='0x'+'00'*32
    if change=='expiry':r['grantExpiresAt']='100'
    if change=='timestamp':p['events'][0]['timestamp']='0100'
    with pytest.raises(ValueError):log(p)


@pytest.mark.parametrize('key,value',[('requestDigest','0x'+'77'*32),('dataId','0x'+'77'*32),
                                     ('recipientKeyHash','0x'+'77'*32),('ciphertextDigest','0x'+'77'*32),
                                     ('keyEpoch','1'),('token','0x'+'77'*32)])
def test_response_must_match_redacted_cache_commitments(key,value):
    r=response()
    if key=='token':r['responseEnvelope']['token']=value
    else:r[key]=value
    with pytest.raises(ValueError):log().check_response(r)


def test_retry_is_second_attempt_with_one_intent_and_same_cache():
    p=snapshot();p['events'].append(dict(p['events'][1],timestamp='102'))
    p['releases'][0]['sendAttempts']=2;p['releases'][0]['completedAttempts']=1
    p['counts']['releaseSentCount']='2'
    observed=log(p)
    assert [e['type'] for e in observed.events_for(GRANT)]==['RELEASE_INTENT','RELEASE_SENT','RELEASE_SENT']
    assert observed.check_response(response())['completedAttempts']==1
