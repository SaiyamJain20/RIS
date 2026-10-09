# agent-2 (proxy-2) handoff (2026-10-10, after S2-0006)

## Current pins
- **Protocol tree (working, READY in S2-0006):** `protocol/evidence/source-manifest.sha256` sha256 551e9f774b91f8a0d55c60b85088de0e29b2c597682145f6d755a02c93649ae3 (127 entries, `sha256sum -c` 0 failures).
- **E2 FREEZE pin, unchanged and still valid:** protocol 0716a8e / d16ddad8.. (108 entries). `hmbc_protocol/**`, `testtools/**` (faulty_adapter.py f0ab2400..), `exports/**` and `abi/**` are byte-identical to it; adapter.json is 7146495b...

## What S2-0006 added (tests and test-infrastructure only)
- **T1:** `tests/test_paper_release.py`. Paper subject routing on paper-strict and paper-minimal; asserted, never skipped.
- **T2:** `tests/test_recovery.py`. Crash before the durable intent leaves no trace; a restart releases once; three profiles.
- **T3:** `tests/test_faulty_adapter.py`. The first production restart after the original expiry answers EXPIRED with the worker log unchanged; 3 profiles x 2 points.
- **Ports:** `tests/conftest.py` gains opt-in `HMBC_TEST_PORT_RANGE=LOW-HIGH` for the live Anvil pairs. Unset keeps the old behaviour.
- **Mutants:** `tools/mutation_check.py` gains three mutants (suites routing, recovery, restart).
- **Docs:** one README line.

## Reproduce (repo root)
```
export PATH="$HOME/.foundry/bin:$PATH" HMBC_FOUNDRY_DIR="$HOME/.foundry/bin" HMBC_TEST_PORT_RANGE=19545-19599 PYTHONDONTWRITEBYTECODE=1
.venv/bin/python -m pytest -q -rs -p no:cacheprovider -c protocol/pytest.ini --rootdir protocol --basetemp=<scratch> protocol/tests
#   -> exit 0, 1375 passed, 201 skipped (~6 min)
# mutation check: copy protocol/ to <scratch>/repo/protocol, then in <scratch>/repo with GIT_DIR=<repo>/.git:
.venv/bin/python protocol/tools/mutation_check.py --only routing,recovery,restart --out <scratch>/m.json
#   -> exit 0, 3/3 DETECTED
PYTHONPATH=protocol .venv/bin/python -m hmbc_protocol.export --check
#   -> exit 0
```
Evidence: `protocol/evidence/p2-t1-t3/` (15 files) and `protocol/evidence/reviews/s2-0005-sl1/` (3 files).

## Messages
- S2-0001..0003: P0 reviews.
- S2-0004: SL1 protocol ACK.
- S2-0005: SL1 protocol REVIEW, with no discrepancy and these notes:
  - fingerprints repeat across fresh chains with deterministic addresses; no effect, because state dirs are new;
  - release margin was 28-29 s.
- S2-0006: READY for T1-T3.

## Limits
- Characterization tests: RED is mutant-based.
- Logical crash points only; no power loss.
- Only the 3 new mutants were re-run.
- In-process stub HTTP servers still use OS port 0.
- Live fixtures deploy ledger 91add8c (the suite's existing pin).
- Correlated self-review.

## Next action
- Agent 1 commits the exact paths listed in S2-0006.
- Proxy-2 ACKs SL2's FREEZE in protocol scope when it is published, then reviews its result.
