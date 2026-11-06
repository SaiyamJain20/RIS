# Exporter framing and captured marker binding — C-F1, 2026-11-06

Classification: **synthetic tested reconstruction/extension result**. Internal
evaluator composition only, not an HMBC paper vulnerability or integrated F case.

`evaluation.export_snapshot_v2.verify_export_snapshot` requires caller-selected
BindingExport/WitnessEvidence, exit0, empty byte stderr and exactly canonical ASCII
JSON plus one LF. It composes anchored binding/owner checks or the full declared
signed-history checker, then compares the physical captured INITIALIZED content
with closed schema2/owner/binding and the witness export's declared marker.
Duplicate keys/nonfinite constants/invalid JSON refuse. Marker whitespace is
unspecified and permitted; its exact bytes are separately fingerprinted. The
result includes stdout/marker/logical SHA256 and unchanged history labels/counts.
No file/RPC access or existing consumer/default-v1 switch occurs in this API.

Verification (all fresh; exact UTC/argv/exits/output hashes in commands.json):

- Genuine missing-module RED: **57 failures**; implementation GREEN:57 PASS.
- Fault/clear and bit1/bit5 exclusion composition controls:61 PASS; duplicate-key
  hardening controls bring final new suite to **64 PASS**.
- Seven narrow in-memory bypasses each admit bad input the real checker refuses:
  exit status, stderr, canonical framing, physical marker, anchored context,
  signed history, duplicate marker keys. No source file mutated.
- Combined v2 schema/certificate/context/observation/signing/history/store/export
  suite: **686 PASS in40.48s**, exit0.
- Bare root `.venv/bin/python -m pytest -q`: **2371 PASS in416.65s**;
  command416.977s/exit0. All **244 selected inputs and175 complete execution
  sources** unchanged before/after, independently checked again before publication.
- Frozen source manifest SHA256:
  `2d4e5ca326d3c67270283f80e6eda2ad81c4040324d76349bebd26cbfef7effb`.
  Python3.13.13, SQLite3.47.2, Git2.54.0, pytest9.0.2, jsonschema4.26.0,
  eth-account0.14.0; no new dependencies.

Real **synthetic local SQLite** controls run under the existing locked reader.
A WAL-only inserted, unexported row changes logicalSha256 while stdout and marker
hashes stay equal and these checks still pass. This intentionally preserves the
boundary: **a matching marker and verified export do not prove row completeness**.
Raw real snapshots must remain private, because an exporter may redact their data.
No owner store/runtime/exporter is opened, imported or run in these tests.

Peer reads: initial Agent1 `8c0285ffa6986858caeb0140b930bf5db759fdc0` unchanged;
Agent2 `42435367cad02063cd8573333ad12a59c38bed92` added pool driver/virtual transport.
Final fetch advanced Agent2 to `254faacdb2344aabed6bb9f66957fc5101487dd6`:
new four witness operation handlers and governance list-field pool support.
Read full new source, relevant tests and latest owner STATUS/HANDOFF; exact
file-changing commits/hashes retained in peer-review*.json and full communication
scan. **368 communication paths, no divergence/ambiguity**;429 reviewed ledger
READY entries/52 frozen F0 pins/31 publication payloads/four copied fixtures verify.
No new addressed outbox since A1-0116/A2-0062 and no source READY/execution ACK.
Owner test/mutant counts and its changed-view/adoption observation were **not
rerun or adopted**. The owner explicitly says NOT_READY; its fake shared ledger
view/virtual time do not prove independent views, live transport or timing.

Limits: caller must pin reviewed paths/locking choreography and hold the proper
lock across snapshot/export/action; this helper cannot enforce that externally.
Snapshots/fingerprints do not authenticate a store/producer. Producer-specific
row projection, orphan/export completeness, native observation/death truth,
arrival chronology, real transport/timing, persistence/power loss, new E parity,
integrated F cases and GateF remain unproved/NOT_RUN. Qualified historical E is
unchanged;32 F cases NOT_RUN; G locked. Complete owner READYs/full consumer mapping
and a separate complete exact source/tools/config/run FREEZE with affected ACKs
precede services/scenarios. Next owned work is row completeness when reviewable,
raw owner-ABI observation/death joins, then independent fault oracle/finite model.

Review is correlated author review because the user prohibits extra agents.
Initial lock attempt mistakenly used mkdir against the established file and
read context before acquiring flock; it refused without changing the lock inode.
Actual scheduled file flock was then acquired before project fetches/edits and
held, with the separate coordinator lock, through publication. A speculative
peer-metadata correction helper wrongly assumed a literal newline escape and
failed its assertion before changing any file. The original JSON was valid;
its successful parse and failed helper log were retained. No test failure or
production check was weakened. Publication/remote/lock cleanup are in
automation memory and its external run directory; no main push or peer edits.

Reproduce: new test file, combined command in commands.json, root pytest, then
`sensitivity.py` and `verify.py`. Logs are lossless gzip with raw/compressed hashes.
