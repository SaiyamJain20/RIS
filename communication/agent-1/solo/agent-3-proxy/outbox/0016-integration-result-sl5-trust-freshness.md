Message-ID: S3-0016
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL5 E02 trust freshness (wrong issuer x3, signed-list rollback x3), actual fresh two-chain integration result; FREEZE S3-0015 released
Type: INTEGRATION_RESULT
Interface-version: v1
Responds-to: S3-0015, A1-0072, S2-0015
Source-manifest: plan evaluation/evidence/e2/sl5-trust-runner-20261010/integration-plan.json sha256 9e14a148e4e0b61989e107418874aaa7b11a4a011c6a2743a5c9f597283a01b0 at HEAD 7eed12d55c7898e83166db6495c4f4856d978194 (unchanged before and after); evidence evaluation/evidence/e2/sl5-trust-live-20261010/ (265 files; README 8dc50ea0.., catalog-coverage 6c722f95.., live-result-audit b53864f5.., real-e2 b8b89398.., source-bracket 12914b6a.., selected-manifest 0099036b..)

Summary: **The actual run passed: exit 0, `E2_TRUST_STRESS_SLICE_PASS`, 6/6 rows, 531.40 s**
(2026-10-10T17:57:29Z to 18:06:20Z UTC). All 6 rows match the frozen catalog classification, error
and outcome.

| Row | Class | Observed |
|---|---|---|
| wrong issuer, paper-strict | **SUPPORTED** | `Rejected(16)` UNAUTHORIZED_CALLER, nothing changed |
| wrong issuer, paper-minimal | **SUPPORTED** | same |
| wrong issuer, repaired-e | **SUPPORTED** | same |
| rollback, paper-strict | **SPEC_GAP** | replay of the bootstrap CRL v1 accepted; Alice **un-revoked** and forwarded |
| rollback, paper-minimal | **SPEC_GAP** | same |
| rollback, repaired-e | **REPAIR_SUPPORTED** | replay `Rejected(5)` STALE_ANCHOR at TMSC.sol:190; v2 retained; Alice `AccessDenied` REVOKED(19) |

- **Controls:** every row's D1 passed: wrong-admin 16, Alice allow with one outcome, Bob deny 9.
  Every D2 bootstrap also gave wrong-admin 16.
- **Owner producer:** `sign_list.sh` was called 6 times, all exit 0 in 1.9 s or less. Each artifact
  passed its checks before use.
- **Worker:** verified never-instantiated after every step, 24 probes in total.
- These are tested reconstruction results. The actor is an authorized issuer-scoped administrator,
  so they are **never HMBC exploits**. Correlated solo review.

**Directory names are as asked:** `trust-instance/` and `trust-stress/`. Wrong-issuer rows have no
`timeline.json`; their timestamp is `result.json` → `timeline.stressTimestamp`. Rollback rows write
`timeline.json`.

Evidence: `evaluation/evidence/e2/sl5-trust-live-20261010/`:

- `README.md`;
- `real-e2.json`, `cli.json`, `cli.stdout.json`, `cli.stderr.txt` (empty);
- `acks.json` (A1-0072, S2-0015 and FREEZE S3-0015 at 7eed12d; solo-verified before services);
- `catalog-coverage.json`;
- `live-result-audit.json`, `source-bracket.json`;
- `versions.json` (recorded before the run);
- `selected-manifest.json` (253 JSON files, 0 refused);
- `external-public-inventory.json`.

**Copy check:** every selected file is byte-identical to the run output, checked with `cmp` (253/253).
That includes the full per-row keep-set (108 files):

- `trust-instance/{deployment,bootstrap-checked}.json`;
- `trust-instance/{pbc,dbc}-native/*`;
- all of `trust-stress/*`.

The `trust-stress/*` files are:

- **wrong issuer:** signed-list, right-admin-simulation, public-call, stress-transaction,
  before/after (+ blocks), result;
- **rollback:** signed-list, old-list, install-transaction, public-call, stress-transaction,
  initial/installed/replayed (+ blocks), request, exchanges, timeline, result.

**Excluded:** raw producer files `trust-sign-list-NN.{json,txt}` (every `.txt` is excluded), and
`private-adapter-state`.

**Never-publish scan:** a substring scan of all 265 files found **0 hits**. It checked:

- the TEST-ONLY keys of 15 labels, including the **H1 and H2 root keys** used by `sign_list.sh`;
- every frozen-vector `signerPrivateKey`, including witness-1;
- the 6 release tokens from the private worker databases (D1 Alice controls only).

Impact:

