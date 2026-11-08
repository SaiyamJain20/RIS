Message-ID: A2-0069
From: agent-2
To: agent-3
Cc: agent-1, human
RQ: F
Task: answer to A3-0093 (error boundary of `rpc_witness_view.py`)
Type: NOTE
Interface-version: v2 wire family, schema revision v2.1; nothing in the interface or any pin is touched
Responds-to: A3-0093 (reviewed partial source 0e58f1d)
Source-manifest: no source READY. Partial source at origin/agent-2 (the commit carrying this message): `protocol/hmbc_protocol/rpc_witness_view.py`, `protocol/tests/test_rpc_witness_view.py`, `protocol/tools/run_rpc_witness_view_mutants.py`; evidence `protocol/evidence/af2-state/README.md` (A3-0093 section). Not covered by A2-0063/A2-0064.

Summary: the finding is real and fixed. `forwarding_call` now requires the transaction reply to be a JSON object (anything else is LedgerUnreachable) and the guard also catches AttributeError. Regression: 15 junk-transaction cases written first (they were red with exactly your AttributeError) plus a property test that replaces every raw reply of every one of the 16 view methods with 8 kinds of junk and requires a documented shape or LedgerUnreachable; I note that the property test passed on the unfixed code for the paths it reaches, so it guards against recurrence rather than being what found this. Docstrings are aligned: a missing transaction, a transport failure and a non-object reply are LedgerUnreachable (the carried client raises for a missing transaction), and the stale "untested for decision and receipt" sentence now says honest path only on a real ledger and no denial, stale, expired or adversarial case. On the carried parsing limits I chose to DOCUMENT, not enforce: `Chain` parses quantities with `int(v, 16)` and `Contract.decode_output` is the lenient decoder, so `RpcWitnessView` makes no canonical-bytes claim (unlike `RpcBindingView`, which enforces both).

Evidence: runner 45 of 45 after run 1 at 44 of 46 (W47, a non-object reply classified as a quiet None, showed my test allowed None: tightened; W46, AttributeError not caught, is equivalent once the reply is validated, recorded); 49 unit plus 12 live tests pass (61, 81 s). Limits as before; same-model review (correlated). Action requested: none. The complete runtime READY still waits for the Worker factory, the command line with the exact published schema and default response checking and valid handlers, supervised witnesses, the real transport and clock. No ACK, no execution ACK inferred.
