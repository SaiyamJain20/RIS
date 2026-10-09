"""C-E1 bootstrap through public ABI transactions and independent native joins.

Caller must hold exact integration FREEZE ACKs before starting local services.
This component does not start services or issue an E1/RQ gate verdict. Its named
wrong-admin control tests a baseline issuer restriction, not a repaired feature.
"""
from evaluation.bootstrap import strict_json, validate_bootstrap, signed_digest
from evaluation.native import _quantity


def _require(condition, label):
    if not condition:
        raise ValueError('Native bootstrap '+label+' failed')


def _block(native):
    return {'number': hex(int(native.block_number)), 'hash': native.block_hash}


def _event(native, contract, name):
    matching = [event['fields'] for event in native.decoded(contract) if event['name'] == name]
    _require(len(matching) == 1, name+' must occur exactly once')
    return matching[0]


def execute_bootstrap(chain, raw_bootstrap, *, deployment_bytes):
    """Execute wrong-admin then three positive list updates and two registrations.

    The current PBC must be fresh. Every observation is made through the public
    executor at a bound block; the returned public bundle is not integration or
    delivery evidence. Failure stops the sequence, preserving executor logs.
    """
    sample = strict_json(raw_bootstrap) if isinstance(raw_bootstrap, bytes) else raw_bootstrap
    deployment = strict_json(deployment_bytes)
    binding = sample['binding']
    pbc = deployment['chains']['pbc']
    _require(chain.chain_id == pbc['chainId'], 'chain binding')
    for role in ('TMSC', 'RSC'):
        _require(chain.contracts[role].address == pbc['contracts'][role], 'contract binding')
    source = chain.rpc.call('eth_getBlockByNumber', [hex(int(binding['blockNumber'])), False])
    _require(source is not None and _quantity(source['number']) >= int(pbc['deployBlock']), 'producer block')
    versions = {}
    for authority in deployment['fixture']['authorities']:
        root = authority['root']
        versions[root] = {'revocation': chain.read('TMSC', 'revocationListState', root, block=source)[0]['version'],
                          'temporal': chain.read('TMSC', 'temporalAclState', root, block=source)[0]['version']}
    latest = chain.latest_block()
    checked = validate_bootstrap(sample, deployment_bytes=deployment_bytes, source_block=source,
                                 versions=versions, now_timestamp=str(_quantity(latest['timestamp'])))
    _require(chain.read('RSC', 'tmsc', block=latest) == [pbc['contracts']['TMSC']], 'RSC wiring')
    _require(chain.read('TMSC', 'pbcChainId', block=latest) == [pbc['chainId']], 'TMSC chain')
    _require(chain.read('TMSC', 'profile', block=latest) == [deployment['profileEnum']], 'profile')
    _require(chain.read('TMSC', 'mutations', block=latest) == ['0'], 'baseline mutations')
    for user in checked['users'].values():
        _require(chain.read('RSC', 'isRegistered', user['gid'], block=latest) == [False], 'fresh registration')
    before = {}
    for item in checked['trustLists']:
        state_method = 'revocationListState' if item['kind'] == 'RevocationList' else 'temporalAclState'
        root = item['signer']
        before[(state_method, root)] = chain.read('TMSC', state_method, root, block=latest)[0]
        _require(before[(state_method, root)]['published'] is False, 'fresh trust anchor')
        _require(chain.read('TMSC', 'isCaAdmin', root, item['submitter'], block=latest) == [True], 'positive admin membership')
    epoch = chain.read('TMSC', 'authEpoch', block=latest)[0]
    _require(epoch == '0', 'fresh auth epoch')
    h2 = checked['trustLists'][2]; wrong_admin = checked['trustLists'][0]['submitter']
    _require(chain.read('TMSC', 'isCaAdmin', h2['signer'], wrong_admin, block=latest) == [False], 'negative admin membership')
    rejected = chain.submit('H1-ca-admin', 'TMSC', 'updateRevocationList', h2['list'], h2['signature'], expect_success=False)
    _require(rejected.success is False, 'wrong-admin must reject')
    _require(chain.rejection_code(rejected) == '16', 'wrong-admin rejection reason')
    _require(chain.read('TMSC', 'authEpoch', block=_block(rejected)) == [epoch], 'wrong-admin epoch rollback')
    for (method, root), state in before.items():
        _require(chain.read('TMSC', method, root, block=_block(rejected)) == [state], 'wrong-admin anchor rollback')
    for item in checked['trustLists']:
        method = 'updateRevocationList' if item['kind'] == 'RevocationList' else 'updateTemporalAcl'
        state_method = 'revocationListState' if item['kind'] == 'RevocationList' else 'temporalAclState'
        body = item['list']; old = before[(state_method, item['signer'])]
        native = chain.submit(item['submitterRole'], 'TMSC', method, body, item['signature'])
        _require(native.success is True, 'positive trust update')
        digest = signed_digest(item['kind'], body, item['signature'], item['signer'], pbc['chainId'], pbc['contracts']['TMSC'])
        epoch = str(int(epoch)+1)
        expected = {'published': True, 'version': body['version'], 'validUntil': body['validUntil'],
                    'generation': str(int(old['generation'])+1), 'contentDigest': digest,
                    'blockNumber': native.block_number, 'prevBlockNumber': old['blockNumber']}
        _require(chain.read('TMSC', state_method, item['signer'], block=_block(native)) == [expected], 'anchor/state/digest join')
        event = _event(native, chain.contracts['TMSC'], 'TrustAnchorUpdated')
        expected_event = {k: expected[k] for k in ('version', 'validUntil', 'generation', 'contentDigest', 'prevBlockNumber')}
        expected_event.update(authority=item['signer'], kind='1' if item['kind'] == 'RevocationList' else '2',
                              authEpoch=epoch, submitter=item['submitter'])
        _require(event == expected_event, 'trust update event join')
        _require(chain.read('TMSC', 'authEpoch', block=_block(native)) == [epoch], 'trust update epoch')
    for label, user in checked['users'].items():
        native = chain.submit('relay', 'RSC', 'register', user['registration'], user['possessionSignature'], user['certificate'])
        _require(native.success is True, 'positive '+label+' registration')
        event = _event(native, chain.contracts['RSC'], 'Registered')
        _require(all(event[key] == user['registration'][key] for key in ('gid', 'certDigest', 'recipientKeyHash'))
                 and event['issuer'] == user['certificate']['cert']['issuer'], 'registration event join')
        _require(chain.read('RSC', 'isRegistered', user['gid'], block=_block(native)) == [True], 'registered GID')
        _require(chain.read('RSC', 'recipientKeyHash', user['gid'], block=_block(native)) == [user['recipientKeyHash']], 'registered recipient')
    return {**checked, 'wrongAdminCode': '16', 'registeredUsers': list(checked['users']),
            'scope': 'bootstrap only; full C-E1 runner and integrated controls still required'}
