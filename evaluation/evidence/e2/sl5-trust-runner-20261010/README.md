# SL5: E02 trust-freshness runner and plan (no services yet)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), solo phase (A1-0059, A1-0061 D-6, A1-0064). **Correlated self-review.**

**Status:** runner implemented **test-first** and unit-verified; plan frozen as S3-0015. No service
has run. **No catalog row is completed by this checkpoint.**

## Rows, frozen expectations and pinned ledger facts (933d2a7)

| Row | Frozen expected | Ledger fact (TMSC.sol) | Agreement |
|---|---|---|---|
| E02-wrong-issuer-{paper-strict, paper-minimal, repaired-e} | REJECT / SUPPORTED / UNAUTHORIZED_CALLER | `_authorizeUpdate` checks the issuer-scoped CA-admin caller (line 181) before any signature or freshness check, in every profile | yes |
| E02-signed-list-rollback-paper-strict / -paper-minimal | ACCEPT / SPEC_GAP | `_checkFreshness` returns at once outside REPAIRED_E (line 188): the latest appended list is current, so the replayed CRL v1 starts a new generation without the revocation | yes |
| E02-signed-list-rollback-repaired-e | REJECT / REPAIR_SUPPORTED / STALE_ANCHOR | version ≤ current gives STALE_ANCHOR (line 190); v2 is retained and Alice stays REVOKED | yes |

- **Wrong issuer is a baseline caller restriction** (D-record N-1), not a repair.
- Per A1-0061, the bootstrap's wrong-admin control (also 16) does **not** credit this row. Only the
  row's own SL5 step does.
- The owner's own check (`ledger/tools/check_sign_list.py`, step 4) expects exactly the rollback
  results above.
- **No disagreement between the catalog and the ledger was found.**

## Recipe (`integration-plan.json` sha256 9e14a148..)

Each of the 6 rows runs on a fresh chain pair: PBC port 18545, DBC port 18546, chain IDs
18545/28545.

- **D1** runs the controls: wrong-admin 16; Alice allow with release and one outcome; Bob deny 9.
- **D2** is a fresh second deployment with its own bootstrap, production adapter and 0700 state
  (`kind=trust`).

**Wrong issuer (WRONG_ISSUER_UPDATE):**

1. The owner producer signs a fresh next-version H2 CRL, with no revocations, using the H2 root.
2. An `eth_call` from the **H2** CA-admin (never mined) must return the next generation. This shows
   the list itself is acceptable.
3. The **H1** CA-admin submits the same list. Expected: mined `Rejected(16)`; anchors, authEpoch,
   revocations, credentials and both histories unchanged.

**Signed-list rollback** (INSTALL_NEW_LIST > REPLAY_OLD_LIST > REQUEST_ACCESS):

1. The producer signs H1 CRL v2 revoking Alice's certificate serial 101. The H1 CA-admin installs it,
   and Alice becomes REVOKED(19).
2. The H1 CA-admin resubmits the **bootstrap's own H1 CRL v1**, byte-for-byte. It is still within its
   validity, so only version order can reject it.
3. Alice requests access with the **current authEpoch**, read just before the request (A1-0064).
   - **Paper:** the replay is accepted. Alice is forwarded with `anchorVersion` 1 (ACCEPT, SPEC_GAP).
   - **Repaired-e:** the replay gives `Rejected(5)` with nothing changed. Alice gets `AccessDenied`
     with REVOKED(19) (REJECT, REPAIR_SUPPORTED).

## Owner signed-list producer (A1-0034; confirmed for SL5 in A1-0061 D-6)

