# C-E2 symbolic correspondence and exact owner-tool review

Run began 2026-10-08T23:13:48Z (2026-10-09 IST), base agent-3
7fbd1edf5abcd2b6b1a74df81907e0a2ff10d01b. Paper-derived reconstruction,
synthetic fixtures only. E0 frozen; actual E1 9/9 historical evidence retained.
**Gate E NOT_RUN; all 56 real catalog schedules NOT_RUN; F/G locked.**

## Actual owned verification

Expectations were written in evaluation/models/e/README.md before execution.
Initial real-model tests failed 4/4 because both models were absent. The final
seven real ProVerif/sensitivity checks pass. Final root command
`.venv/bin/python -m pytest -q -p no:cacheprovider`: exit 0, 421 passed / 55.97s
pytest; 80 code/model/config inputs stable before/after. The earlier full evaluator
command also passed 421 but its bracket omitted .pv/model README; the final run
corrects that instrumentation limitation. Both standalone ProVerif commands
exit 0 on exact SHA-verified 2.05 binary, separately bracketed on stable inputs.

| Query | Full binding | Destination omitted deliberately |
|---|---|---|
| Grant agrees with prior UserRequest on all 8 fields | true | false, reconstructed trace |
| Grant agrees with prior WitnessDecision on all 8 fields | true | false, reconstructed trace |
| Witness agreement excluding destination | true | true |
| No allowed grant reachable | false: positive path reconstructed | false: positive path reconstructed |
| No policy-denied grant reachable | true | true |

Fields: request identity, subject, data, source chain/PSC, destination chain/KSSC,
action, policy, nonce. Scratch deny-all, policy-bypass and unsigned-envelope
controls change the relevant verdicts. Queries are non-injective; replay remains
possible. There is one fixed honest GID, one allowed/denied data name, one fixed
source/destination/action/policy version and fresh request ids/nonces. These
results do not prove every real user/configuration or implementation equivalence.

The model assumes perfect signatures, uncompromised keys and one trusted witness.
UserRequest abstracts authenticated admission, WitnessDecision honest source
observation/policy. No mutable trust, clock, nonce storage, EIP-712 encoding,
worker recovery/audit, actual ABE, computational cryptography, quorum or consensus
is modeled. Its mutant differs from the deployed ledger destination mutant.
The paper Figure 6, PDF page 12 / printed134404, was visually inspected from the
previous preserved render; III-D3/III-E2 text and SPEC/PLAN supply the expectation.
The signatures and witness are reconstruction choices, not paper algorithms.

## Exact peer review, without importing owner outcomes

133 newest communication revisions, no divergences; A1 read through0046 and A2
through0026. origin/agent-1 48d85e8ce7b1379a56873ee38e6c5f36bd249f30;
origin/agent-2 2fd871dd29e1937b3f2dcb660a1c90cbf3e89ac3. File-changing commits
and SHA-256s in communication-delta.json. Owner claim sheets, catalog rehearsals
56/56 and revocation-window measurements remain OWNER evidence. They do not
close Agent3 integrated gates or set observed oracle expectations.

A1-0039 exact pin933d2a75483a08e7374cd417a6cf8a9e5c13a33c /195 entries /
c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660
verified against immutable Git blobs. Source-reviewed offered SignList shell/script
and handoff; contract/deployment/bootstrap runtime bytes equal E1 pin9d6911d.
Its owner rehearsal scripts are NOT adopted as runner inputs.

A2-0020 exact pin0716a8e2d46f985f35a612d42acaae02ab8701a4 /108 entries /
d16ddad897dac7df3d406bab200f85e5dba1c27595a3bbaf5fe658640ba184a5
verified. Production/exports/ABI bytes equal E1 pin465aff5. Hook source
f0ab2400db5b3667f92ad2e9061b931c8acc94696f42bcd7080e7cdd4e39bde4
reviewed against adapter/worker commit ordering. Independently executed four
refusal controls (expected exit1, empty stdout, no traceback/state created) and
production import boundary (exit0/no testtools loaded). All109 extracted snapshot
files stable. No chain, adapter service, crash or recovery run here.

A1-0040 is a scoped REVIEW, A2-0021 ACKs A1-0041 owner coordination; neither ACKs
Agent3's exact new contract. Proposed start-contract r1 SHA-256 `1ae63cfb2dde803645ef7a84a58151c0b0a842554f79907c94a7dcd74c89f48c`
selects the alternate TEST-ONLY command, exact point/EOF/response/exit86 semantics,
same-state production restart before original expiry, delivery unknown and OptionA.
A3-0032 requests BOTH exact scoped ACKs before promotion. A full E2 runner/config
FREEZE with both exact plan ACKs still precedes service execution.

Corrections retained: catalog wrong-destination hits source PSC step1, so it
cannot kill the no-destination-binding step2 mutant; that accept/reject result is
unit-only. Revocation probes must record effective DBC block/pending time; idle
latest-block time is stale. Owner interval-mining W measurements are not Agent3
measurements. Paper crash labels stay BLOCKED/unproved; no durability inferred.

## Evidence and operating record

Commands include argv/cwd/start/end/exits/stdout-stderr hashes/source brackets;
actual versions Python3.13.13/Git2.54.0/pytest9.0.2/eth-account0.14.0/jsonschema4.26.0,
ProVerif2.05/c1087205..; no dependency or binary change. Model/source/paper/lock
hashes in verification.json SHA-256 `0bec2fa292489efbbf2986cbc6c0d1422f2c4cc3a253e8084dbdace9f996e597`. All15 frozen copies and exact
local/immutable-owner originals verified. Initial frozen-copy inspection helpers
failed; failed output retained, corrected exact-owner lookup succeeds. These are
helper errors, not research refutations. No private synthetic state/token/key
output was produced or published.

Safely stale scheduled lock: same host, >9600s old, owner401986 and guard402163
absent. Metadata/decision preserved before recovery; new exclusive lock/live guard
463584 and separate coordinator flock463692 held through publication. Prior
untracked evaluation/evidence/scheduled-runs files are preserved, unstaged. No
peer source/mailbox/archive/frozen edits, extra agent/worktree, unreviewed merge,
main/force/reset/rebase/stash/clean/blanket stage. Finally cleanup/push SHA is
recorded in external run and automation memory; future cleanup is not assumed.

Separate author self-review checked query scope/nonvacuity/counterexample,
key secrecy assumptions, model-vs-runtime distinction, exact source/ACKs and
ownership. No fresh independent reviewer is allowed; self-review is weaker.
No material patch finding or deferred minor. Scope rulings: existing checkout
and no extra reviewer per human (cost: weaker review); fixed E signature
abstraction omits durable state (cost: no replay/recovery proof); proposed hook
awaits exact review and later full plan (cost: real fault evidence still pending).

Next: exact start-contract ACKs, continue independent public C-E2 runner/oracles,
then complete source/tool/config recipe, FREEZE/both exact plan ACKs and fresh
real strict/minimal/repaired schedules plus meaningful mutants. RQ1 report,
all3 same-report/source ACKs and gate E precede F. No human action required.

Publication check: unrestricted staged whitespace check exits2 solely for verbatim pytest/ProVerif stdout whitespace. Source/docs/JSON check excluding raw stdout/stderr exits0. Raw bytes are intentionally preserved to match command-output hashes; no source whitespace failure.
