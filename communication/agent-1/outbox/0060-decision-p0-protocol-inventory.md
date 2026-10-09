Message-ID: A1-0060
From: agent-1
To: agent-2 (proxy-2)
Cc: agent-3 (proxy-3), human
RQ: E
Task: decisions on S2-0001..S2-0003 (P0 protocol inventory), P2 assignment for agent 2, correction of my own rehearsal claim
Type: DECISION
Interface-version: v1 (FREEZE f700292e..)
Responds-to: S2-0001, S2-0002, S2-0003
Source-manifest: HEAD 8931563 (agent-1, integrated); ledger/tools/e2_rehearsal.py 8c8ecb09..; ledger/src/DecisionVerifier.sol header; catalog e0_cases.json 438fa38d..; host toolchain communication/agent-1/solo/evidence/host-toolchain/host-toolchain.json

Summary: **S2-0001..0003 accepted as owner evidence. These are agent 1's decisions, under the human's
solo directive:**

- R1: no H1. The forged-tuple row runs with a relay signature.
- Paper crash rows: provisionally Option A, via an explicit D-record, waiting on agent 3's
  concurrence.
- T1-T3 are agent 2's first P2 work.
- R2 is correct, and I correct my "56/56" claim below.

## D-S1: R1 forged tuple, repaired-e. No H1.

- The frozen row (`E01-forged-tuple-repaired-e`, `expected.qualification`) reads: "Repaired control
  uses a **non-witness signature** on an otherwise matching certificate; BAD_SIGNATURE must precede
  any grant."
- `DecisionVerifier` checks quorum signatures at **step 6**. Every checkpoint, freshness and expiry
  check comes later (steps 9-13); see the DecisionVerifier.sol header. A fabricated tuple, with no
  PBC request and a non-witness signature, therefore stops at step 6 with `BAD_SIGNATURE` (1)
  before anything that depends on PBC state. The code itself names the cause.
- The live run shows that the same deployment accepts witness-signed decisions through the Alice
  control in the same run, plus the E1 controls. The witness-signed fabricated-tuple variant stays a
  stated limit, backed by owner unit tests (agent 2's test and the ledger's DecisionBinding tests).
  Adding a signer that holds the witness key would blur key custody for a control that steps 1-6
  already pin.
- Agent 3's runner signs with the relay key. Agent 1's rehearsal recipe (one flipped bit on a real
  request) is **not** the catalog recipe. It stays owner evidence only.

## D-S2 (provisional): the four paper crash rows

Option A:

- The rows are reported as **SPEC_GAP (ambiguity)**, with outcome `UNPROVED` unchanged.
- The frozen label `BLOCKED` and agent 3's prior ruling ("No original-paper durability…",
  `expiry-live-20261009/catalog-coverage.json`) are recorded verbatim, together with the reason: the
  frozen qualification predates D35/A2-0012 (paper registered-key responses). Frozen bytes stay
  unchanged.
- SPEC.md:107 forbids a BLOCKED label "silently" becoming passed. This change is explicit, it is
  **not** a pass, and the live mechanics count only as a tested reconstruction result of our own
  design.

Classification belongs to agent 3, so **proxy-3 must concur or object** before this goes into
DECISIONS.md. If it objects, Option B (keep BLOCKED with an explanation) stands, and gate criterion 3
for E03 is argued in the report.

## P2 assignment for agent 2 (start now)

- T1, T2 and T3 exactly as specified in S2-0001 §T: characterization tests, `protocol/tests/**` and
  `protocol/evidence/**` only.
  - RED is shown by the scratch-copy mutant through `protocol/tools/mutation_check.py`.
  - Live tests use ports 19545-19599 only.
  - No change to `hmbc_protocol/**` or `testtools/faulty_adapter.py` (f0ab2400..).
- When done, publish **S2-0004 READY** with:
  - the new protocol manifest (same format as `protocol/evidence/*manifest*`);
  - commands, exit codes and RED/GREEN outputs.
- Then stay on call for agent 3's FREEZE ACKs (protocol scope).

## Corrections and notes

- **R2 (my error, now corrected):** `ledger/tools/e2_rehearsal.py:301-303` `dropped_outcome` calls
  `w.legit()` and never RELEASEs.
  - So my rehearsal's "56/56 MATCHED" did **not** exercise the worker for the three dropped-outcome
    rows. It checked only the ledger-side PSC status (pending after a grant with no outcome report).
  - The live runs must include RELEASE as the frozen steps require. The ledger fact it relies on is
    unchanged.
- **R3 (ledger confirms):**
  - repaired-e grant expiry = `min(decision.expiresAt, request.expiresAt)` (`ACSC.sol:190`), and
    the witness also caps the decision at the request (`witness.py:140`);
  - expiry rejects at `now >= expiresAt` (DV step 9).
  - The expiry-boundary runs must record both values and which one bound.
- **R4:** the P1 protocol suite is being re-run with `-rs`. The output goes to
  `communication/agent-1/solo/evidence/p1-integrated-baseline/protocol-rs.out.txt`.
- **Host toolchain (new):** ProVerif 2.05 has been built here from the pinned sources (sha256 match).
  - Its binary is bc2cd5ed.. (agent 3's build: c1087205..).
  - The `access.pv` and `access_mutant.pv` RESULT lines are **identical** to agent 3's saved outputs.
  - Foundry and solc are byte-identical to the frozen pins.

Impact: P2 starts with agent 2 on T1-T3. Every remaining catalog row is runnable on existing
protocol code.
Action requested: agent-2 do T1-T3, then S2-0004 READY. agent-3 concur or object on D-S2.
