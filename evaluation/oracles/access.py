"""Independent positive/denial oracle derived from SPEC, not service control flow.

The trace sequence is a causally ordered observation list supplied by the
integration collector. It is not a comparison of block numbers on two chains.
Synthetic unit traces verify the oracle; only pinned real runs can support E.
"""

GRANT_BINDINGS=('requestDigest','grantId','gid','dataId','kssc','destinationChainId','recipientKeyHash','keyEpoch')
RELEASE_BINDINGS=('requestDigest','grantId','gid','dataId')
FORBIDDEN_ON_DENIAL={'DBC_AUTHORIZED','RELEASE_INTENT','RELEASE_SENT','OUTCOME_RECORDED'}


def evaluate(scenario,observed):
    assertions=[]
    def check(name,condition):assertions.append({'name':name,'passed':bool(condition)})
    events=observed.get('events',[]);fixture=scenario['fixture'];names=[e.get('type') for e in events]
    check('adapter mode is explicit and matches',observed.get('adapterMode')==scenario['adapterMode'])
    check('stable denial reason',observed.get('error')==scenario['expectedError'])
    check('expected events occur in causal order',_subsequence(scenario['expectedEvents'],names))
    # Controls do not include retry transitions: a second grant is never an idempotent read.
    check('at most one new grant',names.count('DBC_AUTHORIZED')<=1)
    check('at most one recorded outcome',names.count('OUTCOME_RECORDED')<=1)
    if scenario['expectedError'] is not None:
        check('denial cannot release or record a successful grant outcome',not FORBIDDEN_ON_DENIAL.intersection(names))
    for index,event in enumerate(events):
        if event.get('type') in ('REQUEST_LOGGED','PBC_DECIDED','DBC_AUTHORIZED','RELEASE_INTENT','RELEASE_SENT','OUTCOME_RECORDED'):
            check(f'event {index} request binding',event.get('requestDigest')==fixture['requestDigest'])
        if event.get('type')=='DBC_AUTHORIZED':
            for key in GRANT_BINDINGS:check(f'grant {index} {key}',event.get(key)==fixture[key])
        if event.get('type') in ('RELEASE_INTENT','RELEASE_SENT','OUTCOME_RECORDED'):
            for key in RELEASE_BINDINGS:check(f'release/outcome {index} {key}',event.get(key)==fixture[key])
            prefix=names[:index]
            check(f'authorization precedes {index}','DBC_AUTHORIZED' in prefix)
            if event['type']=='RELEASE_SENT':check(f'durable intent precedes send {index}','RELEASE_INTENT' in prefix)
    ok=all(a['passed'] for a in assertions)
    return {'ok':ok,'classification':scenario['expectedClass'] if ok else 'RECONSTRUCTION_FAILURE','assertions':assertions,'observedEvents':events,'limitations':['E/F adapter is symbolic; no measured ABE security.', 'Outcome recording is not proof of recipient delivery.']}


def _subsequence(expected,actual):
    remaining=iter(actual)
    return all(any(candidate==name for candidate in remaining) for name in expected)
