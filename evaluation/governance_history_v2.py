"""Join declared governance digests to supplied PBC state and local approvals.

Paper-derived HMBC2020 extension, internal API only. The export's observations
are unsigned exporter claims. Caller-supplied approval fixtures authenticate no
producer policy. These checks establish neither signing time, latest head, RPC
truth, native death facts, complete stores, a quorum nor an integrated result.
"""
from evaluation.governance_state_v2 import verify_governance_signature
from evaluation.witness_history_v2 import verify_signed_history


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid governance history: ' + message)


def verify_governance_history(evidence, *, manifest, observations, expected_owner,
                              abi_paths, captures, approvals, compiled_max_admins=None):
    """Check every live/superseded digest against its recorded PBC observation.

    captures is a list of closed {digest,blocks,calls} records, exactly covering
    declared GovernanceAction digests. approvals is passed separately by the
    caller, using governance_state_v2's TEST-ONLY tuples. Repeated immutable facts
    must agree; safe intervals additionally require one hash per height. The
    history checker's fault/clear and mutation-death scope is retained unchanged.
    """
    _require(manifest.get('profileEnum') == '3', 'repaired-f profile required')
    checked = verify_signed_history(evidence, manifest=manifest, observations=observations,
        expected_owner=expected_owner, compiled_max_admins=compiled_max_admins)
    _require(isinstance(captures, list), 'capture list')
    selected = {}
    for capture in captures:
        _require(isinstance(capture, dict) and set(capture) == {'digest','blocks','calls'},
                 'capture fields')
        digest = capture['digest']
        _require(isinstance(digest, str), 'capture digest')
        _require(digest not in selected, 'duplicate capture digest')
        selected[digest] = capture
    expected = {signed['digest'] for row in evidence['superseded'] + evidence['conflicts']
                if row['type'] == 'GovernanceAction' for signed in row['digests']}
    _require(set(selected) == expected, 'exact governance digest coverage')
    headers, heights, calls = {}, {}, {}
    for row in evidence['superseded'] + evidence['conflicts']:
        if row['type'] != 'GovernanceAction':
            continue
        for signed in row['digests']:
            capture = selected[signed['digest']]
            message = row['effect'] | dict(nonce=row['keyField'], expiresAt=signed['expiresAt'])
            verify_governance_signature(message, signed['signature'],
                owner=expected_owner.removeprefix('witness:'), manifest=manifest,
                observations=observations, abi_paths=abi_paths,
                pbc_observation=signed['observation'], blocks=capture['blocks'],
                calls=capture['calls'], approvals=approvals,
                compiled_max_admins=compiled_max_admins)
            # Individual checks established canonical encodings and exact usage.
            for block in capture['blocks']:
                chain, raw = block['chainId'], block['raw']
                key, value = (chain, raw['hash']), (raw['number'], raw['timestamp'])
                _require(key not in headers or headers[key] == value, 'conflicting block facts')
                headers[key] = value
                height = chain, raw['number']
                if checked['declaredSafeLedgerInterval']:
                    _require(height not in heights or heights[height] == raw['hash'],
                             'conflicting safe block hashes')
                heights[height] = raw['hash']
            for call in capture['calls']:
                key = tuple(call[k] for k in ('chainId','blockHash','to','data'))
                _require(key not in calls or calls[key] == call['result'], 'conflicting state call facts')
                calls[key] = call['result']
    return checked | dict(governanceStateSignaturesChecked=len(expected),
        signTimeEstablished=False, latestHeadEstablished=False, approvalPolicyEstablished=False)
