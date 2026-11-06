# Native history RPC capture — 2026-11-06

Classification: **synthetic tested reconstruction/extension result**, paper-derived
HMBC2020. C-F1 WORKING. Integrated execution remains LOCKED. No F case or gate runs.

Internal `evaluation.history_rpc_v2.collect(evidence, *, manifest, observations,
expected_owner, abi_paths, rpcs, output, compiled_max_admins=None, timeout=10.0,
max_calls=1024)` acquires the raw captures needed by `verify_native_history`.

It validates caller-selected history/signatures/context/owner and full owner ABI
inventory before I/O. It plans every declared observation, fault/clear, source
reference and numeric/grant/receipt death getter, deduplicating only identical
required reads. `eth_getBlockByHash` retains every selected hash, including separate
branches at one height. Every hash is re-read after acquisition. Declared safe
intervals also compare both reads with canonical block-number mappings.

Death calls use `eth_call` with an explicit blockHash and requireCanonical flag
under [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898). Safe histories require
canonical blocks; declared fault/clear histories retain conditional labels and
use false. Unsupported hash calls fail visibly with raw receipts; no numeric
fallback occurs. This internal acquisition choice changes no frozen interface,
D50 preimage/open schedule, existing consumer or experiment timing bound.

Both PBC and DBC chain ID/genesis/deployment/binding-anchor checks precede ALL
history reads; both groups run again after ALL cross-chain reads. Clients' selected
origins must match pinned manifest URLs and remain unchanged. Input containers,
ABI selections and file hashes must remain unchanged. The final existing native
checker verifies every block identity/time, exact public ABI death fact and signed
history, rejecting missing/unused captures and preserving mutation exclusions.

The fresh output directory retains API-level method/params/origin/result rows or
exception types in transcript.json, including failed and timed-out requests. The
transport receives copies so it cannot rewrite the retained request. Raw captures
and verification publish as result.json only after every check. Existing output
refuses overwrite. RpcClient separately retains CLI/tool/endpoint receipts when
used by a later authorized recipe. No owner runtime was imported/executed here.

## Verification and provenance

Exact commands, UTC, elapsed time, exits and output hashes: commands.json. Logs are
lossless gzip. inputs-frozen.json contains source hashes/tool versions and both
pre-run peer pins. communication-provenance.json resolves all available remote
communication revisions by file-changing commit; peer-review.json records new
owner paths/hashes and read-only review. verification.json records final results.

New tests initially failed54/54 because the module was absent; implementation
passed54/54. Five review controls then passed59/59 without production changes.
Seven deliberate narrow in-memory guard removals admitted false input refused by
the original collector: origin, call budget, deployment identity, safe canonicality,
caller input drift, post-capture header drift and native death fact verification.
This establishes sensitivity for these controls, not an exhaustive mutation score.
Full root regression/source-bracket results are appended below after completion.

Reproduce the scope: `.venv/bin/python -m pytest evaluation/tests/test_history_rpc_v2.py -q`.
Reproduce deliberate controls: `.venv/bin/python evaluation/evidence/f/v2-history-rpc-20261106/sensitivity.py`.
Whole configured suite: `.venv/bin/python -m pytest -q`.
The proof command is retained in commands.json with its complete Python `-c` source.

## Limits and next permitted work

A fake transport with internally consistent fabricated facts can pass. URL fields,
raw headers/calls and before/after equality do not authenticate a node or prove
consensus, all intervening states or actual native truth. Hash-selected RPC support
on the pinned node has NOT been tested. A transient identity change that returns
to the same observations can evade bracketing. A blocking custom transport cannot
be preempted here; RpcClient has an independent subprocess timeout. No measured
arrival/timing, persistence/power loss, source-state or sign-time semantics, logical
store row projection/export completeness or actual owner lock choreography is proved.
OUTCOME_RECORDED remains distinct from delivery. Existing bit1/bit5 death exclusions
remain in the composed verifier; fault/clear histories never become safe evidence.

Next: source-state/sign-time joins and producer-specific completeness when exact
reviewed owner source/schema/path/locking permits, then independent fault oracle
and finite model. Full source READY/mapping handoffs and separate exact complete
source/tools/config/run FREEZE ACKs precede any integrated services/scenarios.
Qualified historical E remains unchanged;32 Fcases/GateF NOT_RUN; G locked.
Author review is correlated under the explicit no-extra-agents rule.

## Final checked results

Fresh59 scoped tests and2498 configured root tests PASS/exit0. Pytest duration
631.11s; command monotonic631.525s.248selected inputs and186complete execution
sources are unchanged before/after the suite. Frozen manifest SHA256:
`fd41339fcaaa070ec116763217527b52d0455c5fc88e996bd2937608724d39a4`.
All429 ledger READY entries,52 protocol F0 pins,31 published payloads and four
copied fixture bytes verify. Python3.13.13/SQLite3.47.2/Git2.54.0/pytest9.0.2/
jsonschema4.26.0/eth-account0.14.0. Exact versions are in inputs-frozen.json.
The recorded root UTC span is2983.346390s, which differs from its monotonic
631.525112s elapsed. Both are retained in clock-observation.json; no cause or
experimental wall-time performance result is inferred.

Final peer fetch: Agent1 remains8c0285f; Agent2 advancedcde584e to076bde2.
Read the signed-type Byzantine test/digest-routing/mutation changes and latest
owner handoff; exact final hashes/file-changing commits in peer-review-final.json.
Owner33 additional tests/20mutants are read, NOT rerun or adopted. Agent2 still
NOT_READY: real wiring/transport/view/processes/H5/full E regressions/full exact
source READY/consumer mapping remain. No new outbox/ACK since A1-0116/A2-0062.
370latest communication paths resolve without divergent/ambiguous revisions.
