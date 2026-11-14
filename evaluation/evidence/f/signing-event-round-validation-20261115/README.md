# Signing-event round type validation — 2026-11-15

**Classification:** tested reconstruction result on synthetic captured RPC
lines. No service, chain, native RPC endpoint or integrated F case was run.

## Finding and correction

The offline `signing_event_join_v2` parser previously checked
`request["round"] in (1, 2)` and separately excluded booleans. Python also
compares JSON number `1.0` equal to integer `1`, so a caller-supplied envelope
with fractional JSON syntax was accepted as round 1. The helper now requires
`type(round) is int` and the value to be 1 or 2. This is a checker hardening;
it says nothing about what a live protocol service accepts.

## Verification

- RED: added `test_fractional_round_is_not_accepted_as_an_integer_round`; the
  focused command with `-k fractional_round` exited 1 because the helper did
  not raise `ValueError`. Output was displayed in the session but not retained
  as a file.
- GREEN: `.venv/bin/python -m pytest -q evaluation/tests/test_signing_event_join_v2.py`
  exited 0, 16 passed in 3.84 seconds. Captured output is
  `focused-green.txt` (SHA-256 recorded in `commands.json`).
- Full evaluation: `.venv/bin/python -m pytest evaluation/tests -q` exited 0,
  3,004 passed in 638.45 seconds. The summary was observed in the session; full
  stdout was not redirected or retained.

Environment: CPython 3.13.13, pytest 9.0.2, repository root
`/home/karma/Documents/RIS`. Fixture code is synthetic and lives in
`evaluation/tests/test_signing_event_join_v2.py`; source manifest is the four
join/capture files listed in `commands.json`. No external inputs, random seed,
services or integration run.

## Limits

This check validates a caller-provided capture envelope. It does not authenticate
the RPC source, prove capture completeness, establish a native signing time,
prove store export completeness or establish runtime behavior. Plan remains
DRAFT; all 32 F cases and Gate F remain NOT_RUN; G remains locked.
