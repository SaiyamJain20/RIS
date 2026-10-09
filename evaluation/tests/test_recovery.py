"""Independent recovery expectations from accepted startup supplement.

Synthetic redacted exports only; these tests cannot establish worker durability.
Breaks: changing cache on retry, accepting premature/late intent, hiding extra
release events, extending expiry, claiming delivery and accepting wrong counts.
"""
import copy
import importlib
import json

import pytest
from evaluation.tests.test_worker_evidence import snapshot,response,FP,GRANT,GID,REQUEST,DATA,RECIPIENT


def examples(point):
    final=snapshot();final['events'][0]['timestamp']='100';final['events'][1]['timestamp']='101'
    before=copy.deepcopy(final);before['events']=[];before['releases']=[]
    before['counts']={'releaseIntentCount':'0','releaseSentCount':'0'}
    crashed=copy.deepcopy(final);crashed['releases'][0]['completedAttempts']=0
    if point=='after_intent':
        crashed['events']=crashed['events'][:1];crashed['releases'][0]['sendAttempts']=0
        crashed['counts']['releaseSentCount']='0'
    else:
        final['events'].append(dict(final['events'][1],timestamp='102'))
        final['releases'][0]['sendAttempts']=2;final['counts']['releaseSentCount']='2'
    grant=dict(exists=True,allowed=True,requestDigest=REQUEST,gid=GID,dataId=DATA,keyEpoch='0',expiresAt='130',recipientKeyHash=RECIPIENT,issuedAt='99')
    return dict(before=before,crashed=crashed,after=final,response=response(),
                crash_response=None if point=='after_intent' else response(),grant=grant,grant_id=GRANT,
                recipient=RECIPIENT,point=point,fingerprint=FP,dbc_now='103')


def check(data):
    assert importlib.util.find_spec('evaluation.recovery') is not None,'Independent C-E2 recovery checks missing'
    return importlib.import_module('evaluation.recovery').check_recovery(**data)


@pytest.mark.parametrize('point',['after_intent','after_send'])
def test_exact_cached_retry_counts_keep_delivery_unknown(point):
    got=check(examples(point))
    assert got['delivery']=='unknown' and got['ok'] is True
    assert got['sendAttempts']==(1 if point=='after_intent' else 2)
    assert got['completedAttempts']==1 and got['originalExpiry']=='130'
    assert '"token"' not in json.dumps(got)


@pytest.mark.parametrize('change',['crash-completed','retry-completed','cache-token','cache-cipher','expiry','created-at',
                                  'extra-intent','extra-send','different-crash-response','future-event','pre-grant-intent',
                                  'response-data','recipient','native-expiry','missing-crash-response','delivery','drop-before'])
def test_reconstruction_faults_cannot_match_recovery_oracle(change):
    data=examples('after_send');r=data['after']['releases'][0]
    if change=='crash-completed':data['crashed']['releases'][0]['completedAttempts']=1
    if change=='retry-completed':r['completedAttempts']=2
    if change=='cache-token':data['crashed']['releases'][0]['tokenDigest']='0x'+'77'*32
    if change=='cache-cipher':data['crashed']['releases'][0]['ciphertextDigest']='0x'+'77'*32
    if change=='expiry':r['grantExpiresAt']='131'
    if change=='created-at':r['createdAt']='101';data['after']['events'][0]['timestamp']='101'
    if change=='extra-intent':data['after']['events'].append(copy.deepcopy(data['after']['events'][0]))
    if change=='extra-send':data['after']['events'].append(dict(data['after']['events'][-1]));r['sendAttempts']=3;data['after']['counts']['releaseSentCount']='3'
    if change=='different-crash-response':data['crash_response']['responseEnvelope']['token']='0x'+'77'*32
    if change=='future-event':data['after']['events'][-1]['timestamp']='104'
    if change=='pre-grant-intent':data['grant']['issuedAt']='101'
    if change=='response-data':data['response']['dataId']='0x'+'77'*32
    if change=='recipient':data['recipient']='0x'+'77'*32
    if change=='native-expiry':data['grant']['expiresAt']='129'
    if change=='missing-crash-response':data['crash_response']=None
    if change=='delivery':r['delivery']='delivered'
    if change=='drop-before':data['before']=copy.deepcopy(data['crashed'])
    with pytest.raises(ValueError):check(data)


def test_paper_zero_native_recipient_still_requires_registered_recipient():
    data=examples('after_intent');data['grant']['recipientKeyHash']='0x'+'00'*32
    assert check(data)['ok']
    data['recipient']='0x'+'77'*32
    with pytest.raises(ValueError):check(data)


def test_late_observation_is_allowed_but_each_actual_send_remains_before_expiry():
    data=examples('after_send');data['dbc_now']='140'
    assert check(data)['ok']
    data['after']['events'][-1]['timestamp']='130'
    with pytest.raises(ValueError):check(data)
