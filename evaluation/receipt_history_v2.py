"""Check declared receipt digests against separately supplied raw state/events.

Internal paper-derived HMBC2020 extension. Observation selection is explicit;
supplied bytes establish no RPC truth, signing time, latest head, complete log
range/export/store, native death/transition, persistence, delivery or quorum.
Fault/clear intervals and mutation death exclusions retain their original scope.
"""
from evaluation.receipt_state_v2 import verify_receipt_signature
from evaluation.witness_history_v2 import verify_signed_history


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid receipt history: ' + message)


def verify_receipt_history(evidence, *, manifest, observations, expected_owner,
                           abi_paths, captures, compiled_max_admins=None):
    """Require one closed capture per declared live/superseded receipt digest.

    Capture fields: digest, dbcObservation, blocks, calls, logs. The PBC
    observation comes from the stored signature record; neither observation is
    attested signing time. Captures may share identical raw facts. At one raw
    fact key contradictory values refuse even in a declared fault interval.
    In a declared safe interval a grant also retains one canonical event.
    These consistency checks do not establish possible native transitions.
    """
    _require(manifest.get('profileEnum') == '3', 'repaired-f profile required')
    checked = verify_signed_history(evidence, manifest=manifest, observations=observations,
        expected_owner=expected_owner, compiled_max_admins=compiled_max_admins)
    _require(isinstance(captures, list), 'capture list')
    selected = {}
    for capture in captures:
        _require(isinstance(capture, dict) and set(capture) ==
                 {'digest','dbcObservation','blocks','calls','logs'}, 'capture fields')
        digest = capture['digest']
        _require(isinstance(digest, str), 'capture digest')
        _require(digest not in selected, 'duplicate capture digest')
        selected[digest] = capture

    rows = [r for r in evidence['superseded'] + evidence['conflicts'] if r['type']=='GrantReceipt']
    expected = {signed['digest'] for row in rows for signed in row['digests']}
    _require(set(selected) == expected, 'exact receipt digest coverage')
    headers, heights, calls, events, grant_events = {}, {}, {}, {}, {}
    for row in rows:
        message = row['effect'] | dict(requestDigest=row['keyField'])
        for signed in row['digests']:
            capture = selected[signed['digest']]
            verify_receipt_signature(message, signed['signature'],
                owner=expected_owner.removeprefix('witness:'), manifest=manifest,
                observations=observations, abi_paths=abi_paths,
                pbc_observation=signed['observation'], dbc_observation=capture['dbcObservation'],
                blocks=capture['blocks'], calls=capture['calls'], logs=capture['logs'],
                compiled_max_admins=compiled_max_admins)
            # Per-signature checks validated canonical fields and exact usage.
            for block in capture['blocks']:
                chain, raw = block['chainId'], block['raw']
                key, value = (chain, raw['hash']), (raw['number'], raw['timestamp'])
                _require(key not in headers or headers[key]==value, 'conflicting block facts')
                headers[key] = value
                height = chain, raw['number']
                if checked['declaredSafeLedgerInterval']:
                    _require(height not in heights or heights[height]==raw['hash'], 'conflicting safe block hashes')
                heights[height] = raw['hash']
            for call in capture['calls']:
                key = tuple(call[k] for k in ('chainId','blockHash','to','data'))
                _require(key not in calls or calls[key]==call['result'], 'conflicting state call facts')
                calls[key] = call['result']
            log = capture['logs'][0]
            grant = message['dbcChainId'], log['address'], message['grantId']
            key = grant + (log['blockHash'],)
            value = log['blockNumber'], tuple(log['topics']), log['data']
            _require(key not in events or events[key]==value, 'conflicting grant event facts')
            events[key] = value
            event = log['blockHash'], value
            if checked['declaredSafeLedgerInterval']:
                _require(grant not in grant_events or grant_events[grant]==event, 'conflicting safe grant event')
            grant_events[grant] = event
    return checked | dict(receiptStateSignaturesChecked=len(expected),
        signTimeEstablished=False, latestHeadEstablished=False,
        logCompletenessEstablished=False, nativeTransitionsEstablished=False)
