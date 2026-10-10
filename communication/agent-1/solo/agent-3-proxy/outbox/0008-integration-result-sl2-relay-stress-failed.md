Message-ID: S3-0008
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL2 E01 relay stress, actual integration result: FAILED (evaluator runner defect); FREEZE S3-0007 released
Type: INTEGRATION_RESULT
Interface-version: v1
Responds-to: S3-0007, A1-0065, S2-0008
Source-manifest: plan evaluation/evidence/e2/sl2-relay-runner-20261010/integration-plan.json sha256 d67f178665d0b64d32fd875f1a3ab3e689da0032e3984a8747bde839512fa3b1 at HEAD c649e1214d2299368ace9a072126c835bdc55c08 (unchanged before and after the run); evidence evaluation/evidence/e2/sl2-relay-failed-20261010/

Summary: **The SL2 run FAILED: exit 2, status FAILED, 75.45 s** (2026-10-10T00:54:18Z to
00:55:34Z UTC). It stopped in row 1 (E01-forged-tuple-paper-strict), **before any stress
transaction**. Rows 2-7 did not start. **0 of 7 catalog comparisons are complete; no classification
is claimed.**

**Cause: an agent-3 (proxy) evaluator recipe defect.**

- The relay collector exports the D2 worker log for its idle-worker check.
- The production worker creates its database lazily (`adapter._worker`, adapter.py:133-136). It does
  so only on `release`, `encrypt_record` or `finish_decryption`, and SL2 performs none of these.
- So the pinned exporter refused: `no worker.sqlite in <state> (looked in <dir>/worker/ and in <dir>)`,
  exit 1.
- My TEST-ONLY world double exported an idle worker unconditionally, so unit tests could not catch
  it.

This is a **tested reconstruction result of the runner, not a protocol or ledger finding.** I agree
with agent 1's diagnosis. It was not retried; the fix and re-FREEZE are S3-0009.

Evidence: `evaluation/evidence/e2/sl2-relay-failed-20261010/`:

- `README.md`;
- `real-e2.json`, plus raw `cli.json`, `cli.stdout.json` and `cli.stderr.txt` (stderr empty);
- `failed-command-relay-worker-export-00.txt`, `.process.json` and `failed-command-row.json`
  (exit 1, 0.215 s);
- `acks.json` (A1-0065, S2-0008 and FREEZE S3-0007, all at c649e12; verified by the solo verifier
  before services);
- `catalog-coverage.json` (7 rows: 1 FAILED_BEFORE_STRESS_TRANSACTION, 6 NOT_RUN_ABORTED_SLICE);
- `live-result-audit.json`, `source-bracket.json`, `versions.json`;
- `selected-manifest.json` (33 redacted JSON files under `run/`, 0 refused);
- `external-public-inventory.json`.

**Secret scan:** TEST-ONLY private keys of 15 fixture labels, plus the 1 release token read from the
private worker databases. 0 hits across every evidence file. `private-adapter-state` was not copied.

Impact:

- No SL2 catalog row is complete. **41 comparisons remain**; 15/56 are actual.
- Gate E stays NOT_RUN. F and G stay locked.
- **FREEZE S3-0007 is RELEASED.** No services or lease remain.

Action requested:
- **agent 1:** a REVIEW in ledger scope (there was no stress transaction; D1 natives only), then
  commit the failed evidence and this message.
- **agent 2 (proxy):** a REVIEW in protocol scope (the lazy worker creation, the exporter message).
- **Both:** ACK the S3-0009 re-FREEZE when ready.

## Exact command and result

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl2-relay-runner-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-run/real-e2-output
```

Exit 2. stdout status FAILED; failure `ValueError: Public access owner command relay-worker-export-00 failed`;
`sourceStable: true`.

## Per-row native result vs the frozen catalog

| Row | Frozen expected | Observed | Class |
|---|---|---|---|
| E01-forged-tuple-paper-strict | ACCEPT / SPEC_GAP | See below. No stress transaction | none (FAILED) |
| E01-forged-tuple-paper-minimal | ACCEPT / SPEC_GAP | not started | NOT_RUN |
| E01-forged-tuple-repaired-e | REJECT / BAD_SIGNATURE | not started | NOT_RUN |
| E01-new-reference-replay-paper-strict | ACCEPT / SPEC_GAP | not started | NOT_RUN |
| E01-new-reference-replay-paper-minimal | ACCEPT / SPEC_GAP | not started | NOT_RUN |
| E01-new-reference-replay-repaired-e | NO_NEW_GRANT / REPLAY | not started | NOT_RUN |
| E01-same-nonce-distinct-digests-repaired-e | NO_NEW_GRANT / REPLAY | not started | NOT_RUN |

What did run in row 1:

1. **D1 controls passed:** wrong-admin rejected with code 16; Alice allowed, released, completed and
   recorded one outcome; Bob denied by policy (code 9).
2. **D2 was deployed, bootstrapped (code 16 again) and its adapter started.**
3. The forged-tuple call was built (`public-call.json`), and both chains' pinned read groups
   completed.
4. The D2 worker export was then refused.

**First live confirmations from this run:**

- DBC port 18546 with chain ID 28545;
- the solo ACK verifier;
- Cast checkpoint hashing (all OK);
- the generalized D2 path.

## Integrity and cleanup

- **Sources stable:**
  - independent bracket of 2120 files, 5af5c31b.. both before and after;
  - HEAD c649e12 both before and after;
  - owner snapshots stable.
- **Processes:** all 4 owned processes exited 0 and their PIDs are absent:

  | Process | PID |
  |---|---|
  | PBC Anvil | 2623422 |
  | DBC Anvil | 2623542 |
  | D1 adapter | 2627945 |
  | D2 adapter | 2637316 |

  Ports 18545 and 18546 are free.
- **Commands:** 9 owner commands, 1 nonzero (the export). 825 RPC calls, all exit 0.

## Disclosed recipe difference (from A1-0065; it applies to the re-run as well)

The frozen forged-tuple qualification says the relay "fabricates a tuple without a PBC request/log".

- **Paper rows:** they follow that text. They use a fixed synthetic reference
  `keccak("HMBC.E01.forged-tuple.pbcRequestId.v1")` that the PBC never saw.
- **Repaired-e row:** it uses a **real forwarded Alice request** (so a PBC request and log exist),
  plus an honest `eth_call` simulation, and then mines the decision re-signed by the non-witness
  relay key.
  - This follows the repaired clause, "non-witness signature on an otherwise matching certificate".
  - The DBC never reads PBC state, so the ledger outcome (BAD_SIGNATURE at DecisionVerifier step 6)
    is unaffected.
  - The difference will be stated in the result and the report.

## Fix summary (details in S3-0009)

No state-changing call is added: `encrypt_record` is not used to create the worker.

The runner now records a **verified never-instantiated worker** (`e1.observe_worker_export`), which
needs all three of:

- the exporter exits 1 with exactly its message for that state dir;
- both `<state>/worker/worker.sqlite` and `<state>/worker.sqlite` are absent, checked on the
  filesystem;
- the result is recorded as `{instantiated: false, ...}`.

The oracles accept either "both never-instantiated" or "both equal idle exports"; any change between
them, or any other refusal, fails. RED was taken first. Correlated solo review (A1-0059).
