"""Synthetic subject-evidence sensitivity, not integrated catalog results.

Removing a tuple, unchanged-state, credential or event join must accept one of
the false observations below and fail these tests. Expectations come from the
frozen E01 subject cases, SPEC4 and D35/A38, not the owner implementation.
"""
import copy
import importlib

import pytest


def oracle():
    assert importlib.util.find_spec('evaluation.oracles.subject') is not None, 'subject oracle missing'
    return importlib.import_module('evaluation.oracles.subject').check_subject_substitution


def facts(profile='paper-strict'):
    original = dict(gid='alice', dataId='record', action='1', nonce='1',
                    recipientKeyHash='alice-key', expiresAt='130')
    records = [dict(role='Doctor'), dict(role='OnDuty')]
    forward = dict(pbcRequestId='digest', gid='alice', dataId='record', action='1')
    certificate = dict(decision=dict(requestDigest='digest', result='1'), signatures=['original-signature'])
    args = [copy.deepcopy(original if profile == 'repaired-e' else forward),
            copy.deepcopy(certificate if profile == 'repaired-e' else records)]
    args[0]['gid'] = 'bob'
    if profile == 'repaired-e': args.append(copy.deepcopy(records))
    before = dict(request=dict(status='1', gid='alice', dataId='record', expiresAt='130',
                               requestLogId='7', outcomeLogId='0', decidedAt='100'),
                  grant=dict(exists=False, allowed=False), nonceAlice=False, nonceBob=False,
                  accessLogCount='0', worker=dict(events=[], releases=[]),
                  logs=dict(pbc=[{'request': 'original'}], dbc=[]))
    after = copy.deepcopy(before)
    events = []
    if profile != 'repaired-e':
        after['grant'] = dict(exists=True, allowed=True, requestDigest='digest', gid='bob',
                              dataId='record', recipientKeyHash='0x'+'00'*32,
                              keyEpoch='0', issuedAt='110', expiresAt='140')
        after['accessLogCount'] = '1'
        events = [dict(name='GrantIssued', fields=dict(grantId='grant', requestDigest='digest',
                       gid='bob', dataId='record', keyEpoch='0', expiresAt='140',
                       recipientKeyHash='0x'+'00'*32, nonceConsumed=False, nonce='0')),
                  dict(name='AccessLog', fields=dict(requestRef='digest', gid='bob', dataId='record',
                       allowed=True, code='0', grantId='grant', credentialDigest='credential-digest', submitter='relay'))]
        after['logs']['dbc'] = copy.deepcopy(events)
    return dict(profile=profile, original_request=original, request_digest='digest',
                forwarded=forward, records=records, certificate=certificate,
                submitted_arguments=args, target_gid='bob', grant_id='grant',
                credential_digest='credential-digest', relay='relay', before=before, after=after,
                success=profile != 'repaired-e', rejection_code='3' if profile == 'repaired-e' else None,
                receipt_events=events, timestamp='110')


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_subject_substitution_distinguishes_paper_tuple_from_unchanged_certificate(profile):
    proof = oracle()(**facts(profile))
    assert proof['ok'] and proof['delivery'] == 'unknown'
    assert proof['classification'] == ('REPAIR_SUPPORTED' if profile == 'repaired-e' else 'SPEC_GAP')
    assert proof['error'] == ('WRONG_SUBJECT' if profile == 'repaired-e' else None)
    assert proof['workerUnchanged']
    assert proof['releaseTested'] is False


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
@pytest.mark.parametrize('mutation', ['no-substitution', 'wrong-target', 'data', 'reference-or-nonce',
    'credentials', 'not-forwarded', 'unlogged', 'prior-grant', 'nonce-alice', 'nonce-bob',
    'pbc-change', 'worker-change', 'count', 'missing-history', 'before-request', 'expired'])
