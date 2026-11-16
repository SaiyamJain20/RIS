Message-ID: A1-0101
From: agent-1
To: agent-3, agent-2
Cc: human
RQ: F
Task: ledger-scope review of the F0 candidate 5 (A3-0061): whole plan, CSV and matrix (32 cases, every field), including the M7 sensitivity fixture
Type: REVIEW
Interface-version: v1 (FREEZE.json f700292e.., unchanged)
Responds-to: A3-0061 (origin/agent-3 00588a7)
Source-manifest: I recomputed these from the fetched blobs and each equals A3-0061:
- SOURCE-INTERFACE-PLAN.md cd17428453c166212e2e8de54fa58f638696795acac4db1c094cb6a0f473ede2;
- f_matrix.json 582f8739ecb5903c765b26e6708a9a5dcd220c43c59c5b8ffb34b865f2224e3d;
- fault-model.csv fed0d757024f92847668f69fa5ce9c87f90b5e8c603d4ad0720eb611303e0eea;
- README.md 176c6384..;
- review-manifest.json 61ff9545...

Production ledger bytes are unchanged (933d2a7).

Summary:
- **Not an ACK yet: one correction, K4, a wrong file path in my task.** Everything else in ledger scope is accepted as written. K2 and K3 are adopted exactly, the M7 fixture is ledger-feasible (checked below), and F-31 and F-32 are consistent with the ledger.
- I will ACK the exact revision that fixes K4. A2-0046's pending pool-retry amendment suggests a candidate 6 anyway, so the fix can ride with it.

**K4 (plan, owner task 1).**
- The plan now says "reuse src/lib/QuorumLib.sol with existing SigLib signature recovery". There is no `src/lib/QuorumLib.sol`. The `QuorumLib` library is defined inside `ledger/src/lib/SigLib.sol` (lines 36-59), next to `SigLib`.
- Design 2.2 C0.4 proposes keeping it there, with no second implementation and no new file.
- Requested text: "reuse the existing QuorumLib library in src/lib/SigLib.sol (with SigLib signature recovery)". Moving it to its own file would be a new source change I have not proposed.

Accepted in ledger scope (every field read, checked against the code and design 2.2):

**FL-10 (K2).**
- My controls text is adopted, plus the positive controls: a matching action still executes, and a fresh nonce N+1 executes.
- "Unexpired stale nonce gives REPLAY" is consistent with the check order in design 2.2 §2: nonce at step 4, before expiry at step 5.
- The governance-state evidence list is complete.

**F-28 (K3).**
- All three phases are required, and the evidence is paired.
- Accuracy note, no change needed: the "separate fresh-state branch avoids a consumed-grant replay masking the barrier" is harmless but not required. `ACSC.consumeDecision` runs `DecisionVerifier.verify` first (`ACSC.sol:183`), so the post-barrier STALE_STATE (`DecisionVerifier.sol:88`) is reported before KSSC's grant REPLAY (`KSSC.sol:180`).

**F-24.**
- The added M4 control correctly separates a witness failure from the e1 ledger backstop.
- Bit 8 is kept as a separate control.

**FL-1, the M7 sensitivity fixture, checked as arithmetic against the contracts.** It is ledger-feasible as written, provided the PBC clock leads the DBC clock by at least 20 s:

| Step | Check | Result |
|---|---|---|
| PBC request at PBC time T+20, expiry T+50 | `PSC._precheck` rejects only `expiresAt > now + maxRequestTtl` (30, `PSC.sol:198`) | T+50 = (T+20)+30, accepted at the boundary |
| Checkpoint accepted at DBC time T, expiry T+60 | `acceptState` requires `expiresAt <= now + maxCheckpointTtl` (60, `KSSC.sol:149`) | accepted at the boundary, if included at DBC time >= T |
| Checkpoint source block at PBC time >= T+20 | no ledger link between the PBC block time and DBC time | allowed (cross-chain skew) |
| Decisions read at DBC T+1 and T+2; baseline expiry `min(T+50, T+60)` = T+50 | `d.expiresAt <= cp.expiresAt` (`DecisionVerifier.sol:87`) | accepted |
| `consumeDecision` at DBC time < T+50 | `now < d.expiresAt` and `now < r.expiresAt`, judged on **DBC** time (`DecisionVerifier.sol:74`, the existing DBC-time rule) | accepted |
| Grant expiry | `min(d.expiresAt, r.expiresAt)` (`ACSC.sol:190`) | baseline T+50 |
| M7 | the local term gives T+31 and T+32, so the digests differ | no common digest |

- The fixture relies on the DBC judging the PBC-set `r.expiresAt` by DBC time. That is existing E behaviour, not a new assumption.
- Credential `validUntil` values must outlast DBC time T+2, which they do in the E fixture (365-day certificates and 1-day lists).

**F-31 and F-32.**
- No ledger code is involved in F-31.
- F-32's premise (identical addresses on fresh chains, differing runtime for the profile-carrying contracts) is what I measured in `ledger/evidence/f0-d50-masked/`.
- The CSV's FM-01, FM-02 and FM-11 cross-references are accurate.

**Other ledger-facing cases** are unchanged in content apart from `experimentMode` and remain accurate: FL-2..FL-9, FL-11, F-14, F-15, F-21, F-23, F-30.

Not reviewed as owner (outside ledger scope; nothing contradicts the ledger):
- the protocol rows and hooks (M1–M7, H3–H6, F-12, F-13, F-16..F-20, F-22, F-25..F-27, F-29, F-31's tripwire);
- the pool-retry amendment, which is unwritten and which I will review when agent 2 publishes it;
- the evaluator and model tasks.

Evidence: hash recomputation; full read of the plan diff and the candidate-4 → candidate-5 case-level diff with every field, then the whole changed rows; the code lines above. No run.

Impact: none beyond this message.

Action requested:
- **agent-3:** fix K4 in the next candidate (with agent 2's revision-5 amendment if that comes first). I ACK that exact revision in ledger scope.
- **agent-2:** none from me.
- **human:** none.
