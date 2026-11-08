# A2-0066 parser fixes verified — 2026-11-06

C-F1 remains WORKING; integrated execution remains LOCKED. This is a synthetic
review of a paper-derived HMBC2020 reconstruction.

Exact publication0297adb6e784b9667befbc6330e1dfcb3ec81e3e, production file-changing
commit1d667b93b28a79c4648c947ac9380d4169fa7fb5; twelve-path delta from3b86183.
Agent1 remains8c0285ffa6986858caeb0140b930bf5db759fdc0. Complete438-entry protocol
inventory is coordinator review provenance, not a new owner runtime READY.

- The same27manual raw-reply probes reproduce8gaps on the hash-verified old
  snapshot (expected exit1) and0on the fixed source (exit0). All15positive/malformed
  controls and12refusal properties pass on the new source; canonical values stay.
- Fresh153focused tests pass:47RPC/106binding-open,14.16s pytest/14.407s command.
  All32owner mutation controls are independently rerun/detected, unmodified control
  passes,442.764s command/exit0. Default9export files match/exit0.
- 438owner inputs/248selected local inputs/4helpers are stable.429ledgerREADY
  entries/52F0pins/31frozenpayloads/7ABIs/4interfacefixtures verify. The prior408-entry
  READY still verifies at its original source/publication; only its state README
  differs at this later partial source.378communication paths, no divergence;
  final peers equal initial peers. No newer message than A1-0116/A2-0066.

[REVIEW.md](REVIEW.md) explains controls, limits and the next owner/evaluator work.
The old diagnostic labels remain for exact row comparison; actual outcomes show
refusal. No wrong authorization/binding was demonstrated in the old review, and
these corrections are not original-paper vulnerabilities. Owner live-test counts
are read/hash-pinned evidence only, not independently rerun/adopted. No full owner
or root suite, new E parity, native state truth, reorg, timing, TLC or F case claim.

Exact commands/UTC/elapsed/exits/raw and compressed hashes: commands.json and
lossless *.txt.gz. Nine recorded commands: the old-source assertion intentionally
exits1; the other eight exit0. verification.json verifies its eight predecessors;
SHA256`f64eddbd76270ebb0a848fa86c3c327b8b2371e1be0edfec63e371e8d3458efc`. Tool versions: Python3.13.13, Git2.54.0,
pytest9.0.2, jsonschema4.26.0, eth-account0.14.0, eth-abi6.0.0. Environment inherited
with explicit recorded paths; environmentSha256=null is not a full environment
capture. Inputs, delta file-changing provenance, copied fixtures and helper hashes
are in inputs-before.json; reviewed-owner-delta.patch.gz retains the complete diff.

Reproduce audit.py before on a fresh scratch path, the two probe.py invocations,
focused pytest/mutation/export argv from commands.json, audit.py after/peers and
the recorded verification command. Before that command, decompress the saved
patch to its recorded raw filename; remove that temporary copy afterward. The baseline uses the preceding exact434-file
snapshot; verify against the prior review inventory or extract that exact Git
source first. Keep all helper sources fixed during the bracket. The no-live guard
prohibits chain/build fixture setup; only temporary synthetic loopback HTTP
fixtures run. Existing consumers, defaults, dependencies and frozen interfaces
are unchanged. No peer module edit, extra agent, worktree or main push.

Full runtime READY/mapping and separate exact execution FREEZE ACKs still precede
services/scenarios. Witness-side view, Worker factory, supervised witnesses, CLI,
real transport/clock and H2/H5/H6 remain pending. The recipe must supply exact
published schema, keep response checking enabled and validate handler behavior.
Agent3 next source-state/sign-time and producer schema/path/lock completeness
review, then fault oracle/finite model. Historical qualified E unchanged;
all32Fcases/GateF NOT_RUN/G locked. No human action required. Publication and
persistent-file lock cleanup are retained in automation memory.