| Condition | How the runner meets it |
|---|---|
| exact bytes | `ledger/tools/sign_list.sh` 806e9a98.. and `ledger/script/SignList.s.sol` 7aa3b1dd.., both equal to the 933d2a7 inventory entries; re-hashed before every call |
| exact command | argv only from the per-variant plan template (`e1.sign_list_argv`, tested), with no `--version`: `bash ledger/tools/sign_list.sh <pbc-rpc> <D> <out> crl H1 --revoke 101` (rollback) or `... crl H2` (wrong issuer). cwd is the ledger snapshot root |
| same deployment file | `<D>` is the stress adapter's own `--deployment` path, re-checked as byte-identical before each call |
| non-zero exit | a failed trial: no retry, no submission. Only `sign-list-refusal.json` (exit code, output sha256, first line) is written. The raw command log stays in the private run output |
| check before use | schema `hmbc-ledger-signed-list/v0`, `testOnly` true; binding to this chain, TMSC, RSC, deployment sha256 and profile; the planned authority and revocations; the next on-chain version; the root signature recovered under the evaluator's own EIP-712 encoder (HMBCTrust, PBC TMSC) |
| never publish | the producer writes no key. The never-publish scan still runs |

## Worker-DB precondition, re-checked for every step

**Static check:** the only adapter operation in SL5 is `prepare_request`, which is pure
(adapter.py:79-104 at 0716a8e). The trust updates are CA-admin chain transactions. The producer is a
ledger owner command with no adapter state. **SL5 performs no worker operation.**

**Dynamic check:** the D49 probe runs at baseline and after every catalog step:

- wrong issuer: `WRONG_ISSUER_UPDATE`;
- rollback: `INSTALL_NEW_LIST`, `REPLAY_OLD_LIST`, `REQUEST_ACCESS`.

Each observation must be the identical verified never-instantiated record. Any instantiation fails
the row.

## Verification (`manifest.json`)

**RED first:** all SL5 tests were written before any SL5 code: **124 failed**
(`red-before-implementation.txt`): 84 oracle-module-missing, 18 collector-module-missing and 22
`create_plan(trust_stress)` errors.

**Two test-double corrections after RED** (no test was weakened):

- The CredentialRecord field is `anchorVersion`, the frozen schema field, not `crlVersion`.
- The worker-appears control now returns a valid idle export, so it fails at the intended
  never-instantiated check.

**GREEN:**

- oracle 84 passed and collector 18 passed;
- every oracle mutation fails at its intended check, after one reorder;
- 9/9 collector negative controls and 3 unsupported variants fail for the intended reason
  (`control-reasons.txt`):

  | Control | Fails with |
  |---|---|
  | producer exits 1 (×2) | failed trial |
  | wrong signer (×2) | signature mismatch |
  | paper version check, repaired without version monotonicity, unchecked caller (×2) | native status differs from the expected control |
  | worker instantiated | "never-instantiated worker after REQUEST_ACCESS" |

- plan tests: 22 passed;
- full suite `.venv/bin/python -m pytest -q -rs`: exit 0, **1350 passed, 0 failed, 0 skipped**,
  385 s. The bracket of 3043 files is stable.

**`agent3Sources` changed since SL4 (98 files):**

- new: `evaluation/trust_stress.py` and `evaluation/oracles/trust.py`;
- changed: `evaluation/e1.py` (`TRUST_VARIANTS`, `SIGN_LIST_TEMPLATES`, `sign_list_argv`, the
  `trust_stress` D2 branch with `stress_sign_list`) and `evaluation/e2.py` (the trust plan,
  `TRUST_EXPECTED`).

## Limits

- **Not yet run live:** the producer on Anvil, the D2 trust path, and the PSC denial path. All are
  unit-tested only, against a TEST-ONLY double that follows the pinned TMSC/PSC order.
- **CRL only.** The catalog allows CRL or TempACL; TempACL rollback is not exercised. This is an
  explicit choice.
- **MUT_NO_VERSION_MONOTONE counterparts** are P3 mutant work.
- Symbolic adapter; safe-ledger, trusted-worker and one-trusted-witness assumptions.
- **Do not touch these files before the run.** All 98 `agent3Sources` are frozen, including every
  `evaluation/**/*.py`. Store helper scripts as `.py.txt`.
