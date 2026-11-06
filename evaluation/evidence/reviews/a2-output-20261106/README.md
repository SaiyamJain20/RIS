# A2-0064 output-validation delta review — 2026-11-06

Classification: **synthetic tested reconstruction/extension source review**.
C-F1 WORKING; integrated execution LOCKED. Paper-derived HMBC2020 reconstruction.

Source `c138185428ebe572c86cdc42985b340a262aa8aa`, READY publication
`f2c86ad868c3c6c0799f2b610ad55f5cb1a7306f`; manifest
`protocol/evidence/af2-source-ready-2/MANIFEST.sha256`, SHA-256
`016ffd0870e3b9bfd2b8b297c8c977bcfe29ce687d0a54b548b901c52e8b9cbf`.
All408entries equal the entire tracked protocol source tree, publication and
scratch bytes. Exactly four non-evidence paths differ from A2-0063: adapter_v2.py,
test_adapter_v2.py, new test_adapter_v2_output.py and run_adapter_v2_mutants.py.
No owner source is merged into the coordinator checkout.

## Fresh verification

- Isolated protocol: **2046 PASS / 201 SKIP / 199 DESELECT**, exit0, pytest32.04s
  (command32.385s). The new19output tests are included. The skips remain the
  owner's out-of-scope schema-review cases; excluded IDs/reasons are retained in
  regression-selection.json. The same explicit dynamic-fixture/build/catalog
  selector and hard setup guard from the previous review are reused unchanged.
- Evaluator schema tests: **172 PASS**, exit0, pytest27.23s; four named test files
  in commands.json. Independent public API/format controls: **21 PASS**.
- Changed owner adapter runner: **58/58 mutations detected**, unmutated control
  PASS, exit0, command117.905s. Equivalent A59 remains explicitly excluded.
  Other owner runners/full2245PASS count were read, **not rerun or adopted**.
- Default exporter check: all9files match, exit0.
- All408owner entries,248selected evaluator inputs and four review helper scripts
  unchanged across testing.429ledgerREADY entries,52F0pins,31frozen publication
  files and four copied fixture sources verify. Of142historicalEentries exactly
  the two previously declared carried files differ; D50 binding remains fixed.
- 374communication paths/no divergence; final reviewed peers A1`8c0285f` and
  A2`f2c86ad`. Exact file-changing commits/hashes are in inputs-before.json and
  communication-provenance*.json. Verification SHA-256 `716b93f44c2baf5ed479c00a803089b8a99f7d77f55d85d24007d96531228cd0`.

The new response check closes the arbitrary-dict output limit **when the exact
published schema is supplied and check_responses is enabled**. Valid results
remain intact; invalid/wrong-operation results become the fixed generic failure.
The check enforces custom uint widths and canonical signatures. Bare jsonschema
FormatChecker does ignore these formats, but the evaluator's existing custom
checkers already enforce them; independent controls verify both implementations.
No evaluator code or shared schema change was needed.

Both `schema=None` and `check_responses=False` still bypass output validation.
The runtime recipe must supply the exact schema and keep the default enabled
check. Producer user-key-ref/evidence-path remain annotations; the evaluator
refuses the sampled invalid strings. These controls demonstrate shape/encoding,
not actual signature recovery, source-state truth or deployment membership.
See REVIEW.md for exact scope, code review and operational exception.

CLI/real chain and Worker wiring/supervised witnesses/real transport and clock
remain missing. Full runtime READYs/mapping plus separate complete exact
source/tools/config/run FREEZE ACKs precede services/scenarios. No service,
newEparity, full owner/root rerun, TLC, timing, Fcase or gate result. Historical
qualified E unchanged;32Fcases/GateF NOT_RUN/G locked. No human action required.

## Reproduction and retained evidence

`audit.py before` creates a fresh ignored snapshot and refuses an existing one;
`after` verifies all source/helper/evaluator pins; `peers` verifies fetched branch
provenance. Exact argv/cwd/UTC/exits/elapsed/raw and gzip hashes are retained in
commands.json. The verification command's full Python source is retained there.
The test environment selects PYTHONDONTWRITEBYTECODE=1, PYTHONPATH as scratch
protocol plus this evidence directory and RIS_REVIEW_DESELECTION as this review's
regression-selection.json. Other environment is inherited; environmentSha256=null
is **not** a full environment capture. All10recorded commands exit0; raw/gzip
hashes of the preceding9commands are checked by the final verification command.

Tools: Python3.13.13, Git2.54.0, pytest9.0.2, jsonschema4.26.0, eth-account0.14.0;
exact executable/version strings in inputs-before.json. Fixture identities are
synthetic; checkpoint/signature shape controls use the published v2 signing vector.
Owner tests and mutants remain correlated. No original-paper vulnerability claim.

Operational: initial scheduled-lock inode exclusion was not proved because the
startup helper replaced the prior file on stale PID metadata. Current exclusive
flock held since before project work; coordinator lock acquired before Git writes.
The mistake and prescribed persistent-file-flock recovery are retained in REVIEW
and automation memory. Publication/remote verification and cleanup receipts are
recorded in automation memory, outside this tested source bracket.
