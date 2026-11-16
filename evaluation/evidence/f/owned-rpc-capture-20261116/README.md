# Owned witness RPC acquisition — A3-0161, 2026-11-16

Agent 3 / C-F1 continues A3-0160. **Tested reconstruction result:** a new
`evaluation.owned_witness_capture.CapturedWitnessProcess` collects exchanges at
the owned process pipe, using the existing bounded E transport without changing
it. This is implementation progress toward F's runner, not an F case result.

The user challenged repeated branch-only runs while independent runner work
remained. The live peers are not blocking this implementation: Agent 1's ledger
is READY, Agent 2's accepted protocol is READY, and both scoped report reviews
already exist. Their exact execution ACKs await the coordinator's complete
recipe/FREEZE. Unchanged remote refs must not stop the next independent runner
task. Next: implement source-pinned stage-3 baseline recipes and bounded isolated
execution, test-first with synthetic commands; do not execute actual integrated
services or cases before exact authorization.

## What changed and what was measured

- The parent records request/response wire bytes in `wire.jsonl`, counts attempts
  internally, and emits the existing capture and caller-sealed receipt formats.
  The journal uses hex to preserve bytes even when a complete frame is invalid
  UTF-8/JSON. An attempt record is not proof that its full request was written.
- Only the four public witness RPC kinds are accepted. Their message bodies
  pass the existing frozen v2 typed schema before sending/journaling. Worker
  operations, the worker crash API and unknown message fields are rejected.
- `completed_capture()` requires at least one matching exchange, natural stdout
  EOF, exit 0, no extra stdout, no stderr and no recorded transport/caller error.
  Shutdown drains stdout within its budget and retains at most 1 MiB of tail;
  over-limit or nonterminating children never yield a completed capture. Cleanup
  uses the existing bounded supervisor for this process only.
- The final 83 focused checks include 23 new acquisition probes plus existing
  process, sealing, signing-join and preflight checks. Initial RED: 17 failures
  because acquisition did not exist. First GREEN: 17 passed. Review added a
  failing secret-field test (1 failed/2 passed/17 deselected), then schema-based
  pre-send validation. The final command includes all later probes.
- `sample/` retains one real **synthetic child** run with four fixture signature
  replies, each joined to the existing synthetic signed-history fixture:
  AccessDecision, StateCheckpoint, GrantReceipt and GovernanceAction. Exit 0;
  `transportComplete=true`, 4 captured events, 4 joined signatures, 0 integrated
  cases. The child printed fixed public fixture replies; it did not validate
  proposals, sign messages itself, contact RPCs or run Agent 2's service.

## Reproduce

From repository root, with Python 3.13.13 and the existing root environment:

```text
.venv/bin/python -m pytest -q evaluation/tests/test_owned_witness_capture.py evaluation/tests/test_processes.py evaluation/tests/test_sealed_signing_capture_v1.py evaluation/tests/test_signing_event_join_v2.py evaluation/tests/test_f_preflight.py
```

Final exit 0, 83 passed in 23.14 seconds; raw output `green.txt`. Red/initial/review
outputs are retained separately; their exact commands and exits are in
`audit.json`. RED logs are losslessly gzip-compressed; raw SHA-256 values are in
the audit. They are development evidence, not F-case outcomes.

To regenerate the retained four-kind probe, supply a **new** output path:

```text
.venv/bin/python -m evaluation.evidence.f.owned-rpc-capture-20261116.probe evaluation/runs/owned-witness-capture-example
```

The probe imports synthetic test fixtures. Source input hashes include the probe,
fixture helpers, collector, transport, join/seal/schema modules and v2 schema;
see `source-inputs.sha256`. Check `SHA256SUMS` from this receipt directory. The
empty child stderr is retained as `sample/stderr.log.gz`; its decompressed hash
matches `sample/process.json`. PIDs/timestamps and argv paths are host-specific.

## Claims and remaining work

`transportComplete` describes this supervised, single-flight pipe session only.
It is not cryptographic capture authentication, global transcript completeness,
complete signed history, process honesty, absence of off-channel signing, native
ledger truth, persistence or Byzantine consensus. Both existing join flags remain
false: `captureAuthenticated` and `transcriptCompletenessEstablished`. Semantic
reply/signature verification still belongs to the existing independent join.
Incomplete/extra frames rejected inside the inherited roundtrip may not have
their raw partial bytes retained; failed sessions are not usable evidence of
complete capture. The caller must pin and review argv, source, environment and
fixture before any real run. This module is not yet wired into an integrated F
runner and is not a replacement for Agent 2's concurrent pool supervisor.

Report SHA `e59a51cd8c92a38780aa820191286887d9dc92deb1a0cdefe8c699f34a6e3b40`,
packet SHA `562f2047e2c45dfb677b3ba1439122d91196f9d614f88b8604a0add0dcc05aaf`,
and plan SHA `1a2d5e4fb7bd7fbf066a76d05e026db1a6e32079c36427cd63beda2c50dad919`
are unchanged. Their existing scoped reviews remain about those exact bytes.
Plan DRAFT/`authorizesExecution=false`, all 32 cases and Gate F NOT_RUN, G LOCKED.
Stages 3–7, native signing observations, integrated capture/history linkage,
integrated E regression and exact role ACKs/authorized FREEZE remain incomplete.
No services, actual protocol/ledger runs, integrated cases or external messages.
Review is same-author/correlated self-review; no extra agents/worktrees.
