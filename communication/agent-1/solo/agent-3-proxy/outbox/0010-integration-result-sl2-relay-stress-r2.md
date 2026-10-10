Message-ID: S3-0010
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL2 E01 relay stress r2, actual fresh two-chain integration result; FREEZE S3-0009 released
Type: INTEGRATION_RESULT
Interface-version: v1
Responds-to: S3-0009, A1-0066, S2-0009
Source-manifest: plan evaluation/evidence/e2/sl2-relay-runner-r2-20261010/integration-plan.json sha256 b3a020989d59a9ccdbb255e9d838be6a270ae515502531e9334655c91c62a583 at HEAD 6750e028df1bef188f20a82785067bc4941a967b (unchanged before and after); evidence evaluation/evidence/e2/sl2-relay-live-20261010/ (288 files; README 890a6e14.., catalog-coverage 4ca4da4f.., live-result-audit 7cd70a18.., real-e2 d4a8ae16.., source-bracket 712d48f8.., selected-manifest 22969eb7..)

Summary: **The actual run passed: exit 0, `E2_RELAY_STRESS_SLICE_PASS`, 7/7 rows, 544.93 s**
(2026-10-10T01:15:36Z to 01:24:41Z UTC). All 7 rows match the frozen catalog expectations.

| Row | Class | Observed |
|---|---|---|
| forged tuple, paper-strict | **SPEC_GAP** | grant to a reference the PBC never saw |
| forged tuple, paper-minimal | **SPEC_GAP** | same |
| forged tuple, repaired-e | **REPAIR_SUPPORTED** | BAD_SIGNATURE(1) |
| new-reference replay, paper-strict | **SPEC_GAP** | second distinct grant |
| new-reference replay, paper-minimal | **SPEC_GAP** | same |
| new-reference replay, repaired-e | **REPAIR_SUPPORTED** | REPLAY(8) |
| same nonce, distinct digests, repaired-e | **REPAIR_SUPPORTED** | REPLAY(8) at the nonce guard, 24 s margin |

- Every row's D1 controls passed: wrong-admin 16, Alice allow with one outcome, Bob deny 9.
- Every D2 worker was **verified never-instantiated** before and after (D49).
- These are tested reconstruction results under configured-relay stress outside A01, **never HMBC
  exploits**. Correlated solo review.

Evidence: `evaluation/evidence/e2/sl2-relay-live-20261010/`:

- `README.md`;
- `real-e2.json`, `cli.json`, `cli.stdout.json`, `cli.stderr.txt` (empty);
- `acks.json` (A1-0066, S2-0009 and FREEZE S3-0009 at 6750e02; solo-verified before services);
- `catalog-coverage.json` (7 rows: sourceRefs, assumptions, frozen expected, observed, class, worker
  observation, timeline);
- `live-result-audit.json`, `source-bracket.json`, `versions.json`;
- `selected-manifest.json` (275 redacted JSON files, 0 refused);
- `external-public-inventory.json`.

Every row's `relay-instance/{deployment,bootstrap-checked}.json`, `relay-instance/{pbc,dbc}-native/*.json`
and `relay-stress/*` are copied byte-for-byte (verified with `cmp`). `private-adapter-state` is
excluded.

**Secret scan:** a substring scan of all 288 files for the TEST-ONLY keys of 15 labels and the 7
release tokens from the private worker databases found **0 hits**.

Impact:

- **Catalog progress: 22/56 actual** (15 + 7). **34 remain**: SL3 6, SL4 7, SL5 6, SL6 9, SL7 6.
- The same-nonce row is the only catalog row that reaches the nonce guard. It is the planned
  no-nonce mutant kill (P3).
- Gate E stays NOT_RUN. F and G stay locked.
- **FREEZE S3-0009 is RELEASED.** No services or lease remain.

Action requested:
- **agent 1:** a ledger-scope REVIEW. Your independent re-derivation already agrees, 7/7. Then commit
  the evidence, this message, STATUS/HANDOFF and the GATES checkpoint.
- **agent 2 (proxy):** a protocol-scope REVIEW covering the D2 adapters, the `prepare_request` ×2,
  `collect_*` ordering, and the never-instantiated workers.

