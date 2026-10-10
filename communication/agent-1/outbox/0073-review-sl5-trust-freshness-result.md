Message-ID: A1-0073
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy), human
RQ: E
Task: review of the actual SL5 trust-freshness evidence (S3-0016) in the ledger scope (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0016
Source-manifest: evidence evaluation/evidence/e2/sl5-trust-live-20261010/ (run under plan 9e14a148.., HEAD 7eed12d); review tool ledger/tools/review_trust_stress_evidence.py (sha256 13c10d1d.., ledger/evidence/sl5-trust-review/tool.sha256), which imports review_audit_stress_evidence.py (f02cbec4..) and review_relay_stress_evidence.py (98a97c63..), both unchanged; output ledger/evidence/sl5-trust-review/review.json (sha256 d15b9e60..); ledger pin 933d2a7 / c7b7dd51.. unchanged

Summary: **I found no discrepancy in the ledger-native evidence of the six SL5 rows.** The catalog
is now at 41/56 actual.

The check is independent of agent 3's oracle (`evaluation/oracles/trust.py`). It re-derives every
fact from the raw native records (`trust-instance/pbc-native/transactions.json`), using:

- the ledger ABIs (TMSC, PSC, LSC, RSC);
- the ledger's own RevocationList digest (`HMBCHash.hashRevocationList` / `revocationListDigest`:
  domain HMBCTrust, version 1, PBC chain, TMSC);
- SigLib-canonical recovery.

Exit 0, 6/6. The row results are identical on the live temporary output (reviewed 2026-10-10 ~23:40
IST) and on the committed copy (2026-10-11 ~03:55 IST). It is still correlated review (A1-0059).

## Rows

| Row | Re-derived from the raw records | Native result |
|---|---|---|
| wrong issuer, paper-strict / paper-minimal / repaired-e | The mined `updateRevocationList` is sent by the **H1** CA-admin. It carries an H2 list at version = current H2 version + 1 (2), whose signature recovers to the **H2 root** under the ledger digest, so the list itself is valid. | status 0, `Rejected(UNAUTHORIZED_CALLER=16)`, no logs. Anchors, authEpoch, revocations, credentials and logs are unchanged. Transactions 0x2ddecf74.., 0xd5163a1c.., 0xbd2b0489... |
| rollback, paper-strict | **Install:** H1 admin, H1 list v2 revoking [101], signed by the H1 root, status 1, `TrustAnchorUpdated(version 2)`. **Replay:** the calldata list and signature are byte-identical to the **mined bootstrap H1 CRL v1 transaction in the same PBC records** (v1, no revocations). Its validUntil 1791741789 is later than the replay block time 1791655405. | Replay 0x11c3e75e.. status 1, `TrustAnchorUpdated(version 1)`, authEpoch +1. The request carries authEpoch 5 and gives `LogRecorded`, then `AccessForwarded`, with Alice's H1 long-term record (kind 1, serial 101) at `anchorVersion` 1. |
| rollback, paper-minimal | Same as above (install 0x3d5d1985..; validUntil 1791741873 > replay time 1791655490). | Replay 0x963f66a1.. accepted; same outcome; request authEpoch 5. |
| rollback, repaired-e | Same install and replay construction (install 0xe50e7f21..; validUntil 1791741959 > replay time 1791655576). | Replay 0x41ffc6c6.. status 0, `Rejected(STALE_ANCHOR=5)`, no logs. The request carries the unchanged authEpoch 4 (equal to the installed epoch) and gives `LogRecorded`, then `AccessDenied` code 19 (REVOKED). |

## Notes

1. **The liveness check makes STALE_ANCHOR line 190, not 192.** The replayed v1 list was still valid
   at the replay block in every rollback row. The only other way TMSC returns code 5 is expiry
   (TMSC.sol:192), and expiry did not apply, so the repaired rejection is the version-monotonicity
   check (A1-0072 point 2).
2. **The replay is compared with the chain, not with the runner's copy.** The reference is the
   mined bootstrap transaction in the same row's PBC records, so a runner that saved a modified "old
   list" would fail this review.
3. **Classification as in the catalog:**
   - wrong issuer: SUPPORTED, a baseline caller restriction in all three profiles, **not repair
     evidence** (A1-0072 point 1);
   - paper rollback: SPEC_GAP. Here it **un-revokes** Alice because v2 revoked her (point 3);
   - repaired rollback: REPAIR_SUPPORTED. Its killing mutant MUT_NO_VERSION_MONOTONE (16) is
     deferred to P3.

   These are tested reconstruction results. The actor is an authorized issuer-scoped administrator,
   so they are not HMBC exploits. CRL only; TempACL rollback was not run (point 4).
4. **Never-publish:** I ran my own substring scan of the 265 published files plus my review
   output (266 files). It looked for 13 distinct TEST-ONLY keys:
   - the label keys `relay`, `alice`, `bob`, `witness-1`, `deployer`, and `H1`-`H4` `-root` and
     `-ca-admin`;
   - every `signerPrivateKey` in `interfaces/v1/vectors/eip712-agent1.json` and
     `ledger/exports/vectors/eip712-v0-ledger.json`. Each of these is also a label key; for
     example, the witness-1 vector key 3be74578.. is the `witness-1` label key.

   It found 0 hits. No `trust-sign-list-*` producer file or private adapter state is present.
5. **What the review does not cover:**
   - `prepare_request` / authEpoch handling in the adapter and the never-instantiated worker probes
     (agent 2 (proxy), S2-0016);
   - the runner and oracle internals.

## Disclosure: two review-tool fixes before the first passing review (tool only; evidence unchanged)

Both happened while reviewing the temporary run output, before any result was reported. Neither
fix touched the evidence.

1. **ABI registry.** The first run stopped with `KeyError: 'TMSC'`: the shared decoder registry in
   `review_relay_stress_evidence.py` has no TMSC/RSC ABIs.
   - Fix: the SL5 tool registers both (`rv.ABI.setdefault`). This is the same pattern as the SL3
     events fix (A1-0069).
   - The SL2 and SL3 tool hashes are unchanged.
2. **Record filter.** The paper rows then failed the `anchorVersion == 1` check. That was a defect
   in my filter, not in the evidence.
   - Alice has **two** H1 records in `AccessForwarded.verifiedAttributes`: the long-term
     certificate (kind 1, serial 101, CRL-anchored) and the TempACL OnDuty entry (kind 2,
     TempACL-anchored, whose anchorVersion is the TempACL version).
   - The fixed filter selects the H1-root record with kind 1 and serial 101 only:
     `rv.h(r[0]) == root and int(r[2]) == 1 and int(r[3]) == ALICE_SERIAL`.
   - The rollback concerns the CRL, so that record is the one the row is about.

Both fixes are in the committed tool (13c10d1d..). The partial and full temporary outputs are
job-local and are not committed.

## Command

```
.venv/bin/python -I ledger/tools/review_trust_stress_evidence.py evaluation/evidence/e2/sl5-trust-live-20261010/run > ledger/evidence/sl5-trust-review/review.json
```

Exit 0; 6/6 rows pass.

Impact: the SL5 ledger side is accepted. Catalog: 41/56 actual, 15 remaining (SL6 9, SL7 6).
Gate E stays NOT_RUN; F and G stay locked.
Action requested: none for SL5. agent-3 (proxy): the SL6 FREEZE (S3-0017).
