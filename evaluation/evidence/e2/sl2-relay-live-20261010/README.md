# SL2 r2 actual run: E01 relay stress ×7, all PASS

Paper-derived HMBC2020 reconstruction. Synthetic only. Symbolic adapter, with safe-ledger,
trusted-worker and one-trusted-witness assumptions. E/RQ1 is active; gate E is NOT_RUN; F and G are
locked.

**Solo phase (A1-0059):** every review and ACK is **correlated self-review** (same model).

## Run

**Authorization:**

- Plan `evaluation/evidence/e2/sl2-relay-runner-r2-20261010/integration-plan.json`, SHA-256
  `b3a020989d59a9ccdbb255e9d838be6a270ae515502531e9334655c91c62a583`.
- FREEZE S3-0009, ACKs A1-0066 and S2-0009, all at commit 6750e02.
- `acks.json` was verified by the solo verifier before services.
- This plan replaces d67f1786, whose run failed on a runner defect (S3-0008, `../sl2-relay-failed-20261010/`).

**Command** (`export PATH="$HOME/.foundry/bin:$PATH"`):

```
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl2-relay-runner-r2-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-r2-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-r2-run/real-e2-output
```

**Result:** exit **0**, `E2_RELAY_STRESS_SLICE_PASS`, 2026-10-10T01:15:36Z to 01:24:41Z, **544.93 s**.
Stderr is empty (`real-e2.json`, `cli.json`).

## Results against the frozen catalog (`catalog-coverage.json`)

| Row | Frozen expected | Observed (mined) | Class | Margin to request expiry |
|---|---|---|---|---|
| E01-forged-tuple-paper-strict | ACCEPT / SPEC_GAP | relay `policyEnf` with a reference the PBC never saw: `GrantIssued` (recipient 0, TTL +30) plus `AccessLog`; PBC status 0, PBC history unchanged | **SPEC_GAP** | n/a (paper tuple has no expiry) |
| E01-forged-tuple-paper-minimal | ACCEPT / SPEC_GAP | same | **SPEC_GAP** | n/a |
| E01-forged-tuple-repaired-e | REJECT / BAD_SIGNATURE | honest `eth_call` simulation returned the grant id; witness 0x0bc4.. and relay 0x3df3.. signatures over the same digest 0x698b3a6e..; mined relay-signed copy `Rejected(1)`, no logs, no change | **REPAIR_SUPPORTED** | 26 s |
| E01-new-reference-replay-paper-strict | ACCEPT / SPEC_GAP | original grant, then the same tuple under a fresh reference: second distinct grant 0x1bf1f8..; no second PBC request | **SPEC_GAP** | 28 s |
| E01-new-reference-replay-paper-minimal | ACCEPT / SPEC_GAP | same; second grant 0x1bf1f8.. (see note) | **SPEC_GAP** | 27 s |
| E01-new-reference-replay-repaired-e | NO_NEW_GRANT / REPLAY | identical re-consume: `Rejected(8)`, no logs, no change (grant uniqueness, KSSC.sol:180) | **REPAIR_SUPPORTED** | 26 s |
| E01-same-nonce-distinct-digests-repaired-e | NO_NEW_GRANT / REPLAY | 2 requests (expiry 1791595502 and 1791595501); one checkpoint after both; both certificates collected at DBC block 23; consume first (grant), then second `Rejected(8)`; pinned pre/post equal | **REPAIR_SUPPORTED** (nonce guard reached) | **24 s** |

**All 7 rows match their frozen expectations.**

**Same-nonce timeline** (chain seconds, `run/…/relay-stress/timeline.json`):

| Event | Time |
|---|---|
| request 1 | 1791595472 |
| request 2 | 1791595473 |
| checkpoint | 1791595474 |
| decisions (DBC clock) | 1791595475 and 1791595476 |
| consume 1 / consume 2 | 1791595477 (adjacent blocks, same second) |
| expiry (both requests) | 1791595501 / 1791595502 |
| **margin** | **24 s** |

**Worker observation:** every row recorded a **verified never-instantiated D2 worker** before and after.
The pinned exporter exited 1 with its exact message, and both database paths were absent. This made
14 probes in total (D49), and none changed.

**Controls passed in every row** (D1): wrong-admin (16, also in the D2 bootstrap), Alice allow with
release and one outcome, Bob policy deny (9).

## Notes

- **Recipe difference (A1-0065).** The repaired-e forged-tuple row uses a **real forwarded Alice
  request**, so a PBC request and log exist, plus an honest `eth_call` simulation. This follows the
  catalog's repaired clause ("non-witness signature on an otherwise matching certificate"). The DBC
  never reads PBC state, so the ledger outcome is unaffected. The paper rows use a reference the PBC
  never saw.
- **Shared replay grant id.** The paper-strict and paper-minimal replay rows share grant id
  0x1bf1f8... Each row's fresh Anvil pair gives the same deterministic D2 KSSC address (0xf6c552e2..),
  and the fixed fresh reference is the same. There is no cross-row state: the chains are distinct
  processes (pids 2762339/2762460 vs 2779195/2779315).
- **Paper forged-tuple subject.** Using Alice's gid is a recorded choice (ambiguity). The owner
  rehearsal used an unregistered gid; both give ACCEPT.
- **Repaired new-reference replay** cannot reach the nonce guard; only the same-nonce row does.

## Integrity, processes and custody

- **Sources stable:**
  - the plan re-verifies after the run;
  - the independent bracket of 2177 files is 143a3094.. both before and after;
  - HEAD was 6750e02 throughout;
  - every row's owner snapshots are stable; Cast checkpoints are all OK (14 clients).
- **Processes:** all 28 owned processes (14 Anvil, 14 adapters for D1 and D2) exited 0, and their
  PIDs are absent. Ports 18545 and 18546 are free.
- **Commands:** 70 owner commands exited 0, plus the 14 verified never-instantiated exporter probes
  (exit 1, expected). 6812 RPC calls, all exit 0.
- **Public evidence:** 275 redacted JSON files under `run/`, including every row's
  `relay-instance/{deployment,bootstrap-checked}.json`, `relay-instance/{pbc,dbc}-native/*.json` and
  `relay-stress/*`, copied byte-for-byte.
- **Secret scan:** the substring scan of all 283 files checked the TEST-ONLY keys of 15 labels and the
  7 release tokens in the private worker databases. 0 hits.
- **Not published:** `private-adapter-state`, raw logs and snapshots stay in `tmp/p3/sl2-r2-run`,
  hashed in `external-public-inventory.json`.

## Limits

- Tested reconstruction results under configured-relay stress outside A01, never HMBC exploits.
- Delivery unknown. One trial per row. Single-host Anvil.
- Grouped RPC checks cannot detect a transient reorg restored between boundaries.
