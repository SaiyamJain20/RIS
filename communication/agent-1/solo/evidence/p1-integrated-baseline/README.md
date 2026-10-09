# P1 integrated baseline (agent 1, 2026-10-09)

Tree: `78cdd11c6a99ca0aaab57fc031ee0699b759ba0d` = agent-1 2d01f5e + merge origin/agent-3 8e5a6dd (human, 3c068cf) + merge origin/agent-2 96ebe16 (agent 1, 78cdd11). No conflicts (disjoint paths).
Versions: `versions.txt`. Python: repo-root `.venv` 3.13.5 (agent 3 froze 3.13.13; patch-level difference recorded), eth-account 0.14.0, jsonschema 4.26.0, pytest 9.0.2. Foundry 1.8.5 binaries **byte-identical** to evaluation/toolchain.json pins (forge 06c477ae.., anvil 00f97668.., cast 1eb1eecf..); solc 0.8.37 identical (5de843c2..).

| Suite | Command | Exit | Result |
|---|---|---|---|
| ledger | `forge test --root ledger` | 0 | 166 passed, 0 failed |
| protocol | `.venv/bin/python -m pytest -q protocol/tests -p no:cacheprovider` | 0 | 1365 passed, 201 skipped, 361.9 s |
| evaluation | `.venv/bin/python -m pytest -q -p no:cacheprovider` (root testpaths = evaluation/tests) | 1 | 750 passed, **27 failed**, 123.4 s |

## The 27 evaluation failures: host portability, not code defects (diagnosis, to be confirmed by agent 3 proxy)

- 20 in `test_e1_freeze.py` / `test_e2_freeze.py`: `ValueError: Public access tool binary hash failed` or the BLOCKED status that follows from it. The plans pin tool **paths** on agent 3's host (`/home/karma/.local/share/hmbc-tools/...`); the binaries here have identical hashes at different paths.
- 1 `test_interruption_records_failure_and_propagates_cancellation` (DID NOT RAISE KeyboardInterrupt): not yet diagnosed.
- 6 in `test_e_correspondence.py`: `FileNotFoundError /home/karma/.local...` — ProVerif 2.05 not installed on this host. Agent 1 is building it from the pinned sources (OCaml 4.14.2 c2d70643.., ProVerif 2.05 4871f53c..); a locally compiled binary hash will differ from agent 3's c1087205.. and will be recorded as a host difference.

Raw outputs (ANSI stripped, progress lines dropped): `forge.out.txt`, `protocol.out.txt`, `evaluation.out.txt`.

## R4 follow-up: protocol skips explained (`pytest -q -rs`, exit 0, 1365 passed / 201 skipped, 345.8 s)

`protocol-rs.out.txt`: 100 `test_boundary_review.py` + 100 `test_boundary_review_r5.py` "ScenarioResult is not agent-2's scope"; 1 `test_candidate_schema_review.py:35` "FileHash is not an agent-2 wire type (agent-3 evaluation schema)". No skip in `test_paper_release.py` on this host (S2-0001 R4's silent-skip risk did not trigger here; T1 removes it anyway).
