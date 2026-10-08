# Agent 2 handoff (2026-10-08, updated for A2-0010): E0 revision-5 review done; supplement controls measured; candidate B-E1/B-E2 built; NOT E1-unlocked, NOT integration-ready

- RQ/task: E / E0 (acceptance pending) with CANDIDATE B-E1/B-E2 code built ahead of the unlock at the user's instruction. Interface: candidate v1 revision 5
  (agent-3 A3-0012, manifest 124b95eb..., 32 files), NOT frozen. No INTERFACE_READY, E1 unlock or gate is claimed. F and G are untouched (locked).
- Authoritative record: immutable message A2-0009 and `protocol/evidence/source-manifest.sha256`. This file is a snapshot.
- Environment: CPython 3.13.15 (uv venv), eth-account 0.14.0, jsonschema 4.26.0, pytest 9.0.2; Foundry 1.8.5 (51a52c59, hashes = toolchain.json pins); solc 0.8.37 via forge.
  Root `uv.lock` NOT used by me (agent 3 reproduced the E0 suite under it, A3-0010). Ledger under test: agent-1 commit 33a7a5d (ledger sources = e6cf4ff / A1-0014).
- Commands (repo root) and results on agent 2's machine:
  - `python -m pytest protocol/tests -q -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider` -> exit 0, 1307 passed, 201 skipped (agent-3 ScenarioResult/WorkerExpectation/FileHash
    cases that are not agent-2 wire types), 0 xfail, ~3.5 min (live tests start/stop their own Anvil pair on free ports). Log: `protocol/evidence/pytest-e0.txt`.
  - `PYTHONPATH=protocol python -m hmbc_protocol.export --check` -> exit 0 (adapter.json + 8 operation examples equal regeneration).
  - `python protocol/tools/mutation_check.py` (on a scratch copy; edits sources in place) -> 62/69 source-edit mutants detected, 7 documented equivalent survivors, 0 gaps (`protocol/evidence/mutation-check.json`, merged from two runs).
  - `python protocol/tools/crosscheck_schema.py <a3 3e0300a snapshot> --cases protocol/tests/fixtures/boundary-cases-a3-3e0300a.json` -> 7187 mutated inputs, 0 disagreements with agent-3's validator.
  - `python protocol/tools/validate_examples_with_agent3.py <a3 3e0300a snapshot>` -> 16 example cases, 0 disagreements.
- What is real (candidate, symbolic mode): strict EIP-712/wire layer; ABI codec; chain client (pending-block clock, loopback-only, no redirects/proxies); ledger loader (ABI-hash pinned);
  user client; honest relay; single trusted witness (checkpoint, policy-aware decision, grant receipt); durable key worker (write-ahead intent AND send attempt, same cached response on retry,
  expiry bound, crash recovery, deployment-bound state, read-only evidence export); adapter with 8 operations (7 success shapes) and a PINNED deployment (`--deployment`).
  Live evidence: `protocol/evidence/live-adapter-flow.json` (full legitimate flow through the adapter PROCESS), `tests/test_e2_repaired_e.py` (16 repaired-e catalog cases, all agree),
  independent review disposition `protocol/evidence/independent-review-2026-10-08.md`.
- What is NOT done / not claimed: no E1 integration run (runner role played by tests); paper-profile cases (no paper deployment made); F/G; real ABE; power-loss durability (crash tests are in-process);
  authentication of the registrant in encrypt_record (first writer wins the payloadDigest; interface-level limit); catalog coverage of the receipt-binding mutant (see A2-0009).
- Messages sent: A2-0001..A2-0010. Read: A1-0001..A1-0020, A3-0001..A3-0017 (origin/agent-1 012f24c, origin/agent-3 bf10823 at last fetch).
- A2-0010 additions: export label fixed to revision 5; WRONG_PROFILE for witness operations on paper deployments; paper-strict/mutant fixtures; TEST-ONLY deviating-witness tool (`protocol/testtools`, outside the adapter);
  supplement controls MEASURED (receipt binding on repaired-e vs mutant-no-receipt-binding; same-nonce distinct-digest schedule on repaired-e vs mutant-no-nonce); paper review exceptions X-1 (8 cases need a RELEASE of a zero-recipient paper grant, refused by the worker: OPEN decision) and X-2 (paper subject-substitution wording).
- Reproduce: clone SaiyamJain20/RIS, checkout agent-2 (needs git objects of agent-1 33a7a5d for the live fixture: `git fetch origin`), Python 3.13 venv + `protocol/requirements.txt`, Foundry 1.8.5 on PATH or `HMBC_FOUNDRY_DIR`, run the commands above.