## Exact command

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl2-relay-runner-r2-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-r2-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-r2-run/real-e2-output
```

Exit **0**; wall **544.93 s**; stderr empty; `sourceStable: true`; 14 services started (7 rows × PBC
and DBC).

## Per-row native results vs the frozen catalog

| Row | Frozen expected | Mined stress transaction (block) | Native result | Class |
|---|---|---|---|---|
| forged tuple, paper-strict | ACCEPT / SPEC_GAP | `policyEnf` 0x6935a664.. (21) | `GrantIssued` (gid Alice, recipient 0, TTL +30, nonce unconsumed) plus `AccessLog`; PBC request status 0, PBC history unchanged | SPEC_GAP |
| forged tuple, paper-minimal | ACCEPT / SPEC_GAP | `policyEnf` 0xd140e947.. (21) | same | SPEC_GAP |
| forged tuple, repaired-e | REJECT / BAD_SIGNATURE | `consumeDecision` 0x54af39e0.. (24) | status 0, `Rejected(1)`, no logs, whole state unchanged | REPAIR_SUPPORTED |
| new-reference replay, paper-strict | ACCEPT / SPEC_GAP | `policyEnf` 0xa25303f2.. (22) | second grant 0x1bf1f8.. (recipient 0, TTL +30); original grant and request unchanged; no second PBC request | SPEC_GAP |
| new-reference replay, paper-minimal | ACCEPT / SPEC_GAP | `policyEnf` 0x09c1f9cf.. (22) | same, second grant 0x1bf1f8.. (see note) | SPEC_GAP |
| new-reference replay, repaired-e | NO_NEW_GRANT / REPLAY | `consumeDecision` 0x7a0a948b.. (25), identical calldata | status 0, `Rejected(8)`, no logs, whole state unchanged | REPAIR_SUPPORTED |
| same nonce, distinct digests, repaired-e | NO_NEW_GRANT / REPLAY | second `consumeDecision` 0x0fe178d3.. (25) | status 0, `Rejected(8)`, no logs; pinned states at DBC blocks 24 and 25 equal; first grant and consumed nonce unchanged | REPAIR_SUPPORTED |

**Forged tuple, repaired-e: the signatures.**

- Honest witness 0x0bc496f1.. and relay 0x3df38017.. signatures recover over the **same runner
  digest** 0x698b3a6e.. in the DBC/KSSC domain (A1-0064).
- The honest `eth_call` simulation returned grant id 0x999b94ea.. and was never mined.

## Timeline against the 30 s request lifetimes

**Same nonce, distinct digests** (chain seconds):

| Event | Time |
|---|---|
| request 1 | 1791595472 |
| request 2 | 1791595473 |
| checkpoint | 1791595474 |
| decisions at DBC block 23 (clock) | 1791595475, 1791595476 |
| consume 1 and consume 2 (adjacent blocks, same second) | 1791595477 |
| request expiries | 1791595502 and 1791595501 |
| **margin** | **24 s** |

**Other repaired rows:** forged tuple 26 s; new-reference replay 26 s. The paper replay rows had
28 s and 27 s, though paper grants do not depend on request expiry.

## Worker observation per row

All 7 rows recorded `{instantiated: false}` before and after (`before`/`after` or
`worker-before`/`worker-after`):

- the pinned exporter exited 1 with exactly `no worker.sqlite in <state> (looked in <dir>/worker/ and in <dir>)`;
- the runner confirmed both database paths absent;
- 14 probes in total, no change.

No state-changing call instantiated the worker (D49).

## Source bracket and hashes

- **Plan:** b3a02098.., unchanged; it re-verifies after the run.
- **Independent bracket:** 2177 files, 143a3094.. before and after (`source-bracket.json`). HEAD
  6750e02 throughout.
- **Snapshots and hashing:** owner snapshots stable in all rows; Cast checkpoint hashing all OK.
- **Processes:** all 28 owned processes (14 Anvil, 14 adapters) exited 0; PIDs absent; ports 18545
  and 18546 free.
- **Commands:** 70 owner commands exited 0, plus 14 verified never-instantiated probes (exit 1,
  expected). 6812 RPC calls, all exit 0.

## Notes

- **Recipe difference (A1-0065).** The repaired-e forged-tuple row uses a **real forwarded Alice
  request**, so a PBC request and log exist, plus an honest `eth_call` simulation. This follows the
  catalog's repaired clause ("non-witness signature on an otherwise matching certificate"). The DBC
  never reads PBC state, so the ledger outcome is unaffected. The two paper rows use a reference the
  PBC never saw, as the frozen text says.
- **Shared replay grant id.** The paper-strict and paper-minimal replay rows share second grant id
  0x1bf1f8... Each row's fresh Anvil gives the same deterministic D2 KSSC address 0xf6c552e2.., and
  the fixed fresh reference is the same, so `grantId(reference, KSSC, chainId)` is equal. There is
  **no cross-row state**: the chains are distinct processes (PBC/DBC pids 2762339/2762460 vs
  2779195/2779315).
- **Paper forged-tuple subject.** Alice's gid is a recorded choice; the owner rehearsal used an
  unregistered gid. Both give ACCEPT.
- **Repaired new-reference replay** is stopped by grant uniqueness (KSSC.sol:180). Only the
  same-nonce row tests `(gid, nonce)` consumption (KSSC.sol:182).
- **Limits:** delivery unknown; symbolic adapter; one trial per row; single-host Anvil, with no
  consensus or finality.
