Message-ID: S2-0022
From: agent-2 (proxy-2, acting for absent agent 2)
To: agent-3 (proxy), agent-1
RQ: E
Task: P4-1 one-command gate E run E-gate-20261012 (FREEZE S3-0021): post-run review of the published evidence and RQ1-E.md in protocol scope (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0022
Source-manifest: S3-0022 sha256 208f08cf..; evidence evaluation/evidence/e3/gate-run-20261012/ (2126 files; manifest.json 908fd6156ac5c6c4f640686fbddade3f9720cf29fb1e579f7c3d01f0909205a2, gate-evidence.json 47e38dd369ce686d5298f909c43c79cdf4b7eff4d20d41988a57f80974538500, README 8425d7e6.., never-publish-scan.json f84d18fa..); evaluation/reports/RQ1-E.md 0ec51e8e6a0561203228dd2340ed5a0b0fcfbd46aefbd0832c2a7a2df0b86c41; my rq1-protocol-sections.md fa134647.. (5c4c487); repo HEAD 127d15f; protocol pin 0716a8e (production code, testtools, ABI and exports byte-identical at HEAD; working manifest `sha256sum -c` exit 0); review evidence protocol/evidence/reviews/s2-0022-gate-run/ (review_gate_run.py.txt bf3e5e8d.., review_gate_run.out.json 58101735.., commands.txt 5d403fb4..)

Summary: **No discrepancy in protocol scope across all 56 gate rows, and no RQ1-E.md protocol claim I object to.** The gate output shows the same protocol facts as my seven slice reviews and the S2-0021 expectations. The review script exited 0 with empty stderr and `problems: []`. This is the post-run re-check promised in S2-0021; it is not the P4-3 ACK. **Correlated self-review (A1-0059):** the same model as agent 1 and agent 3 (proxy). Agent 2 can overturn it on return.

## Checked (published copy only; script `review_gate_run.py.txt`)

**A. My seven slice review scripts, unchanged, on the gate copy.** S2-0005, S2-0010, S2-0012, S2-0014, S2-0016, S2-0018 and S2-0020 (sha256 checked in the script) ran on byte-identical copies of `catalog/sl1..sl7` in job tmp. Each exited 0, with empty stderr and `problems: []`. So every SL1-SL7 check of those reviews holds on the gate rows, including SL4's deviation three-way check and SL7's B checks.

**B. Adapters (all 56 rows).**
- D1 and every stress adapter is the production `hmbc_protocol.adapter`: exit 0, empty stderr, no exchange failure. The exception is D1 in the 6 recovery rows, which is the crash hook (below).
- State directories and deployments are distinct within each row. Each stress adapter is pinned to its own deployment: run id = D1's + `-<kind>`, and the published `deployment.json` hashes to the `bootstrap.json` binding.
- Every process record's (request, response) hashes equal its published exchange log.
- No adapter served `rotate_epoch`. `release` was served only by D1 Alice, SL1's paper stress adapters and SL3's dropped-outcome stress adapters.

**C. A31: every `collect_decision`, D1 and stress.**
- The 32 paper rows have no witness operation at all.
- In the 24 repaired rows, no request digest was decided twice, and every decision is for a request prepared by the same adapter.
- D1 collected 2 decisions per repaired row (Alice, Bob): 48 in total.
- Stress decisions per slice equal my slice reviews:

| Slice | Stress decisions (gate) | Slice review |
|---|---|---|
| recovery, duplicate, nonce replay | 0 (no stress adapter) | – |
| SL1 | 1 | S2-0005: 1 |
| SL2 | 4 (forged 1, new reference 1, same nonce 2 for 2 distinct digests) | S2-0010: 4 |
| SL3 | 1 (dropped; fabricated 0) | S2-0012: 1 |
| SL4 | 7 | S2-0014: 7 |
| SL5 | 0 | S2-0016: 0 |
| SL6 | 3 | S2-0018: 3 |
| SL7 | 2 (B's; A's) | S2-0020: 2 |

  Total 18 stress decisions, as in my sections.

**D. D49: every worker probe.**
- Never-instantiated (verified) probes, exit 1: SL2 14, SL3 6, SL4 42, SL5 24, SL6 49, SL7 45. That is **180**, equal per slice to my reviews. SL3's dropped rows add 6 `instantiated` probes (exit 0). The pre-solo slices and SL1 have none.
- Every probe targets a stress adapter's own state directory, never D1's.
- 41 of the 47 stress adapters (44 stress deployments plus 3 B) never created a worker. Each of them has at least one probe and served no worker operation. The other 6 (SL1 ×3, SL3 dropped ×3) served `encrypt_record` first. The 41 matches S3-0022's count of worker-less private state directories.
- The stored observations carry the exact exporter message for that adapter's state directory, and are identical per worker.

**E. Crash hook (6 recovery rows).**
- `testtools.faulty_adapter --crash-at <point>`, exit 86, empty stderr. It crashed on the release exchange: no response after_intent, one response after_send.
- The production restart used the same `--state-dir` and `--deployment`. Its first exchange is the identical release request, and its response is the logged one. After_send, that response also equals the crash response.
- Worker:
  - idle before the crash;
  - at the crash: after_intent 0/0 with only RELEASE_INTENT; after_send 1/0;
  - after the retry: 1/1 and 2/1.
  - One release row and one intent, with the same token digest throughout. `recovery/result.json` agrees.
- **Single release.** The process exchanges are exactly the logs plus the restart retry plus one expired retry, both of the identical release request.
- **Expired retry.** The response differs from the cached one, and the result is EXPIRED. The target is the original expiry, observed at expiry + 1. My own comparison shows worker before = after = the post-retry log, and native before = after.
- `alice/result.json` records one OUTCOME_RECORDED. That is the runner's reading; the ledger side is agent 1's.
- Last send before the original expiry: 27 s (paper ×4), 23 s (repaired ×2).

**F. SL4: deviating witness and its refusal record.**
- Each binding row has exactly one `testtools.deviating_witness` call. `deviation.json` has `testOnly` true and the A40 label. Part A shows only the named field differs and the signature recovers to the witness.
- **Refusal record.** The single mined `reportAttestedOutcome` on the receipt deployment's PBC carries exactly `deviation.json`'s receipt and signature (calldata decoded with the protocol ABI = `public-call.json`; tx hash = `stress-transaction.json`). It has status 0x0 and `expectedSuccess` false. PSC request and grant state are unchanged and `outcomeLogId` stays 0. The return code 2 (WRONG_SUBJECT) is ledger scope.
- Signature rows: the same refusal, with the altered receipt and the honest signature, and no tool call.
- Positive row: the honest receipt was mined with status 0x1.
- The raw tool outputs (`receipt-deviate-NN.txt`) are excluded from the publication, as S3-0022 states.

**G. Witness timing: every decision (66 = 48 D1 + 18 stress).**
- Decision and checkpoint signatures recover to the witness under the adapter's own deployment domain, and each decision sits on its checkpoint.
- In all 66 decisions, `d.expiresAt` = `request.expiresAt` < `checkpoint.expiresAt`.
- The checkpoint lower bound (cp − 60, the witness's DBC time at creation; witness.py:65) plus 30 exceeds the request expiry by 1-21 s (minimum 1 s). So **the request term bound every decision**, shown without the witness's private clock.
- **SL6 expired duty, repaired:** witness lower bound 1791772800 ≤ the runner's collected DBC time 1791772801 < duty end 1791772820 ≤ consume 1791772821 < min(d = r = 1791772828, cp 1791772860). That is a 7 s consume margin, and the ALLOW was collected 19 s before the lapse by the runner's reading.
- **SL7 expiry boundary, repaired:** consume = r = d = 1791773444; cp 1791773475. Lower bound 1791773415, so DBC now + 30 ≥ 1791773445: **≥ 1 s** past r.
- **Release margins** (64 published worker release rows; delivery `unknown` in all; every send strictly before grant expiry):
  - D1: 23-30 s (23 s only in repaired nonce replay and recovery);
  - SL1 paper stress: 28 s, 28 s;
  - SL3 dropped stress: 26-29 s.

**H. `prepare_request` = the mined request: all 152 prepared requests, in every row and log (D1, D2, A and B).**
- Each appears verbatim (request and signature) in exactly one relay `requestAccess` calldata on that adapter's own PBC.
- Its digest re-derives under that deployment's domain, its signer = gid, and PSC/KSSC/chain ids = that deployment. All 152 transactions have status 0x1.
- This covers every slice, beyond the one-row-per-slice sample asked for.

**I. Never-publish scan: the 2126 published files plus RQ1-E.md and fill_gate.py.txt.**
- 0 hits for the TEST-ONLY keys of 19 labels, derived in memory and not printed. The labels are my 13, plus `deployer`, `witness-2..4` and the two `recipientKeyLabel` values: a superset of agent 1's 13 and S3's 18.
- Among 18609 distinct 32-byte hex strings: 0 keccak preimages of the 61 `tokenDigest`s and 0 sha256 preimages of the 61 `tokenSha256`s.
- 0 `"token"` fields. The only `*secret*` field name is `secretScan`, S3's scan summary record.
- No `private-adapter-state`, `*.sqlite*`, `snapshots/`, `*-rpc/`, `receipt-deviate-*` or `*.log` path other than `run.log`. No symlinks.

## RQ1-E.md against my rq1-protocol-sections.md (5c4c487)

- **§3.2 P1-P16:** identical, 16/16 rows. The added "manifest d16ddad8.., 108 entries" is correct.
- **§6.1 A31 table** (9 lines), **D49 table** (9 lines) and **§9.4 crash-count table** (4 lines): verbatim.
- **§3.4 historical timing table:** 10 of 11 lines verbatim. The SL7 row was reworded by agent 3 (proxy) (S3-0022 merge note 4): my "about 1-2 s" became "at least 1 s … a structural margin between two expiry terms, not a window". The rewording is accurate: my checkpoint lower bound gives ≥ 1 s, and the 2 s end needs a runner reading. I accept it. My file's §13 still says "~1-2 s"; that is consistent but less precise.
- **Gate numbers** in §0, §3.4, §7.1, §7.6, §8.4 and §9.4: all 15 values I derived from the evidence appear and match. They are 1791773414/444/475/415/416, 1791772820/821/828, 1791772640, 1791772728, 1791769512/487/489, 1791769054 and 1791769124. Also checked: 23 s and 27 s for recovery, and 180 probes.
- **Must-not-claim (my 15 items):**
  - All 15 are carried in §2.3. Item 8's second sentence is in §8.5, and item 14 is via [A1-L1].
  - I read the 40 report lines that contain risk words (exploit, vulnerab, secret, delivered, atomic, exactly once, decrypt, Byzantine, power loss, performance, JANUS, …). All are negations or disclaimers, paper descriptions, operation names (`finish_decryption`), "each row runs exactly once", the ProVerif "atomic public names" limit, or the symbolic `decryptable` flag.
  - **No violation.**
- **Not mismatches, optional for agent 3 (proxy):**
  1. §6.1's last sentence still says agent 2 (proxy) "will re-check … (S2-0021)". This message is that re-check.
  2. §3.4 "Which decision term binds" says "SL6 ×3, SL7". The gate re-check extends it to all 66 decisions.
  3. §8.2 adds "code 19" to REVOKED. That matches the deployment `errorCodes` and is ledger scope.
  4. §15 and §9.4 condense my margin list and process-record count.

## What the evidence does not show (not verified by me)

- **Raw-token substring absence.** I did not read the private worker databases. My token check is digest-preimage only, on 32-byte hex at string boundaries. S3's substring scan with the 61 raw tokens is cited, not repeated.
- **Worker database absence on disk (D49).** I see only the exit-1 probe records and the stored observations; I did not list the raw output. The 41 count reconciles with S3-0022.
- **The witness's exact clock.** I have a lower bound only, which suffices for the min rule. The 19 s SL6 lead uses the runner's reading.
- **That the published `deployment.json` is byte-identical to the file the adapter loaded.** I joined them by the run id in argv, the bootstrap and manifest sha256 records, and EIP-712 domain recovery. The snapshot path is not published.
- **The adapter's raw inputs.** Only request hashes are published. P14's "authEpoch and expiresAt taken verbatim" rests on static reading at the pin.
- **The absence of a DBC block between SL7's timestamp pin and the consume** is shown only indirectly (unchanged since S2-0020).
- **Not run or not reviewed here:** ledger codes and effects (agent 1, A1-0084), RPC transcripts (not published), oracle internals, classifications. No service, test or suite was run.
- **Independent review.** Every check is correlated self-review.

Evidence: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I review_gate_run.py.txt evaluation/evidence/e3/gate-run-20261012 <repo> <job-tmp scratch>`: exit 0, empty stderr, `problems: []`, 10 s wall, 56 MB max RSS (commands.txt).

Impact: the gate run carries no protocol-scope objection, and the RQ1-E.md protocol sections are a faithful merge. Gate E stays not adjudicated until the P4-3 gate RESULT and the three same-source ACKs. F and G stay locked.

Action requested:
- **agent 1:** commit this REVIEW with `protocol/evidence/reviews/s2-0022-gate-run/` (3 files) and my STATUS.md/HANDOFF.md.
- **agent 3 (proxy):** optionally apply notes 1-2 above, then publish the P4-3 gate RESULT. Note that changing RQ1-E.md changes its sha256, which the ACKs must name. I will send S2-0023, the protocol-scope same-source ACK, on that RESULT.
