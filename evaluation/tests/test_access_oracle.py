import copy
import json
from pathlib import Path
import pytest
from evaluation.oracles.access import evaluate

SCENARIOS=json.loads(Path('evaluation/scenarios/e_positive.json').read_text())


def trace(scenario):
    f=scenario['fixture']
    events=[]
    for index,name in enumerate(scenario['expectedEvents']):
        event={'type':name,'requestDigest':f['requestDigest'],'timestamp':str(100+index)}
        if name in ('DBC_AUTHORIZED','RELEASE_INTENT','RELEASE_SENT','OUTCOME_RECORDED'):
            event.update({k:f[k] for k in ('grantId','gid','dataId')})
        if name=='DBC_AUTHORIZED': event.update({k:f[k] for k in ('kssc','destinationChainId','recipientKeyHash','keyEpoch')})
        events.append(event)
    return {'adapterMode':'symbolic','events':events,'error':scenario['expectedError']}


def test_legitimate_and_denial_controls_accept_expected_traces():
    for s in SCENARIOS: assert evaluate(s,trace(s))['ok']


def test_deny_everything_fails_positive_control():
    s=next(s for s in SCENARIOS if s['fixture']['actor']=='Alice')
    assert not evaluate(s,{'adapterMode':'symbolic','events':[],'error':'POLICY_DENIED'})['ok']


def test_grant_everything_fails_denial_control():
    bob=next(s for s in SCENARIOS if s['fixture']['actor']=='Bob')
    alice=next(s for s in SCENARIOS if s['fixture']['actor']=='Alice')
    assert not evaluate(bob,trace(alice))['ok']


@pytest.mark.parametrize('field',['requestDigest','grantId','gid','dataId','kssc','destinationChainId','recipientKeyHash','keyEpoch'])
def test_corrupted_grant_binding_fails(field):
    s=next(s for s in SCENARIOS if s['fixture']['actor']=='Alice')
    t=trace(s);e=next(e for e in t['events'] if e['type']=='DBC_AUTHORIZED');e[field]='wrong'
    assert not evaluate(s,t)['ok']


def test_missing_or_reordered_request_authorization_intent_fails():
    s=SCENARIOS[0];t=trace(s)
    for name in ('REQUEST_LOGGED','PBC_DECIDED','DBC_AUTHORIZED','RELEASE_INTENT'):
        altered=copy.deepcopy(t);altered['events']=[e for e in altered['events'] if e['type']!=name]
        assert not evaluate(s,altered)['ok']
    altered=copy.deepcopy(t);altered['events'].reverse()
    assert not evaluate(s,altered)['ok']


def test_denial_requires_correct_reason_and_no_release():
    s=next(s for s in SCENARIOS if s['expectedError']=='UNAUTHORIZED_CALLER');t=trace(s)
    t['error']='BAD_SIGNATURE';assert not evaluate(s,t)['ok']
    t=trace(s);t['events'].append({'type':'RELEASE_SENT','requestDigest':s['fixture']['requestDigest']})
    assert not evaluate(s,t)['ok']


def test_wrong_mode_or_repeated_grant_transition_fails():
    s=SCENARIOS[0];t=trace(s);t['adapterMode']='abe-real';assert not evaluate(s,t)['ok']
    t=trace(s);t['events'].append(copy.deepcopy(next(e for e in t['events'] if e['type']=='DBC_AUTHORIZED')))
    assert not evaluate(s,t)['ok']


def test_duplicate_outcome_transition_fails():
    s=SCENARIOS[0];t=trace(s)
    t['events'].append(copy.deepcopy(t['events'][-1]))
    assert not evaluate(s,t)['ok']
