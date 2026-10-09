# E1 real paper-strict controls and port-probe recovery

Paper-derived HMBC2020 reconstruction, synthetic fixtures, symbolic decryptability.
This checkpoint is a **tested reconstruction result**, not a paper vulnerability or
RQ gate. Fresh actual paper-strict services passed wrong-admin rejection16 (baseline
issuer restriction), registered Alice access/release/outcome and registered Bob
policy denial9 with no grant/nonce/worker release. The all-profile CLI exited2/FAILED
after113.919s: the paper-minimal port probe saw EADDRINUSE after the strict services
had stopped. Paper-minimal started no services; repaired-e was not run. The retained
profile record says RUNNING for the interrupted pre-service profile; it is not a
completed result. Only3 of9 controls ran.

Exact original plan1899126e.. and A1-0037 at79dacb061a037c8254b11cff732aca88751a129f
(message SHA422bc4ff..) / A2-0018 atc8d89d85f654823a511be21e13fe52fabc8722c9
(message SHAab30d00a..) passed header/hash/ancestry verification before startup.
The full ACK index/messages and verified-inputs.json preserve exact provenance and
scope exclusions. Ledger9d6911d/106-entryec213160.. and protocol465aff5/105-entryeb236421..
were extracted from exact reviewed owner blobs, not branch tips. Later E2 source
remains excluded. No peer module/runtime mailbox, frozen interface or dependency
was edited; no extra agent/worktree, main/force push or history rewrite.

Diagnosis: ss showed no listeners and DBC TIME_WAIT; an ordinary bind failed98
while SO_REUSEADDR succeeded. A real loopback regression reproduced the failure.
The port probe now uses SO_REUSEADDR, permitting the next server's bind after
TIME_WAIT while still refusing active loopback and wildcard listeners. No process
is adopted or killed. This remains a pre-start check, not atomic port reservation.
RED1fail/2pass, GREEN18pass including freeze guards; full evaluator414pass, exit0,
55.94s pytest/56.125s subprocess on75 stable explicit inputs. The actual failed run
had74 stable inputs;211 snapshot inputs and15 frozen copies verify. Source/command/
output hashes, all exits, versions and helper failures are retained. Git2.54.0,
Python3.13.13, Foundry1.8.5, solc0.8.37 and root packages/lock remain unchanged.

Actual PBC340838, DBC340960, adapter345111 ended with exit0; their /proc identities
were absent at audit. Service manifests record timestamps/ports/environment and
transport digests. Only recorded owned processes were stopped. Scheduled guard
and separate coordinator lock remain held through publication; own finally cleanup
and remote SHA verification are recorded in the external run and automation memory.

A3-0027 logical freeze is released after failure. **A3-0029 requests the revised
plan 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008**, runE1-20261008-port-recovery. The only runtime
hash delta is evaluation/e1.py; ports, budgets, Anvil flags, funding/deployer role,
owner pins, commands, control recipe, key custody, frozen interface and dependencies
are unchanged. Old ACKs are explicitly rejected for the revised plan. Both owners
must ACK the exact new hash before new services. No revised real run has occurred.

Selected public native receipts/views, deployment, seven-signature bootstrap,
redacted exchange/worker evidence, service/command manifests are in failed-run/.
Raw RPC logs and private synthetic adapter/snapshot/build state remain under
/home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261008T195325Z/real-e1-output; external-output-inventory.json hashes the public output
inventory. Private state, tokens, keys, Forge caches/broadcast and whole snapshots
are excluded from this published package. RELEASE_SENT remains attempted send;
delivery unknown. No ABE/provider-integrity/consensus/recovery/power-loss proof.

Author-only self-review, weaker than independent review; no additional reviewer
agent authorized. Rulings: preserve failed/partial evidence instead of nine-control
success (cost: E1 stays open); renew exact ACKs for changed runtime bytes (cost: a
review round); honor confirmed checkout/no-extra-agents (cost: no fresh reviewer).
No deferred code-review issue in this patch. All56 schedules and RQ gates NOT_RUN;
four paper crash cases BLOCKED/unproved; E2/E3/F/G remain gated.

After both exact A3-0029 ACKs, reverify the plan and immutable ACK provenance and run:

```bash
.venv/bin/python -m evaluation.e1 --plan evaluation/evidence/e1/port-recovery-20261008/integration-plan.json --acks /absolute/path/to/new-exact-ack-index.json --output /absolute/path/to/fresh-private-output
```

Retain this failed attempt; require all nine fresh controls and cleanup before
closing E1. Do not use the old acks.json in this directory to authorize that run.

Publication preflight caught trailing whitespace in raw pytest RED output (exit2, no commit/push). The exact raw ports-red.stdout remains in the external run, with its original captured SHA. ports-red.normalized.txt strips trailing line whitespace for committed display only; ports-red-normalization.json binds both hashes. Runtime, test and plan bytes unchanged.
