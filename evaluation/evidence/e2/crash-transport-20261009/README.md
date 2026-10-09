# C-E2 accepted startup supplement and process-transport slice

Paper-derived HMBC2020 reconstruction; synthetic fixtures only. This checkpoint
accepts the scoped startup supplement and implements Agent3's process observer.
No real adapter, chain, worker crash/recovery or fault catalog was executed.
Gate E and all56 integrated schedules remain NOT_RUN; four paper crash cases
BLOCKED/unproved; F/G locked. Actual prior C-E1 nine controls remain historical.

## Exact acceptance

`start-contract-acceptance.json` records exact message commit/path/hash, accepted
header/hash, owner ancestry and scope. A1-0047 at af7a60dd650c5d0c9b5d7df1fb5afbde3e30526d
accepts ledger grant/expiry/native facts and ledger933d2a7. A2-0027 at
0dbaed2331fd89ce3843625cd44bdc677dd4d490 accepts startup/process/worker semantics and
protocol0716a8e. Both bind contract1ae63cfb2dde803645ef7a84a58151c0b0a842554f79907c94a7dcd74c89f48c.
All195 ledger +108 protocol inventory entries and hookf0ab2400.. reverified against
Git blobs. A2's Accepted-plan-sha256 alias is expressly NOT a service plan ACK.
Their exclusions are preserved. Proposed contract bytes stay immutable; this
sidecar carries acceptance. A separately published full FREEZE/both plan ACKs
remain mandatory before services. Python3.13.13 hook behavior on a real worker
and the runner retry within the original30s expiry remain unproved.

## Process contract and evidence

`JsonLinesProcess.exchange_crash` requires an empty stdout EOF at after_intent;
after_send requires one response checked by the caller's raising validator and
then EOF. Natural exit86 and empty stderr required; one shared finite deadline
covers write/read/EOF/exit. Invalid point rejects before input; extra/partial
frames, wrong exit, parser/validator rejection and hangs fail with cleanup of the
owned direct child. The method returns a response only in memory and publishes
request/response commitments, argv/cwd/PID/exit/timing/error class. Callers must
supply no secret-bearing command arguments and must independently verify frozen
response schema, grant, worker intent/attempts/cache and recovery facts. Successful
process observation alone cannot classify an E scenario or establish delivery.
No descendant supervision or power-loss/OS-kill guarantee is claimed.

Expectations derive from the accepted startup contract, not observed owner outputs.
Synthetic child scripts have literal outcomes independent of the transport. RED14
missing-method failures are retained in transport-red.*. First implementation
run1fail/47pass exposed a test-fixture error: its -c argv contained a synthetic
response token literal, so normal argv logging retained it. Diagnosis traced the
failure to argv, not pipe logging; moving the synthetic program to a file matches
actual module-entrypoint argv. Corrected transport/process suites48pass/exit0.
Full project `.venv/bin/python -m pytest -q -p no:cacheprovider`:435pass,58.38s pytest,
58.562s wall,exit0. `source-bracket.json`:100 source/config/model/fixture inputs
stable before/after,15 immutable frozen copies rechecked. versions.json records
Python3.13.13/Git2.54.0/pytest9.0.2/eth-account0.14.0/jsonschema4.26.0. Command records
include argv/cwd/start/end/exit/stdout+stderr hashes; full outputs retained.
Navigation mistakes are preserved in helper-failures.json, not research results.

## Review, scope and continuation

Author self-review covers EOF/exit vs ordinary replies, late extra frames,
monotonic deadline, unforced exit, callback rejection, no capability transcripts,
cleanup, ACK aliases/scopes, exact owner pins and unchanged frozen bytes. This is
weaker than independent review; user prohibits extra agents and worktrees.
No material deferred patch finding. Shared normal exchange behavior remains
covered by the process tests. No tool/dependency/key-custody/source-paper assumption
change; no peer module/mailbox or archive edit. Source hashes changed in Agent3's
transport and require new full plan bytes before any integration.

Ruling: use existing human-confirmed checkout and author review per user rather
than skill worktree/reviewer defaults; cost no independent fresh review.
Ruling: preserve proposal bytes and promote scoped acceptance in a sidecar; cost
historical pending prose must be read with this acceptance record.
Ruling: record a bounded coherent transport slice; complete worker/native/oracle
composition and full E2 plan remain required, with no service/gate result inferred.

Next: implement full Agent3 public E2 schedules/oracles/recovery collection and
clock probes; publish complete source/tool/config/fixture FREEZE, obtain both exact
plan ACKs, execute fresh real strict/minimal/repaired/mutant/recovery matrix, draft
RQ1 report and obtain all3 same-source/report ACKs before gate E/F. Owner window
measurements and no-destination-mutant masking caveat remain owner evidence.

Raw failing pytest stdout is preserved byte-for-byte, including its trailing
whitespace. Staged source/docs/JSON whitespace checks pass; the unrestricted
check reports only those two raw stdout captures. No raw output was normalized.
