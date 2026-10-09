"""Revision 5 E0 boundary proposal. No runtime services or real crypto here."""

OPERATIONS = {
    'prepare_request': 'PrepareRequest',
    'collect_decision': 'CollectDecision',
    'collect_checkpoint': 'CollectCheckpoint',
    'attest_grant': 'AttestGrant',
    'release': 'Release',
    'encrypt_record': 'EncryptRecord',
    'finish_decryption': 'FinishDecryption',
    'rotate_epoch': 'RotateEpoch',
}
CLASSIFICATIONS = ('SUPPORTED', 'SPEC_GAP', 'RECONSTRUCTION_FAILURE',
                   'REPAIR_SUPPORTED', 'REFUTED', 'BLOCKED')


def extend(d, obj, ref, array, string, enum):
    d['Scenario']['properties']['expectedLedgerChecks'] = {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                                         'items': enum('DBC_POLICY_DENIAL_LOGGED', 'NONCE_UNCHANGED')}
    d['UserKeyRef'] = {'type': 'string', 'format': 'user-key-ref', 'maxLength': 76}
    d['SymbolicRecord'] = obj({'dataId': ref('Hash'), 'owner': ref('Address'), 'payloadDigest': ref('Hash')})
    # These are ACSC Requirement tuple encodings; clause order is meaningful.
    d['PolicyRequirement'] = obj({'role': ref('Hash'), 'kind': enum('1', '2'), 'issuerMode': enum('0', '1', '2')})
    d['SymbolicPolicy'] = obj({'clauses': {'type': 'array', 'minItems': 1,
                                         'items': array('PolicyRequirement', 1)}})
    d['SymbolicEnvelope'] = obj({'kind': {'const': 'symbolic-partial/v1'}, 'token': ref('Hash')})
    d['PrepareRequestInput'] = obj({'request': ref('AccessRequest'), 'signingKeyRef': ref('UserKeyRef')})
    d['CollectDecisionInput'] = obj({'requestDigest': ref('Hash'), 'witnessSetVersion': {'const': '1'}},
                                    optional=('witnessSetVersion',))
    d['CollectCheckpointInput'] = obj({'witnessSetVersion': {'const': '1'}}, optional=('witnessSetVersion',))
    d['AttestGrantInput'] = obj({'grantId': ref('Hash')})
    d['ReleaseInput'] = obj({'grantId': ref('Hash')})
    d['EncryptRecordInput'] = obj({'record': ref('SymbolicRecord'), 'policy': ref('SymbolicPolicy'), 'keyEpoch': {'const': '0'}})
    d['FinishDecryptionInput'] = obj({'response': ref('ReleaseResult'), 'userKeyRef': ref('UserKeyRef')})
    d['RotateEpochInput'] = obj({'targetEpoch': ref('Uint64')})
    header = {'schemaVersion': {'const': 'v1'}, 'adapterMode': {'const': 'symbolic'}}
    d['PrepareRequestResult'] = obj({**header, 'request': ref('AccessRequest'), 'requestDigest': ref('Hash'),
                                     'signature': ref('Signature'), 'signer': ref('Address')})
    d['CollectDecisionResult'] = obj({**header, 'decision': ref('AccessDecision'),
                                      'signatures': {**array('Signature', 1), 'maxItems': 1},
                                      'credentialRecords': ref('CredentialRecords')})
    d['CollectCheckpointResult'] = obj({**header, 'checkpoint': ref('StateCheckpoint'),
                                       'signatures': {**array('Signature', 1), 'maxItems': 1}})
    d['AttestGrantResult'] = obj({**header, 'receipt': ref('GrantReceipt'),
                                'signatures': {**array('Signature', 1), 'maxItems': 1}})
    d['ReleaseResult'] = obj({**header, **{field: ref('Hash') for field in
                                         ('requestDigest', 'grantId', 'dataId', 'ciphertextDigest', 'recipientKeyHash')},
                              'keyEpoch': {'const': '0'}, 'responseEnvelope': ref('SymbolicEnvelope')})
    d['EncryptRecordResult'] = obj({**header, 'dataId': ref('Hash'), 'keyEpoch': {'const': '0'},
                                    'ciphertextDigest': ref('Hash'), 'policyDigest': ref('Hash')})
    d['FinishDecryptionResult'] = obj({**header, 'decryptable': {'type': 'boolean'},
                                       'dataId': ref('Hash'), 'ciphertextDigest': ref('Hash')})
    def success(result):
        return obj({'schemaVersion': {'const': 'v1'}, 'ok': {'const': True}, 'result': result, 'error': {'type': 'null'}})
    error = obj({'schemaVersion': {'const': 'v1'}, 'ok': {'const': False}, 'result': {'type': 'null'}, 'error': ref('Error')})
    requests, responses = [], []
    for operation, name in OPERATIONS.items():
        d[name + 'Request'] = obj({'schemaVersion': {'const': 'v1'}, 'operation': {'const': operation},
                                  'input': ref(name + 'Input'), 'deploymentManifest': ref('LedgerDeployment')})
        requests.append(ref(name + 'Request'))
        variants = [error] if operation == 'rotate_epoch' else [success(ref(name + 'Result')), error]
        d[name + 'Response'] = {'oneOf': variants}
        if operation != 'rotate_epoch':
            responses.append(ref(name + 'Result'))
    d['AdapterRequest'] = {'oneOf': requests}
    d['AdapterResponse'] = {'oneOf': [success({'oneOf': responses}), error]}
    d['EvidencePath'] = {'type': 'string', 'format': 'evidence-path', 'minLength': 1}
    base_event = {'type': ref('EventName'), 'requestDigest': ref('Hash'), 'timestamp': ref('Uint64')}
    events = []
    for kind in d['EventName']['enum']:
        properties = {**base_event, 'type': {'const': kind}}
        if kind in ('DBC_AUTHORIZED', 'RELEASE_INTENT', 'RELEASE_SENT', 'OUTCOME_RECORDED'):
            properties.update({'grantId': ref('Hash'), 'gid': ref('Address'), 'dataId': ref('Hash')})
        if kind == 'DBC_AUTHORIZED':
            properties.update({'kssc': ref('Address'), 'destinationChainId': ref('Uint256'),
                               'recipientKeyHash': ref('Hash'), 'keyEpoch': {'const': '0'}})
        events.append(obj(properties))
    d['ObservedEvent'] = {'oneOf': events}
    d['Assertion'] = obj({'name': string(), 'passed': {'type': 'boolean'}})
    d['ScenarioResult'] = obj({'scenarioId': string(), 'classification': enum(*CLASSIFICATIONS),
                              'observedEvents': array('ObservedEvent'), 'assertions': array('Assertion'),
                              'latencyMs': {'anyOf': [{'type': 'number', 'minimum': 0}, {'type': 'null'}]},
                              'gasUsed': {'anyOf': [ref('Uint256'), {'type': 'null'}]},
                              'encodedBytes': {'anyOf': [{'type': 'integer', 'minimum': 0}, {'type': 'null'}]},
                              'limitations': {'type': 'array', 'items': string(), 'minItems': 1},
                              'evidencePaths': array('EvidencePath')})
    d['ScenarioResult']['allOf'] = [
        {'if': {'properties': {'classification': enum('SUPPORTED', 'REPAIR_SUPPORTED')}},
         'then': {'properties': {'assertions': {'minItems': 1, 'items': {'properties': {'passed': {'const': True}}}},
                                  'evidencePaths': {'minItems': 1}}}},
        {'if': {'properties': {'classification': {'not': {'const': 'BLOCKED'}}}},
         'then': {'properties': {'evidencePaths': {'minItems': 1}}}},
    ]
    actions = ('REQUEST_ACCESS', 'SUBSTITUTE_SUBJECT', 'REPLAY_REQUEST', 'ADVANCE_CLOCK',
               'FABRICATE_TUPLE', 'SUBSTITUTE_DESTINATION', 'REPLAY_NEW_REFERENCE',
               'INSTALL_NEW_LIST', 'REPLAY_OLD_LIST', 'WRONG_ISSUER_UPDATE', 'REVOKE_ON_PBC',
               'ACCEPT_CHECKPOINT', 'FORWARD_OR_CONSUME', 'RELEASE', 'DROP_OUTCOME',
               'FABRICATE_OUTCOME', 'REPORT_OUTCOME', 'DUPLICATE_OUTCOME', 'CRASH_RESTART',
               'REQUEST_SAME_NONCE_DISTINCT_DIGEST', 'FORWARD_BOTH_REQUESTS',
               'CERTIFY_BOTH_BEFORE_CONSUMPTION', 'CONSUME_FIRST', 'CONSUME_PRECOLLECTED_SECOND', 'ATTEST_GRANT')
    variants = {
        'E01': ('subject-substitution', 'nonce-replay', 'expiry-boundary',
                'forged-tuple', 'wrong-destination', 'new-reference-replay', 'same-nonce-distinct-digests'),
        'E02': ('signed-list-rollback', 'wrong-issuer', 'pre-barrier-revocation',
                'post-barrier-revocation', 'expired-duty'),
        'E03': ('dropped-outcome', 'fabricated-outcome', 'duplicate-outcome',
                'crash-after-intent', 'crash-after-send', 'receipt-binding-control',
                'receipt-signature-control', 'receipt-binding-positive'),
    }
    d['E0CaseStep'] = {'oneOf': [
        obj({'action': enum(*(a for a in actions if a != 'CRASH_RESTART')), 'offsetSeconds': ref('Uint64')}),
        obj({'action': {'const': 'CRASH_RESTART'}, 'offsetSeconds': ref('Uint64'),
             'workerHook': {'const': 'release'}, 'crashPoint': enum('after-intent', 'after-send')}),
        obj({'action': enum('RESIGN_RECEIPT_FIELD', 'ALTER_RECEIPT_KEEP_SIGNATURE'),
             'offsetSeconds': ref('Uint64'), 'receiptField': enum('requestDigest', 'gid', 'dataId')}),
    ]}
    d['WorkerExpectation'] = obj({'releaseIntentCount': ref('Uint64'), 'releaseSentCount': ref('Uint64'),
                                 'sameCachedResponse': {'const': True}, 'delivery': {'const': 'unknown'},
                                 'expiredRetryError': {'const': 'EXPIRED'}})
    d['E0CaseFixture'] = obj({'id': string(), 'caseFamily': enum(*variants),
                              'profile': enum('paper-strict', 'paper-minimal', 'repaired-e'),
                              'sourceRefs': {'type': 'array', 'items': string(), 'minItems': 1},
                              'assumptions': {'type': 'array', 'items': string(), 'minItems': 1},
                              'baseScenarioId': string(), 'variant': string(), 'steps': array('E0CaseStep', 1),
                              'expected': obj({'property': enum('decision-provenance', 'trust-freshness', 'audit-correspondence'),
                                               'outcome': enum('ACCEPT', 'REJECT', 'PENDING', 'NO_NEW_GRANT', 'NO_NEW_OUTCOME', 'CONDITIONAL', 'UNPROVED'),
                                               'classification': enum(*CLASSIFICATIONS),
                                               'error': {'anyOf': [d['Error']['properties']['code'], {'type': 'null'}]},
                                               'qualification': string(), 'worker': ref('WorkerExpectation')}, optional=('worker',)),
                              'adapterMode': {'const': 'symbolic'}, 'executionStatus': {'const': 'NOT_RUN'}})
    d['E0CaseFixture']['allOf'] = [
        {'if': {'properties': {'caseFamily': {'const': family}}},
         'then': {'properties': {'variant': enum(*names)}}} for family, names in variants.items()
    ]
