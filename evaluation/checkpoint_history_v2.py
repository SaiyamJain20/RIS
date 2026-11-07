"""Join every declared checkpoint digest to its supplied state observations.

Paper-derived HMBC2020 reconstruction/extension; internal composition only.
The recorded target observation is exporter data, not attested signing time.
No RPC authenticity, latest-head/ancestry, store/export completeness, native
death facts, quorum or integrated result follows. Fault/clear interval labels
and mutation death exclusions retain the declared-history checker's scope.
"""
from evaluation.checkpoint_state_v2 import verify_checkpoint_signature
from evaluation.witness_history_v2 import verify_signed_history


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid checkpoint history: ' + message)


def verify_checkpoint_history(evidence, *, manifest, observations, expected_owner,
                              abi_paths, captures, compiled_max_admins=None):
    """Check exact live/superseded checkpoint coverage, keyed by signed digest.

    Each capture is {digest, pbcHead, blocks, calls}; raw capture shapes come
    from checkpoint_state_v2. Target blocks are selected by each stored digest's
    observation, never by a caller-supplied override. Captures may share identical
    facts, but contradictory facts at the same key always refuse. Safe intervals
    also refuse conflicting hashes at one height. No inputs or files are changed.
    """
    _require(manifest.get('profileEnum') == '3', 'repaired-f profile required')
    checked = verify_signed_history(evidence, manifest=manifest, observations=observations,
        expected_owner=expected_owner, compiled_max_admins=compiled_max_admins)
    _require(isinstance(captures, list), 'capture list')
    selected = {}
    for capture in captures:
        _require(isinstance(capture, dict) and set(capture) == {'digest','pbcHead','blocks','calls'},
                 'capture fields')
        digest = capture['digest']
        _require(isinstance(digest, str), 'capture digest')
        _require(digest not in selected, 'duplicate capture digest')
        selected[digest] = capture

    expected = {signed['digest'] for row in evidence['superseded'] + evidence['conflicts']
                if row['type'] == 'StateCheckpoint' for signed in row['digests']}
    _require(set(selected) == expected, 'exact checkpoint digest coverage')
    headers, heights, calls = {}, {}, {}
    for row in evidence['superseded'] + evidence['conflicts']:
        if row['type'] != 'StateCheckpoint':
            continue
        for signed in row['digests']:
            capture = selected[signed['digest']]
            message = row['effect'] | dict(sequence=row['keyField'], expiresAt=signed['expiresAt'])
            verify_checkpoint_signature(message, signed['signature'],
                owner=expected_owner.removeprefix('witness:'), manifest=manifest,
                observations=observations, abi_paths=abi_paths, pbc_head=capture['pbcHead'],
                dbc_observation=signed['observation'], blocks=capture['blocks'], calls=capture['calls'],
                compiled_max_admins=compiled_max_admins)
            # The per-signature checker validated canonical fields and exact usage.
            for block in capture['blocks']:
                chain, raw = block['chainId'], block['raw']
                key, value = (chain, raw['hash']), (raw['number'], raw['timestamp'])
                _require(key not in headers or headers[key] == value, 'conflicting block facts')
                headers[key] = value
                height = chain, raw['number']
                if checked['declaredSafeLedgerInterval']:
                    _require(height not in heights or heights[height] == raw['hash'], 'conflicting safe block hashes')
                heights[height] = raw['hash']
            for call in capture['calls']:
                key = tuple(call[k] for k in ('chainId','blockHash','to','data'))
                _require(key not in calls or calls[key] == call['result'], 'conflicting state call facts')
                calls[key] = call['result']
    return checked | dict(checkpointStateSignaturesChecked=len(expected))
