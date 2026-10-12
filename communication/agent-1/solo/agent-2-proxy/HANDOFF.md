# agent-2 (proxy-2) handoff (2026-10-12, P4 in progress, after S2-0021)

Paper-derived HMBC2020 reconstruction, solo phase, synthetic fixtures only. Correlated self-review (A1-0059).

## Current pins
- **E2 FREEZE pin, used by every integrated run:** protocol 0716a8e / d16ddad8.. (108 entries). faulty_adapter f0ab2400.., deviating_witness 0511ba57...
- **Working protocol tree:** `protocol/evidence/source-manifest.sha256` sha256 551e9f774b91f8a0d55c60b85088de0e29b2c597682145f6d755a02c93649ae3 (127 entries; T1-T3 tests added in S2-0006). `sha256sum -c` exit 0 on 2026-10-12.
- `hmbc_protocol/**`, `testtools/**`, `exports/**`, `abi/**`: byte-identical to the pin at HEAD ec426c6 and again at 5c4c487 (S2-0021 review). The A1-0046 window adapter (8b7caf5) has byte-identical `hmbc_protocol/**` and `abi/**` too.

## Where things stand
- **Catalog 56/56 actual.** SL1-SL7 each have my protocol-scope ACK and REVIEW (S2-0004..S2-0020), no discrepancy. Review scripts and outputs: `protocol/evidence/reviews/s2-00{05,10,12,14,16,18,20}-*/`, each `problems: []`.
- **P3 closed** (A1-0081): ProVerif re-published byte-identical; live mutant matrix and integrated window **NOT RUN** by human decision after safety-classifier stops (A1-0080, A1-0081). Never resume them.
- **P4 in progress** (A1-0082). My part:
  1. `rq1-protocol-sections.md`: **refreshed 2026-10-12** (this handoff). It adds P14-P16 (prepare_request purity and verbatim authEpoch; lazy worker and D49; one adapter per deployment with shared label keys), per-slice adapter operations and A31 counts, D49 probe counts and never-publish scans, witness timing rules with measured margins, protocol text for every E01/E02 row, SL3/SL4 [I] text for §7.3, criterion-4 and window wording in protocol scope (A1-0080/A1-0081), process errors, "what the evidence does not show", and a 15-item must-not-claim list. The §7.2 figure placeholder is replaced by the A1-0064 citation.
  2. **S2-0021 sent** (`outbox/0021-ack-e-gate-run-freeze.md`): ACK of plan c0086019.., no blocker. Self-check OK (S2-0021; a wrong hash is refused). Review: `protocol/evidence/reviews/s2-0021-gate-freeze/` (`review_gate_freeze.py.txt`, exit 0, `problems: []`; `faulty-adapter-tests.txt`, 15 passed on this host). It establishes:
     - the pin;
     - the embedded plans equal the historical ones except runId/freezeMessage/agent3Sources, plus the SL0 host fields for the pre-solo slices;
     - the pinned production code has no port, env or HOME dependency;
     - the pre-solo adapter call sequence is unchanged; only the evaluator files access_execution/chain/e1/e2/rpc changed, by branch-isolated additions and the Cast checkpoint.
     It also has the margin table: agent 3's host repaired recovery retry 2.1-5.4 s, grouped replay 3.44 s, first replay −0.05 s; this host's repaired control release 25.0-26.4 s before expiry.
  3. After the gate run:
     - re-check the gate output for the same protocol facts: the 6 recovery rows with `expiredRetry` EXPIRED_NO_CHANGE_PASS, D49 observations, A31 counts, B's adapter;
     - check the publication selection excludes every `private-adapter-state/**` and passes the key/token scan, including `source-instance/`, `recovery/` and `expired-retry/`;
     - check the merged RQ1-E.md against the must-not-claim list;
     - then send the P4-3 same-source ACK naming the gate `manifest.json`, `gate-evidence.json`, RQ1-E.md sha256 and HEAD.
     If a repaired pre-solo row FAILED on EXPIRED, report it as a kept timing failure, never as a protocol finding.

## What I checked for S2-0021 (from A1-0082 P4-1; done)
- `owners.protocol` = 0716a8e / d16ddad8.. (108), materialized from git blobs.
- Aggregation only: the gate calls the same slice runners and oracles (`e2.create_plan` slice flags), no new oracle logic; slice directory layouts unchanged.
- Every stress deployment gets its own production adapter, 0700 state and pinned deployment (D2; A and B for wrong destination); D49 probes as in the slices; A31 counts still oracle-enforced in SL6/SL7.
- Mutant and window stages dropped; ProVerif re-run compared with A3-0033 and p3-proverif-20261012.
- Failed or timed-out rows kept, never silently retried; nothing writes in the repo during the run.
- Thin margins: SL7 expiry boundary ~1-2 s request-binding margin; SL6 expired-duty consume ~7 s. Overruns must fail visibly.
- Never-publish: no key, no raw token (`tokenSha256` only), deviating-witness raw logs private.
- Self-check the ACK with `e1._verify_solo_ack_message(raw, agent='agent-2', plan=..., plan_sha256=...)`.

## Reproduce (repo root)
```
export PATH="$HOME/.foundry/bin:$PATH" HMBC_FOUNDRY_DIR="$HOME/.foundry/bin" HMBC_TEST_PORT_RANGE=19545-19599 PYTHONDONTWRITEBYTECODE=1
# protocol owner suite (S2-0006): exit 0, 1375 passed, 201 skipped (~6 min)
.venv/bin/python -m pytest -q -rs -p no:cacheprovider -c protocol/pytest.ini --rootdir protocol --basetemp=<scratch> protocol/tests
# one slice review (example SL7): exit 0, problems []
.venv/bin/python -I protocol/evidence/reviews/s2-0020-sl7/review_sl7.py.txt evaluation/evidence/e2/sl7-destination-live-20261011 <repo>/protocol
# manifest
sha256sum -c --quiet protocol/evidence/source-manifest.sha256
```
Host memory is low: do not run a full suite unless asked.

## Limits
- Correlated self-review throughout; the original agent 2 has reviewed none of SL1-SL7.
- Symbolic adapter crypto; no ABE or real encryption; TEST-ONLY keys derivable from labels; one trusted witness; trusted worker; no consensus; not the authors' implementation.
- Logical crash points only; delivery unknown; key-substring scans only for SL4-SL7.
- Witness clock readings are bounded, not observed.

## Next action
- Agent 1 commits `communication/agent-1/solo/agent-2-proxy/{outbox/0021-ack-e-gate-run-freeze.md,STATUS.md,HANDOFF.md}` and `protocol/evidence/reviews/s2-0021-gate-freeze/` (4 files) with S3-0021 and A1-0083, before the run. The run compares `git status`.
- Proxy-2 reviews the gate output once agent 1 says the run has ended.
