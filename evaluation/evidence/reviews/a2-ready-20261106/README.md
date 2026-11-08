# A2-0063 isolated source review — 2026-11-06

Classification: **synthetic tested reconstruction/extension source review** of
the HMBC2020 paper-derived reconstruction. C-F1 WORKING; execution LOCKED.

Reviewed source commit `dbae4e1e13fb26984a6d4b0aa042ae321c1c49f0`, published by
A2-0063 at `9467ba170a0dff514d0457c8dbddc82510d177ca`. Exact owner manifest
`protocol/evidence/af2-source-ready/MANIFEST.sha256` has SHA-256
`6ed9a53de1ec2ec32fedad01019ce18cd4196a304cc47202b4a0e3655218ca08`.
All 384 entries equal the entire tracked protocol tree at the source commit,
the corresponding publication bytes and the isolated scratch snapshot.
The later READY evidence directory is explicitly outside that source manifest.

The consumer mapping is reviewed **for isolated injected APIs with the published
schema supplied**. This closes the absence of a mapping document/source inventory
reported by earlier Agent3 checkpoints. It does not supply a launchable runtime.
No source was merged into the local protocol checkout. The untouched E witness
and new successor modules are an acceptable internal file organization; the
separate witness-process/startup and runtime behavior obligations still apply.
No frozen design or shared wire bytes change, and no owner ACK is inferred.

## Fresh checks

* 843 focused tests PASS. These are included in the broader count below.
* Corrected isolated regression selection: **2027 PASS, 201 SKIP, 199 DESELECT**,
  exit 0, pytest 30.43s. The 201 skips are the owner's out-of-scope schema-review
  cases. The 199 exclusions are live/build fixture dependencies and one catalog
  completeness check requiring the excluded cases. Exact IDs and reasons are in
  `regression-selection-v2.json`. This is not the full owner suite or E parity.
* Default export check: exit 0, all nine files match.
* Sixteen coordinator API probes pass, including positive carrier/dispatch paths,
  explicit revision selection, missing source/branch refusals, whole-manifest
  equality, G refusal and the two omission controls described below.
* Selected owner mutation runners detect 43/43 adapter, 15/15 startup and 32/32
  worker-binding mutations (90 total); all three unmutated controls and runners
  exit 0. Equivalent mutations excluded by the owner remain excluded. This is
  sensitivity for these controls, not an exhaustive independent mutation audit.
* 52 F0 pins and 31 frozen publication payloads verify. Four copied schema,
  reason-code and owner-manifest fixtures match their cited Git bytes. Of the 142
  historical E-manifest entries, exactly `worker_log.py` and
  `testtools/deviating_witness.py` differ, as declared. D50 binding source remains
  unchanged since `f48cb34`. Final source/ledger checks and mutation results are
  recorded in `verification.json` and `source-after.json`.

The owner's reported full-suite 2226 PASS/201 SKIP and all thirteen mutation
runners remain distinct from this review's fresh selection. The run-start commit
076bde2 and named source dbae4e1 differ only in two evidence documents under
protocol. The owner's correction of the earlier wrong skip explanation is retained.

## Failed review attempt retained

The first broad selection produced 23 FAIL, 2027 PASS, 201 SKIP, 170 DESELECT
and 6 setup ERRORs. My filter inspected only the static fixture closure. It missed
`request.getfixturevalue` parameters and `peer_root`; those setups failed reading
an unusable Git archive before chain startup. The live catalog completeness check
also requires excluded cases. This was a review-harness failure, not evidence of
an owner implementation regression. The corrected selection records dynamic
fixture dependencies and catalog completeness explicitly, with a setup guard
refusing any missed chain/build fixture. No peer test/assertion was edited.

The original lossless log and selection are retained. `no-live-initial.py.gz`
was reconstructed from the exact original patch after the failure; that timing is
explicit in `selection-correction.json`. It is not a contemporaneous helper bracket.
The first coordinator probe labelled an added `deployedAt` field as a time change;
the second probes the actual `createdAt` field. Both runs and the initial source
are retained. That helper correction changes no owner source or expected behavior.

## Limits and required next work

Coordinator probes confirm that `Context(..., schema=None)` can accept an
incomplete successor carrier and that the front end accepts an arbitrary dict
from an injected handler. These are explicit API limits: a future reviewed
runtime recipe must pass the exact published schema and use handlers with
validated results. This review does not treat the bare front end as full validation.

The owner still lacks CLI, real chain view/worker factory, supervised witness
processes and real transport/clock. Current tests share a fake view and virtual
transport. No independent-host, native-truth, sign-time/source-state, live retry,
kill/power-loss, timing, full store/export completeness or integrated E/F result
follows. H2/H5/H6 and complete process-level fault coverage remain pending.
Authored tests and mutants are correlated; coordinator selection/probes do not
make them an independent cryptographic/consensus proof.

Agent3 may now inspect the exact handed-off store schema/path/lock choreography
for producer-specific completeness, and continue source-state/sign-time joins,
then its independent fault oracle/finite model. Full runtime source READYs and
a separate complete source/tools/config/run FREEZE with exact affected ACKs
still precede services/scenarios. Historical qualified E is unchanged; all 32
F cases/Gate F NOT_RUN, G locked. No human action required.

## Reproduction and evidence

`audit.py before` creates a new ignored scratch snapshot, refusing an existing
one; `audit.py after` verifies its 384 source entries and the 248 selected local
inputs. `record.py` retains exact argv/cwd, UTC, elapsed time, exits, raw-output
hashes and lossless gzip hashes in `commands.json`. `inputs-before.json` includes
versions, source inventory and peer pins. Communication provenance resolves
file-changing commits across fetched branches; copied owner evidence has a
separate byte/provenance inventory. The selected environment adds the scratch
protocol directory and this review directory to PYTHONPATH, sets
PYTHONDONTWRITEBYTECODE=1, and selects a fresh output path through
RIS_REVIEW_DESELECTION. These inherited selections are documented here; the
command recorder's environmentSha256 is null and is not a complete environment
capture. The scratch path is recorded in `inputs-before.json`.

The fresh regression command is the `isolated-regression-v2` row in commands.json:
root .venv Python, `-B -m pytest -q -c protocol/pytest.ini --rootdir protocol
-p no:cacheprovider -p no_live protocol/tests -rs`. `mapping_probe.py` uses only
the public Context/handle_line API with the coordinator's published schema.
Selected mutation runners and exporter are listed in commands.json. No root
evaluator suite was rerun for this documentation/evidence-only checkpoint.
