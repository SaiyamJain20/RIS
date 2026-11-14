# Sealed signing-capture checks — 2026-11-15

## Scope

Agent-3-owned offline runner work. `sealed_signing_capture_v1` validates a
caller-supplied event count and SHA-256 over the canonical capture object before
invoking `signing_event_join_v2`. It rejects a count mismatch and post-seal edit;
the join checks contiguous event sequences and per-exchange request/response IDs.
The count must be obtained
independently to expose truncation. The receipt and count remain caller-supplied;
they do not authenticate the source, establish transcript completeness, prove
that the process ran the captured bytes, or join a native ledger observation to
a real signing time. Fixtures are synthetic; no services/chains/cases were run.

## Test-first and verification

The first implementation test run was RED as intended: the new test module failed
collection with `ModuleNotFoundError: evaluation.sealed_signing_capture_v1`.
After implementation, focused tests caught two design issues: non-ASCII JSON was
hashed differently from default ASCII-escaped JSON, and the wrapper rejected
sequential exchanges that reused a JSON-lines request ID. The encoding was fixed;
the global ID uniqueness rule was removed because the protocol only requires
per-exchange request/response ID matching. Two fixture setup omissions for the
profile's compiled `MAX_ADMINS` were corrected and retained. The final focused
suite passes 5/5; the full evaluation suite passes 3,003/3,003 in 679.32 s, exit 0.
Historical suite outputs are `evaluation-suite-3003-id-unique.txt` (before the
request-ID correction) and `evaluation-suite-3002.txt` (before the Unicode and
ID-reuse controls). Failure summaries are in `red.txt`,
`red-unicode.txt`, `red-rpc-id.txt`, `fixture-failure.txt`, and
`fixture-failure2.txt`.

Commands (repository root):

```text
uv run --frozen python -m pytest evaluation/tests/test_sealed_signing_capture_v1.py -q
uv run --frozen python -m pytest evaluation/tests -q
```

Environment: CPython 3.13.13, pytest 9.0.2, lock `uv.lock` SHA-256
`1fb4777a5d4078434af8e7fe4a88f2f3afbe1d8f65d30e8a182999d7a7a29cbe`.
The existing synthetic fixtures are in
`evaluation/tests/test_signing_event_join_v2.py` and
`evaluation/tests/test_witness_history_v2.py`.

## Source and output hashes

SHA-256 values are recorded in `hashes.txt`. The source inputs include the new
wrapper/test, existing signing-event join and its synthetic fixture modules. The
full-suite count includes the five new tests. Earlier legacy-Python invocation
`python -m pytest ...` exited 1 because `/usr/bin/python` has no pytest; the
pinned `uv run --frozen` invocation was used for all reported passing results.

## Classification and limits

This is a tested reconstruction result over caller-supplied synthetic records,
not an integrated F result. It verifies artifact consistency against the
provided receipt and catches duplicates/truncation only relative to supplied
metadata. No capture acquisition, cryptographic attestation of the receipt,
source counter validation, history-export completeness, native chain fact,
service validation, persistence, or production corruption-rate claim is made.