def test_subject_oracle_rejects_wrong_schedule_and_false_state(profile, mutation):
    d = facts(profile)
    if mutation == 'no-substitution': d['submitted_arguments'][0]['gid'] = 'alice'
    if mutation == 'wrong-target': d['submitted_arguments'][0]['gid'] = 'unregistered'
    if mutation == 'data': d['submitted_arguments'][0]['dataId'] = 'other'
    if mutation == 'reference-or-nonce': d['submitted_arguments'][0]['nonce' if profile == 'repaired-e' else 'pbcRequestId'] = 'other'
    if mutation == 'credentials': d['submitted_arguments'][-1].append({'role': 'extra'})
    if mutation == 'not-forwarded': d['before']['request']['status'] = '0'
    if mutation == 'unlogged': d['before']['request']['requestLogId'] = '0'
    if mutation == 'prior-grant': d['before']['grant']['exists'] = True
    if mutation == 'nonce-alice': d['after']['nonceAlice'] = True
    if mutation == 'nonce-bob': d['after']['nonceBob'] = True
    if mutation == 'pbc-change': d['after']['logs']['pbc'].append({'outcome': 'new'})
    if mutation == 'worker-change': d['after']['worker']['events'].append('RELEASE_INTENT')
    if mutation == 'count': d['after']['accessLogCount'] = '2'
    if mutation == 'missing-history': d['before']['logs'].pop('dbc')
    if mutation == 'before-request': d['timestamp'] = '-1'
    if mutation == 'expired': d['timestamp'] = '130'
    with pytest.raises(ValueError): oracle()(**d)


@pytest.mark.parametrize('mutation', ['decision', 'signature', 'wrong-code', 'success', 'receipt', 'state'])
def test_repaired_subject_requires_original_certificate_and_whole_rollback(mutation):
    d = facts('repaired-e')
    if mutation == 'decision': d['submitted_arguments'][1]['decision']['requestDigest'] = 'rewritten'
    if mutation == 'signature': d['submitted_arguments'][1]['signatures'] = ['replacement']
    if mutation == 'wrong-code': d['rejection_code'] = '2'
    if mutation == 'success': d['success'] = True
    if mutation == 'receipt': d['receipt_events'].append({'name': 'GrantIssued'})
    if mutation == 'state': d['after']['grant']['allowed'] = True
    with pytest.raises(ValueError): oracle()(**d)


@pytest.mark.parametrize('mutation', ['deny-all', 'grant-subject', 'grant-recipient', 'grant-expiry',
    'no-grant-event', 'extra-event', 'access-subject', 'access-credentials', 'grant-id', 'history'])
def test_paper_subject_requires_exact_allowed_grant_and_access_evidence(mutation):
    d = facts()
    if mutation == 'deny-all': d['success'] = False
    if mutation == 'grant-subject': d['after']['grant']['gid'] = 'alice'
    if mutation == 'grant-recipient': d['after']['grant']['recipientKeyHash'] = 'alice-key'
    if mutation == 'grant-expiry': d['after']['grant']['expiresAt'] = '160'
    if mutation == 'no-grant-event': d['receipt_events'].pop(0)
    if mutation == 'extra-event': d['receipt_events'].append({'name': 'Other'})
    if mutation == 'access-subject': d['receipt_events'][1]['fields']['gid'] = 'alice'
    if mutation == 'access-credentials': d['receipt_events'][1]['fields']['credentialDigest'] = 'other'
    if mutation == 'grant-id': d['receipt_events'][0]['fields']['grantId'] = 'other'
    if mutation == 'history': d['after']['logs']['dbc'].append({'name': 'Other'})
    with pytest.raises(ValueError): oracle()(**d)


@pytest.mark.parametrize('mutation', ['wrong-caller', 'before-decision', 'wrong-action', 'unknown-profile'])
def test_subject_oracle_enforces_caller_action_and_observation_clock(mutation):
    d = facts()
    if mutation == 'wrong-caller':
        d['receipt_events'][1]['fields']['submitter'] = 'outsider'
        d['after']['logs']['dbc'][1]['fields']['submitter'] = 'outsider'
    if mutation == 'before-decision':
        d['timestamp'] = d['after']['grant']['issuedAt'] = '99'
        d['after']['grant']['expiresAt'] = '129'
        d['receipt_events'][0]['fields']['expiresAt'] = '129'
        d['after']['logs']['dbc'][0]['fields']['expiresAt'] = '129'
    if mutation == 'wrong-action':
        for obj in (d['original_request'], d['forwarded'], d['submitted_arguments'][0]): obj['action'] = '2'
    if mutation == 'unknown-profile': d['profile'] = 'mutant-no-binding'
    with pytest.raises(ValueError): oracle()(**d)
