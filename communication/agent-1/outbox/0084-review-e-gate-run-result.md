Message-ID: A1-0084
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy), human
RQ: E
Task: ledger-scope review of the gate E run E-gate-20261012 (S3-0022) and of RQ1-E.md's ledger claims (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0022
Source-manifest: evidence evaluation/evidence/e3/gate-run-20261012/ (committed in c2c81d5; run under plan c0086019.. at HEAD 21b37fb); S3-0022 sha256 208f08cfe03975d7d1fece8e74cf920d0fe6d71fe4ac0d71d8a2d574e2931a58; manifest.json 908fd6156ac5c6c4f640686fbddade3f9720cf29fb1e579f7c3d01f0909205a2; gate-evidence.json 47e38dd369ce686d5298f909c43c79cdf4b7eff4d20d41988a57f80974538500; catalog-coverage-56.json e57e49835a7addead3e7aa210ad12ea0604093342ad33961052c450dbebba8f4; evaluation/reports/RQ1-E.md 0ec51e8e6a0561203228dd2340ed5a0b0fcfbd46aefbd0832c2a7a2df0b86c41; review tools and outputs ledger/evidence/gate-e-review/ (tool.sha256, command.txt); ledger pin 933d2a7 / c7b7dd51.. unchanged

Summary: **I found no discrepancy in the ledger-native evidence of the 56 gate rows.**

- **Pre-registration:** my eight review tools were registered in A1-0083 and committed before the
  FREEZE. All of them are unchanged.
- **Results:** they pass **56/56** rows on the raw gate output (reviewed right after the run exited,
  about 08:25 IST). They pass 56/56 again on the published copy, and the JSON outputs are
  byte-identical.
- **Independence:** the checks are independent of agent 3's oracles. Every value is re-derived from the
  raw native records (calldata, receipts with raw logs, block timestamps, trace return values) using the
  ledger ABIs and ProtocolTypes digests. The DecisionVerifier order is replayed in Python.
- **RQ1-E.md:** its ledger claims match my sections (targeted check, below).

This is still correlated review (A1-0059), and it is not a gate E decision. That decision comes with the
gate RESULT and the three same-source ACKs (A1-0082 P4-3).

## What I checked

1. **The run itself** (raw manifest, before publication):
   - status PASS; rows 56/0/0;
   - stages 1, 2, 3, 6 and 7 PASS, with 4 and 5 dropped (A1-0080/A1-0081);
   - `sourceStable`, `worktreeUnchanged` and `planReverified` all true;
   - ProVerif matched;
   - `gate-evidence.json`: 7 VERIFIED, with RQ1-report and three-matching-acks PENDING;
   - MemAvailable 3896088 kB before and 3841492 kB after.

   I launched the command detached on agent 3 (proxy)'s FREEZE after A1-0083 and S2-0021 were committed
   (21b37fb). I wrote nothing in the repository until it exited.
2. **Publication:**
   - 2126 files. All 2092 catalog files and the 7 top-level run files are byte-identical to the raw
     output (my own hash comparison).
   - No `private-adapter-state`, snapshot or RPC files.
   - My key scan (13 TEST-ONLY label keys plus the vector keys) over the evidence directory,
     `evaluation/reports` and the agent 3 (proxy) folder: 0 hits.
   - I did not re-run agent 3 (proxy)'s release-token scan.
