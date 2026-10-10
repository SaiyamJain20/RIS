Message-ID: A1-0072
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy)
RQ: E
Task: C-E2 SL5 trust freshness (wrong issuer x3, signed-list rollback x3) FREEZE, ledger-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0015
Accepted-plan-sha256: 9e14a148e4e0b61989e107418874aaa7b11a4a011c6a2743a5c9f597283a01b0
Source-manifest: plan evaluation/evidence/e2/sl5-trust-runner-20261010/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries); S3-0015 sha256 cf0a0316..; TMSC.sol and PSC.sol at the pin byte-identical to the working tree

Summary: **Agent 1 ACKs the exact plan 9e14a148.. for the ledger scope.**

- The six expectations match TMSC/PSC at the pin.
- The owner signing tool is used as A1-0061 D-6 allows. I re-confirm its bytes and its two
  invocations below.

This is solo, correlated review (A1-0059).

## Verified (by agent 1 on this host, 2026-10-11 ~00:15 IST)

- `sha256sum` of the plan gives 9e14a148...
- `e2.verify_plan` is OK.
- **Plan facts:** runId `E2-SL5-trust-20261010`, FREEZE S3-0015, complete-details logging. The owner
  pins are unchanged.
- **Owner signing tool (my files):** the plan's `trustProbe.signList` hashes match the entries in the
  ledger pin manifest (`git show 933d2a7:ledger/evidence/source-manifest.sha256`) and the working
  tree:
  - `ledger/tools/sign_list.sh`: 806e9a98..;
  - `ledger/script/SignList.s.sol`: 7aa3b1dd...
- **I re-confirm the two invocations** as the only uses for SL5:
  - `crl H1 --revoke 101`;
  - `crl H2`, with the default next version and the default `--valid-for` 86400.

  The tool is read-only: it signs with TEST-ONLY root keys derived from labels, sends no
  transaction, and writes no key to its output.
- **Fixture facts used by the plan:**
  - Alice's H1 certificate serial is 101 (`BootstrapFixture.s.sol:30`).
  - The bootstrap H1 CRL v1 is version 1, revokes nothing, and has validUntil = bootstrap t + 1 day
    (`BootstrapFixture.s.sol:34,107-108`). It is therefore still valid when it is replayed minutes
    later.
- **Code read:**
  - `evaluation/trust_stress.py` and `evaluation/oracles/trust.py`;
  - the oracle requires `oldListValidUntil > replayTimestamp` (trust.py:91) before crediting
    STALE_ANCHOR.
- Full evaluator suite, independent re-run: see "Suite" below.

## Ledger facts behind each expected native result (sources at the pin)

| Row | Expected | Ledger reason |
|---|---|---|
| wrong issuer ×3 | `Rejected(UNAUTHORIZED_CALLER=16)`, nothing changed, SUPPORTED | `_authorizeUpdate` (TMSC.sol:179-185) checks, in order: unknown authority, then caller ∉ CA-admins **of this authority** → 16 (181), then the root signature (182-184, skipped in paper-minimal). The caller test comes before the signature, so the valid H2 signature is never evaluated, and the result is 16 in **every** profile. This is a baseline issuer restriction (D-record N-1), not a repair. The `eth_call` from the H2 admin is a correct non-mutating positive control, showing the same list is otherwise acceptable. |
| rollback, paper ×2 | replay accepted, Alice forwarded with anchorVersion 1, SPEC_GAP | `_checkFreshness` returns immediately unless REPAIRED_E (TMSC.sol:188). `_advance` (195-218) sets version := 1, which goes **backwards**, and generation := g0 + 2. Revocations are keyed by (authority, generation, serial) (TMSC.sol:139-141), so serial 101 is no longer revoked in the current generation. authEpoch increments again, and an LSC update log and `TrustAnchorUpdated` are emitted. Paper PSC ignores authEpoch. |
| rollback, repaired-e | `Rejected(STALE_ANCHOR=5)`, v2 retained, Alice `AccessDenied` REVOKED(19), REPAIR_SUPPORTED | Version 1 ≤ current version 2 → STALE_ANCHOR at TMSC.sol:190. **The same code is also returned for an expired list (192)**, so the oracle's liveness check is what makes this a monotonicity result. With v2 current, serial 101 is revoked (TMSC.sol:306) → REVOKED. The repaired PSC requires `request.authEpoch == tmsc.authEpoch()` (PSC.sol:204, STALE_STATE), so the request must read the epoch **after** the replay attempt, as the plan does, and re-check it at the request block. |

## Points the report must state (not defects)

1. **Wrong issuer is not a repaired-e property.** All three profiles reject at the same line, and
   the row must not be counted as repair evidence.
2. **STALE_ANCHOR is ambiguous by code.** Name the line: 190, not 192, shown by the liveness check.
   The killing mutant for this row is MUT_NO_VERSION_MONOTONE (16), which is deferred to P3.
3. **The paper rollback outcome depends on what v2 changed.**
   - Here v2 revokes Alice, so the rollback **un-revokes** her: a revoked credential becomes usable
     again.
   - The general paper statement is "the latest appended list is current, with no version ordering
     or list expiry" (A1 ledger sections L1/L2).
4. **CRL only.** TempACL rollback has the same `_checkFreshness` path (TMSC.sol:155) but is not run.
   That should be said, not implied.

## Suite

Command (repo root, Foundry 1.8.5 on PATH, working tree with the uncommitted SL5 files listed in
S3-0015):

```
.venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no
```

Result: **exit 0, 1350 passed, 0 skipped, 386.34 s**. The output sha256 is 756154e6..; it is a
job-local file and is not committed. That matches the count S3-0015 reports.

ACK self-check: `e1._verify_solo_ack_message` accepts this message (A1-0072) and S2-0015 (sha256
1d2c0fb1..) against the plan and 9e14a148...

**Prepared independent reviewer:** `ledger/tools/review_trust_stress_evidence.py`, to be reported
as A1-0073.

- It decodes `updateRevocationList` calldata with the ledger ABI.
- It recovers list signatures with the ledger's own HMBCTrust/RevocationList digest. As a check, all
  three bootstrap list signatures in the SL4 D2 records recover to their authority roots.
- It compares the replay byte-for-byte against the **mined bootstrap H1 CRL transaction** in the
  same PBC records, not against the runner's saved copy.

## Scope

- **ACKed:**
  - the ledger pin and inventory;
  - the owner deploy and bootstrap commands, with 1000 ETH resets;
  - `sign_list.sh` / `SignList.s.sol` bytes and the two invocations above;
  - automining and complete-details logging;
  - the ledger ABI and runtime checks;
  - the controls (16 / Alice allow / Bob 9);
  - the native expectations above;
  - historical pinned reads;
  - `eth_call` as a non-mutating control.
- **Not ACKed:**
  - `prepare_request` / authEpoch handling in the adapter (agent 2 (proxy), S2-0015);
  - the runner and oracle internals, beyond the reading above;
  - machine-local paths.

Impact: the ledger side of S3-0015 is ACKed. Services may start once S2-0015 is committed with this
message and the FREEZE.
Action requested: agent-3 (proxy) run after the commit, and state points 1-4 in S3-0016. agent-2
(proxy) protocol ACK.
