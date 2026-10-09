Message-ID: A1-0064
From: agent-1
To: agent-2 (proxy), agent-3 (proxy)
Cc: human
RQ: E
Task: acceptance of S2-0007 (deviating_witness for SL4, SL2-SL7 protocol notes, A31 disclosure); paper figure check for the durability placeholder
Type: DECISION
Interface-version: v1
Responds-to: S2-0007
Source-manifest: references/HMBC2020.pdf pages 11-13 (Fig. 5, 6, 8); references/HMBC2020.txt; S2-0007 sha256 ff23ef7c..; rq1-protocol-sections.md sha256 90a1cc3f..

Summary: **S2-0007 is accepted as written.** It has three parts:

- the SL4 conditions for `testtools.deviating_witness`;
- the per-slice plan notes;
- the A31 disclosure.

Agent 3 (proxy) folds the conditions and notes into the SL2-SL7 plans and oracles. I also checked the
paper figures for the durability placeholder in `rq1-protocol-sections.md`: the "silent" reading holds.

## Rulings

1. **D-6, protocol side, closed.** `deviating_witness` at pin 0716a8e (sha256 0511ba57..) may be an
   SL4 runner input under exactly the S2-0007 conditions:
   - the exact command and hash appear in the plan;
   - the runner checks each output three ways: only the named field differs, the signature
     recovers to the witness under the evaluator's own EIP-712 receipt domain, and `testOnly` is
     true;
   - any non-zero exit is a failed trial;
   - the never-publish list applies.

   The ledger side was confirmed in A1-0061 (`sign_list.sh`).
2. **A31 is an assumption, not enforced in code.** The RQ1 report must say that "at most one
   `collect_decision` per checkpoint" is **runner discipline**, not protocol enforcement.
   - Classification: ambiguity / a stated trust assumption. It is not a vulnerability.
   - Ledger safety does not depend on it:
     - a repeated certificate for the same request has the same grantId, which gives `REPLAY` at
       `KSSC.sol:180`;
     - a different request under the same (gid, nonce) gives `REPLAY` at the nonce guard
       (`KSSC.sol:181-183`);
     - an older decision is invalidated by a newer accepted checkpoint (DV step 10, `STALE_STATE`).
   - The SL6 oracle checks exactly one `collect_decision` per request in `exchanges.json`, as
     proposed.
3. **Slice notes adopted for agent 3 (proxy):**
   - SL2 forged tuple: recover the honest witness signature under the runner's own digest before
     relying on BAD_SIGNATURE.
   - SL2 same-nonce: checkpoint after both forwards, both decisions before any consume.
   - SL3 dropped outcome: includes RELEASE (cf. my R2 correction, A1-0060).
   - SL5: current authEpoch.
   - SL6 expired-duty: collect while the duty is still valid.
   - SL7: record which expiry binds.

## Paper figure check (resolves the placeholder in rq1-protocol-sections.md §7.2)

Agent 1 read `references/HMBC2020.pdf` pages 11-13 as rendered images:

| Figure | Content |
|---|---|
| Fig. 5 (p. 11) | two-step decryption: the KSSC partially decrypts with K_onDuty, the user finishes with K_Doctor |
| Fig. 6 (p. 12) | access-control sequence (1)-(10): ACSC caching/policy enforcement → KSSC request/encrypted data → partially decrypted data to the user; "store trans_details on the BC" at the PSC and ACSC |
| Fig. 8 (p. 13) | "Caching transaction details": the request details go to a cache database in Docker 1, the response details are added, then "(8) finalized transaction" to the PBC |

**No figure specifies crash, retry, restart, durability or recovery semantics for key release.**

- The only failure language (§IV-B, p. 13) is that the pending log session, "if not treated
  properly during the implementation", "may delay block publications and most certainly will cause
  the system to fail".
- That concerns batching log sessions into the PBC, not KSSC or worker crash recovery.
- A text search of `references/HMBC2020.txt` for crash/durab/retry/recover/persist/restart/fail finds
  only lines 291 (revocation) and 1033 (this same passage).

The SPEC_GAP reading of D47 therefore stands: the paper is silent, and the cache database is a
logging buffer. The report should cite Fig. 8 accurately as a "pending log session cache", not as
release-state durability.

Impact: no pin change. The SL4 protocol confirmation is now in hand.
Action requested:
- agent-3 (proxy): adopt the slice notes and A31 wording; cite this message when merging the
  protocol sections.
- agent-2 (proxy): replace the placeholder with a citation of A1-0064 the next time you edit the
  file.
