# Evidence: the witness operations wired into the successor command line (A2-0074 proposals P1 and P2)

Code: `hmbc_protocol/adapter_v2_main.py` (`build_runtime`, the supervisor lifecycle in `main`, the optional TEST-ONLY `--allow-governance`), tests `tests/test_adapter_v2_main_wiring.py`, runner `tools/run_adapter_v2_main_mutants.py` (extended). `build_context` is byte-for-byte unchanged. PAPER-DERIVED RECONSTRUCTION; symbolic; TEST-ONLY keys; CPython 3.13.12, pytest 9.0.2 (frozen root `uv.lock`); one host; correlated review.
All results below are runs I made myself.

| Check | Result | File |
|---|---|---|
| RED, wiring tests on the unwired CLI | **18 failed, 1 passed**; every failure is a missing `build_runtime` or `allow_governance` (the 1 pass is the control that `build_context` is unchanged) | `RED-wiring-tests-18failed-1passed.txt` |
| GREEN, wiring tests with the three existing CLI test files (`test_adapter_v2_main.py`, `test_startup_refusals.py`, `test_witness_main.py`) | **276 passed**, 0 skipped, exit 0 | `GREEN-wiring-plus-CLI-tests-276passed.txt` |
| `run_adapter_v2_main_mutants.py` (43 mutants, 1 argued equivalent) | control passes; **43 / 43 detected**, exit 0, 10 min; the 12 new wiring mutants W1..W12 are all detected | `runner-adapter-cli-43of43.txt` |

**A real bug the first GREEN run found (kept):** `SupervisorError` is a `RuntimeError`, not a `ValueError`, so a manifest with the wrong number of witness labels escaped `build_context`'s `except ValueError` and would have reached `main`'s last-resort guard under the WRONG closed code (`ADAPTER_UNAVAILABLE` instead of `MALFORMED`). Fixed in the wiring (the factory call maps it to `Refusal("MALFORMED")`); the test that found it stays.
**A mistake of mine in the runner (kept):** my first insertion of the new mutants landed in the equivalents list `E` (mutants that must SURVIVE) instead of `M`; the "31 mutants" count instead of 43 exposed it before any run. Two older anchors (C12, C30) and the equivalent C25 went stale or ambiguous because `main()` and the new `wired_start` repeat their text; all re-pointed, every anchor is validated to match exactly once before anything runs.
**Not established here:** real processes behind ONE adapter command (the live tests are separate), a completed F case, the alternate TEST-ONLY adapter entry (proposal P3).
