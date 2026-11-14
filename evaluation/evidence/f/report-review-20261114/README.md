# RQ2-F partial report correction and evidence review — A3-0129

2026-11-14. Paper-derived HMBC2020 reconstruction; synthetic keys/fixtures; correlated author
review. **Plan DRAFT; all 32 cases NOT_RUN; Gate F NOT_RUN; G locked. No services started.**

## What changed

The report now distinguishes fixed-slot quorum agreement, store death rules, honest service
validation, ledger submission and native transition reachability. It has a claim-to-evidence
table and a fuller residual trust matrix. Prior measurements remain prior measurements.

S2-0024 at agent-1 `73fec05c18e8de050b844879c7835ca6e9dfdd09` correctly points out my
A3-0121 error: a grant may kill an ALLOW pin at the store API, but the honest service refuses
`REPLAY` before reaching the store once the nonce is consumed. Its decision path passes only
`overtaken-decision-sequence`. Correcting my report requires no protocol or oracle-code edit.
The oracle currently checks the more permissive store rule, not all service validation.

Classification: **tested reconstruction result** for the four probes below; **ambiguity** for
SPEC's permanent single-signing shorthand versus accepted F0 live-generation rules. Neither is
an HMBC vulnerability. The finite-model results and deliberate mutations retain their original
scope and classification. S2-0024 is a proxy's reading, not agent 2's confirmation or execution ACK.

## Fresh verification

`command.json` records exact argv, cwd, UTC start/end, exit 0 and script/output SHA-256.
`review.py.txt` is the reproducible driver. It runs with root `.venv/bin/python -I` on a disposable
`git archive 9d44754f7db364e4c39150c699b1e38bedded559 protocol` extract. That exact protocol
subtree is identical to candidate `55f180e15d73825870d3326a3edb817824b3f265`.

- **90 passed, 7 deselected, exit 0** from the unmodified owner files
  `tests/test_witness_service_decision.py` and `tests/test_witness_state.py`. The seven excluded
  cases spawn crash-test child processes and are outside this strictly offline selection.
- **4/4 composite probes match expectations**, using real WitnessService, real SQLite WitnessStore,
  real synthetic EIP-712 signatures and the owner's DView injected ledger fixture:

| probe | expected / observed | state evidence |
|---|---|---|
| ALLOW then proposed DENY after consumed nonce | REPLAY | store unchanged |
| ALLOW then DENY, same live sequence, no grant | CONFLICT_PINNED | store unchanged |
| ALLOW then DENY after sequence 4->5, no grant | SIGNED | one supersession, sequence death |
| DENY then ALLOW after sequence 4->5, no grant | SIGNED | one supersession, sequence death |

The changed results across sequences are scripted input states. They do **not** establish that
those evaluations can arise from actual monotone PBC/DBC histories. There is no native grant,
real checkpoint advance, network, Anvil, adapter process or F matrix verdict in this run. Four
single-witness traces do not establish a q=3 certificate or whole-system agreement.

`review.json` contains outcomes and tool versions: CPython 3.13.13, SQLite 3.47.2, pytest 9.0.2,
eth-account 0.14.0, eth-abi 6.0.0, jsonschema 4.26.0. No package/dependency was changed.
The driver refuses subprocess creation and socket connect/bind, except the exact read-only
`file -b <executing-python>` request used by PyCryptodome's architecture detection. The final
run recorded that one command and zero blocked attempts. This guard is evidence about this
driver's exercised paths, not a general sandbox proof.

All **2,262 owner files** match the exact Git archive and remain unchanged across the final
test/probe command. `owner-source-hashes.json.gz` contains their SHA-256 map; its uncompressed
digest is in `review.json`. `provenance.json` records source/tree/archive hashes, peer-message
hashes/file-changing commits, fixture, interpreter context and branch tips. No peer module,
shared interface, frozen evidence, dependency lock or active plan JSON was edited.

## Failed verification attempts retained

These are reviewer harness failures, not product defects:

1. `first-attempt/`: exit 1 during crypto import. My guard blocked PyCryptodome's read-only
   `platform.architecture()` subprocess. The final guard permits only that exact command.
2. `second-attempt/`: exit 1; 90 passed / 7 failed. The overbroad selection included seven
   process-spawning crash cases. The guard refused them; no child or service started.
3. `third-attempt/`: exit 1; same 90/7 because absolute `--deselect` paths did not match pytest's
   collected node IDs. Name-based `-k` selection excludes exactly those seven in the final run.

Original scripts, logs, command receipts and generated results are retained (large JSON results
are losslessly gzipped). Two exploratory reads of the checkout's protocol paths failed because
the new owner F runtime is not integrated into this checkout. Review switched to the exact
archive; the stale local module was never used as the current protocol source.

## New peer publications and remaining work

Final inspected tips: agent-1 `f25eae1b71089576e2bb2ff33ae7290a62ec4561`, agent-2
`9d44754f7db364e4c39150c699b1e38bedded559`; own starting checkpoint `ae7635e616b1c924c3c074526b1274945debade0`.
Read A1-0130/0131 and S2-0024/0025/0026, plus current owner/proxy STATUS/HANDOFF. Their
exact hashes and file-changing commit provenance are recorded separately.

S2-0025's delta source is agent-1 `37ca31c80ab9a81956647428435addb1802cb370`, protocol subtree
`7566f63d693afe8fa88ab7cc69872082d58d88db`. It reports 40/40 K1 detections, 40/40 controls,
and 3,226 passed / 201 skipped on its host. **Those are proxy-reported results, not rerun or
adopted here.** No claim that K1 is closed on Agent 3's host follows. The old candidate still
has the measured 29/40 limit. Do not mix the two source revisions.

S2-0026 is a useful review of the draft, not an execution ACK. Before a later exact FREEZE:

- Review/reproduce the new delta on this host, including 40-run mutant/control and source brackets.
- Resolve protocol publication provenance explicitly. Preserve current origin/agent-2 ancestry
  enforcement and candidate pins while the proxy source is under review; merely keeping that
  candidate does not reject the new delta. A subtree hash identifies bytes but does not grant
  ownership or supply a missing ACK. No proxy ownership exception is inferred here from a
  peer's account of another conversation.
- Specify exact adapter argv/schema flags/ABI paths per case, distinct fresh chain/state dirs,
  validated pid-file process controls, snapshot-lock choreography and stop/restart rules.
- Preserve F-16..18/F-31 virtual-view limits. G2 is an RPC-view wrapper in a real witness process,
  not a second chain/node, fork or reorganisation implementation.
- Join per-digest signing-time observations and supersession evidence to the independent oracle;
  numeric/grant/receipt provenance still needs validation. Hold no exclusive snapshot lock across
  signing; snapshot the non-cooperative worker only with no operation in flight.
- Implement/review remaining runner stages and obtain the required exact owner confirmations and
  authorized execution FREEZE ACKs before services or cases. S2-0024/0026 and A1-0129 do not supply them.

Full evaluator regression was not rerun for this documentation/evidence slice. The previously
recorded A3-0128 2,978/14 counts remain historical results, not new checks. The next permitted
slice is offline K1-delta/runner/oracle review; no current human action is required to do it.
