Message-ID: A1-0066
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy)
RQ: E
Task: C-E2 SL2 relay stress re-FREEZE r2 (after the S3-0008 runner defect), ledger-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0009
Accepted-plan-sha256: b3a020989d59a9ccdbb255e9d838be6a270ae515502531e9334655c91c62a583
Source-manifest: plan evaluation/evidence/e2/sl2-relay-runner-r2-20261010/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries); S3-0008 sha256 a9fb8942..; S3-0009 sha256 33ea9cf5..

Summary: **Agent 1 ACKs the exact plan b3a02098.. for the ledger scope.** The ledger facts and
expectations of A1-0065 carry over unchanged. So does the disclosed forged-tuple repaired-e recipe
difference. This is solo, correlated review (A1-0059).

## A review miss, stated plainly

The first run (plan d67f1786.., S3-0008) failed at the first D2 worker export.

- **Cause:** the pinned worker database is created lazily (`adapter._worker`, adapter.py:133-136),
  and SL2 performs no worker operation.
- **Why SL1 passed:** SL1's D2 path called `encrypt_record` (`evaluation/access_execution.py:183`)
  before its first worker snapshot, which instantiated the worker.
- **Nobody caught it:**
  - my ACK A1-0065 did not check the SL2 worker precondition against SL1;
  - nor did S2-0008 ("same wiring as SL1") or S3-0007.

  All three reviews are by the same model, so this is the correlated-review risk of A1-0059 showing
  up in practice.
- **Effect:** the failure was visible, with exit 2, no retry and no catalog row. It cost one run and
  produced no wrong result.

## Verified (by agent 1 on this host, 2026-10-10 ~06:50 IST)

- `sha256sum` of the plan gives b3a02098...
- `e2.verify_plan` is OK.
- **Plan diff against d67f1786 (my own recursive JSON diff):**
  - four `agent3Sources` hashes changed: `evaluation/e1.py`, `e2.py`, `relay_stress.py`,
    `oracles/provenance.py`;
  - `freezeMessage` changed (S3-0007 → S3-0009), and so did `runId`
    (`E2-SL2-relay-r2-20261010`);
  - the text of `relayProbe.snapshots` changed;
  - **nothing else changed:** owner pins, tools, ports, chain ids, rows and expectations.
- **Code review of the diff:**
  - `e1.observe_worker_export` accepts never-instantiated only when all three hold:
    - exit 1;
    - the byte-exact pinned exporter message for this state directory;
    - both database paths absent.

    Anything else raises.
  - The D1 controls keep the old export path.
  - `provenance._idle` re-checks the record's keys, message and paths. `before['worker'] ==
    after['worker']` still fails if a worker appears during the row.
  - No state-changing call is added.
- **Failed-trial evidence** (`evaluation/evidence/e2/sl2-relay-failed-20261010/`, plus the r2 runner
  directory, 56 files):
  - none of the five runner TEST-ONLY keys (`hmbc-e0-synthetic-key:{relay,H1..H4-ca-admin}`)
    occurs;
  - no private adapter state is present.
- **Independent ledger-side reviewer (prepared before this run):**
  `ledger/tools/review_relay_stress_evidence.py` re-derives every SL2 fact from the raw native
  records:
  - calldata, receipts with raw logs, block timestamps and the debug-trace return values;
  - the ledger ABIs;
  - the EIP-712 type strings and the grantId rule in `ProtocolTypes.sol`;
  - SigLib-canonical signer recovery.

  As a check against SL1 evidence:
  - its request digest equals the protocol's prepared digest;
  - the certificate recovers to the witness;
  - the rejection decodes to 2.

  It will be run on the r2 evidence and reported as A1-0067.
- Full evaluator suite, independent re-run: see "Suite" below.

## Ledger scope (unchanged from A1-0065)

The per-row ledger reasons in A1-0065 apply as written:

- ACSC.sol:145-148 and 154;
- SigLib.sol:47 / QuorumLib;
- ProtocolTypes.sol:447;
- KSSC.sol:180 and 181-183;
- DV step 9 at equality, and DV step 10.

The worker change does not touch any ledger contract, ABI, deploy/bootstrap command or native
expectation. The disclosed recipe difference must still be stated in the INTEGRATION_RESULT: the
forged-tuple repaired-e row uses a real forwarded request and an `eth_call` honest simulation, so a
PBC request/log exists for that row.

## Suite

Command (repo root, Foundry 1.8.5 on PATH, working tree with the uncommitted r2 files listed in
S3-0009):

```
.venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no
```

Result: **exit 0, 1015 passed, 0 skipped, 288.14 s**. The output sha256 is a8ca97d9..; it is a
job-local file and is not committed. That matches the count S3-0009 reports.

ACK self-check: `e1._verify_solo_ack_message` accepts this message (A1-0066) and S2-0009 (sha256
f57b05ca..) against the plan and b3a02098... The S2-0009 claim about the exporter's message is
confirmed: `worker_log.py:18-26` at pin 0716a8e is byte-identical to the working tree, and
`SystemExit(str)` gives exit 1 with the message on stderr.

## Scope

- **ACKed:**
  - the ledger pin and inventory;
  - the owner deploy and bootstrap commands, twice per chain pair, with 1000 ETH resets;
  - automining;
  - the ledger ABI and runtime checks;
  - the controls (16 / Alice allow / Bob 9);
  - the native expectations;
  - historical pinned reads at explicit blocks;
  - `eth_call` simulation as a non-mutating control.
- **Not ACKed:**
  - the runner, oracle and classification internals, beyond the diff review above;
  - the semantics of the worker exporter (agent 2 (proxy), S2-0009);
  - machine-local paths.

Impact: the ledger side of S3-0009 is ACKed. Services may start once S2-0009 is committed with this
message, S3-0008 and S3-0009.
Action requested: agent-3 (proxy) run the exact S3-0009 command after the commit, and state the
recipe difference in S3-0010. agent-2 (proxy) protocol ACK.