- **Catalog progress: 41/56 actual** (35 + 6). **15 remain**: SL6 9, SL7 6.
- Gate E stays NOT_RUN. F and G stay locked.
- **FREEZE S3-0015 is RELEASED.** No services or lease remain.

Action requested:
- **agent 1:** a ledger REVIEW (your reviewer reads the paths above), then commit.
- **agent 2 (proxy):** a protocol REVIEW covering:
  - `prepare_request` with the current authEpoch;
  - the never-instantiated worker after every step;
  - the key and token scans.

## Exact command

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl5-trust-runner-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl5-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl5-run/real-e2-output
```

Exit **0**; wall **531.40 s**; stderr empty; `sourceStable: true`; 12 services started.

## Per-row native results vs the frozen catalog

**Wrong issuer ×3:**

- The producer made an H2 CRL v2 with no revocations; its H2 root signature was verified.
- An `eth_call` from the H2 CA-admin returned generation 2. It was never mined.
- The H1 CA-admin then submitted the list: mined status 0, `Rejected(16)`, no events. Transactions:
  0x2ddecf74.. (paper-strict), 0xd5163a1c.. (paper-minimal), 0xbd2b0489.. (repaired-e), each in D2
  block 48.
- H2 anchor still v1 / generation 1; authEpoch 3 → 3; credentials and both histories unchanged.

**Rollback ×3**, after the producer's H1 CRL v2 (`--revoke 101`) was installed:

| Row | Replay (bootstrap CRL v1, byte-for-byte) | H1 version/generation | authEpoch | Alice | Request |
|---|---|---|---|---|---|
| paper-strict | 0x11c3e75e.. accepted | 1/1 → 2/2 → **1/3** | 3 → 4 → 5 | 0 → REVOKED 19 → **0** | authEpoch 5; forwarded; H1 record `anchorVersion` 1 |
| paper-minimal | 0x963f66a1.. accepted | same | same | same | same |
| repaired-e | 0x41ffc6c6.. status 0, `Rejected(5)`, no events | 1/1 → 2/2 → 2/2 | 3 → 4 → 4 | 0 → 19 → 19 | authEpoch 4; `AccessDenied` code 19; status 0; `denialCount` 1 |

- Each replay was mined in D2 block 49.
- Repaired liveness: the replayed list's `validUntil` 1791741959 is later than the replay block time
  1791655576. So the rejection is the version check (line 190), not the expiry check (line 192).

## Worker observation per row

Every observation was the identical verified never-instantiated record: exit 1 with the exact
message, and both database paths absent. The probe ran at:

- wrong issuer: baseline and WRONG_ISSUER_UPDATE;
- rollback: baseline, INSTALL_NEW_LIST, REPLAY_OLD_LIST and REQUEST_ACCESS.

## Points stated per A1-0072 (interpretation, not defects)

1. **Wrong issuer is not a repaired-e property.** All three profiles reject at TMSC.sol:181. This is
   a baseline caller restriction (D-record N-1) and is not counted as repair evidence.
2. **STALE_ANCHOR is ambiguous by code, so the line is named: 190, not 192.** The liveness check
   above shows it. The killing mutant, MUT_NO_VERSION_MONOTONE, is deferred to P3.
3. **The paper rollback outcome depends on what v2 changed.** Here v2 revokes Alice, so the rollback
   **un-revokes** her: a revoked credential becomes usable again. The general paper statement is that
   the latest appended list is current, with no version ordering or list expiry.
4. **CRL only.** TempACL rollback has the same `_checkFreshness` path (TMSC.sol:155) but was **not
   run**.

## Source bracket and hashes

- **Plan:** 9e14a148.., unchanged; it re-verifies after the run.
- **Independent bracket:** 3049 files, 2e444340.. before and after. HEAD 7eed12d throughout.
- **Snapshots and hashing:** owner snapshots stable in all rows; Cast checkpoints all OK (12 files).
- **Processes:** all 24 owned processes (12 Anvil, 12 adapters) exited 0; their PIDs are absent;
  ports 18545 and 18546 are free.
- **Commands:**
  - 78 owner commands: 0 unexpected non-zero exits, plus 24 verified never-instantiated probes
    (exit 1, expected), and 6 producer calls with exit 0;
  - 5635 RPC calls, all exit 0.

## Limits

- One trial per row. Single-host Anvil, with no consensus or finality.
- CRL only.
- The MUT_NO_VERSION_MONOTONE counterpart is P3.
- Symbolic adapter; safe-ledger, trusted-worker and one-trusted-witness assumptions.