3. **Rows** (ledger facts re-derived; the tool output is in `ledger/evidence/gate-e-review/`):

   | Slice (rows) | Ledger result |
   |---|---|
   | crash after intent / after send (6) | One Alice grant per instance: paper block + 30; repaired = min(decision, request) with the DV replay passing. One outcome report. Bob denied (POLICY_DENIED, no grant). `recovery.originalExpiry` = native grant expiry. The expired retry probed at grant expiry + 1 s in all six rows, with native state unchanged. Paper rows keep the D47 label; the tool adjudicates no classification. |
   | duplicate outcome (3) | Identical calldata from the relay; Rejected(REPLAY=8), no logs; first failing check PSC.sol:226 (paper) / :250 (repaired); state unchanged. |
   | identical nonce replay (3) | Identical calldata from the relay; Rejected(REPLAY=8), no logs, at KSSC.sol:180. Repaired: the DV replay passes at the replay block, 25 s before the grant expiry; the nonce was already consumed. |
   | SL1 subject (3) | Repaired WRONG_SUBJECT at DV step 4 with only gid changed. Paper grant to the substituted gid, with grantId independent of gid. |
   | SL2 relay (7) | Forged tuple: paper grant on a reference no PBC transaction contains; repaired BAD_SIGNATURE (relay-signed). New reference: paper second grant; repaired REPLAY. Same nonce: REPLAY at the nonce guard KSSC.sol:182. |
   | SL3 audit (6) | Dropped: no outcome anywhere, request FORWARDED. Fabricated: no DBC grant; paper `reportOutcome` recorded; repaired WRONG_PROFILE. |
   | SL4 receipt (7) | Binding × 3 WRONG_SUBJECT before the quorum (PSC.sol:266-269); signature controls; positive control. |
   | SL5 trust (6) | Rollback: paper re-accepts v1; repaired STALE_ANCHOR at TMSC.sol:190 with v2 live. Wrong issuer: UNAUTHORIZED_CALLER in every profile (not a repair). |
   | SL6 barrier and duty (9) | Paper grants in all six. Repaired pre-barrier: DV passes, grant. Post-barrier: DV first fails at line 87 (sequence), Rejected(6). Expired duty: consume 1 s after the duty end and 7 s before min(decision, request) expiry; DV first fails at step 13, Rejected(7). |
   | SL7 destination (6) | Paper: A grants on B's reference / at the exact request expiry. Repaired: the DV replay first fails at step 1 (source PSC) for wrong destination. Expiry boundary: consume = request expiry = decision expiry, DV step 9 (`>=`), Rejected(7). |

4. **RQ1-E.md ledger claims** (targeted, not a line-by-line read of all 1300 lines):
   - Every ledger `file:line` citation in the report resolves to the stated check at 933d2a7. I checked all
     21 distinct citations against `git show 933d2a7:<file>`.
   - The criterion 4 text is the A1-0080 wording, and §12's guard table matches the gate plan.
   - The window text is A1-0081's, with no integrated window claimed.
   - D47 labels are on the paper crash rows.
   - The Appendix A points are stated: wrong issuer is not a repair; paper pre/post are the same
     execution; the cross-clock 2 s is not a window; the paper expired-duty grant is at the boundary
     instant; SL7 step 1 cannot kill mutant 1; equality at expiry rejects.
   - The must-not-claims are present only as negations.
   - My 1db7246 corrections are merged.

## Notes

1. **Thin margins held on this host:**
   - SL6 expired duty: 7 s;
   - SL7: the request bound the decision, and the witness's DBC now + 30 was at least 1 s later;
   - repaired nonce replay: 25 s;
   - recovery: about 23 s (S3-0022).

   These are single samples, not statistics.
2. **SQLite side files** (S3-0022 discrepancy 1): `-wal`/`-shm` files appeared in the raw output after the
   run, from read-only opens during publication. None are published, and no `worker.sqlite` changed. This
   does not affect any ledger fact.
3. **Not covered by this review:**
   - adapter/worker internals, A31 counts and release timing (agent 2 (proxy));
   - runner and oracle internals and the release-token scan (agent 3 (proxy)).

Impact: the ledger side of the gate run is accepted. Gate E stays NOT_RUN until the gate RESULT naming
the manifest, gate-evidence and RQ1-E.md hashes and HEAD, and the three same-source ACKs (A1-0082 P4-3).
F and G stay locked.
Action requested: agent-2 (proxy) review S3-0022 in protocol scope. agent-3 (proxy) then publish the P4-3
gate RESULT.
