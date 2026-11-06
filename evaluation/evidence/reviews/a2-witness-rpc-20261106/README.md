# Partial witness RPC review — 2026-11-06

C-F1 remains WORKING; integrated execution remains LOCKED. Paper-derived
HMBC2020 reconstruction, synthetic inputs. Publication
`0e58f1da659f48ffd39b6af138acf194b0ae111f` carries A2-0067/0068;
the new production file last changed at
`86521cd9098aa6ad6ad86c385af2ea6ae4f5143f`. The 14-path delta from
`0297adb6e784b9667befbc6330e1dfcb3ec81e3e` is retained losslessly in
reviewed-owner-delta.patch.gz. This 446-entry inventory is coordinator review
provenance, not an owner source/runtime READY.

- Fresh 222 focused tests PASS: 26 new view tests plus 196 affected witness-service
  tests. Final pytest 2.45s / command 2.669s, exit 0. All 43 owner mutation controls
  are independently rerun and detected after a passing unmodified control;
  command 23.612s, exit 0. Default nine export files match, exit 0.
- Fourteen manual raw-RPC controls pass. Thirteen diagnostics reproduce nine
  gaps: four transaction shapes escape as AttributeError; three noncanonical
  quantities and two permissive ABI encodings are accepted. Four other suspicions
  are refuted. See [REVIEW.md](REVIEW.md). No incorrect authorization was shown.
- All 446 owner files, 248 selected local inputs and five helpers stay fixed in
  the final bracket. The 429-entry ledger READY, 52 F0 pins, 31 frozen payloads,
  seven copied ABIs and four interface fixtures verify. The old 408-entry owner
  READY verifies at its own exact source/publication; only its state README
  differs at this later partial source.
- Final peers remain A1 `8c0285ffa6986858caeb0140b930bf5db759fdc0` and A2
  `0e58f1da659f48ffd39b6af138acf194b0ae111f`; 381 communication paths have no
  divergent/ambiguous revisions. Their exact file-changing commits and hashes
  are retained in communication-provenance*.json and inputs-before.json.

Exact argv, cwd, UTC, elapsed time, exits and output hashes are in commands.json;
raw outputs are lossless *.txt.gz. Eleven recorded commands exit 0; verification
checks its ten predecessors. verification.json SHA256
`74f2e5c04f07de3f7ef5023cc7e8830fea0faf1b0e1f2d651bcc1bf2983eb629`.
Python 3.13.13, Git 2.54.0, pytest 9.0.2, jsonschema 4.26.0,
eth-account 0.14.0 and eth-abi 6.0.0; executable and source pins are in
inputs-before.json. Inherited environment plus explicit path overrides is
recorded, not a complete environment capture. No random fault seed is used.

The first verifier draft anticipated twelve gaps; observed results showed nine.
Only verify.py's count assertions changed. The initial inventory, probes and
222-test output are retained; verification-helper-amendment.json records both
helper hashes. A new inventory and repeated identical probes/focused tests then
establish the final fixed-helper bracket. No target/probe expectations were
changed to hide a failure. An intermediate user-facing count of 373 tests was
wrong and corrected to the actual 222 before publication.

Reproduction: audit.py before creates a fresh ignored scratch snapshot; execute
the final probe, focused pytest, mutation and export argv in commands.json, then
audit.py after and peers and verify.py. record.py refuses existing output labels;
use a fresh evidence destination for a new run. audit.py's before mode refuses an
existing scratch directory. The recorded first and final inventories explain
the preserved initial files. No-live selection guards prevent fixture-driven
chain/build startup. New owner live tests are read/hash-pinned only; neither their
37/38 counts nor the idle-chain staleness observation is independently adopted.

No full owner/root suite, live node, deployment, service, new E parity, native
source-state/sign-time proof, reorg, timing, TLC, F case or gate result. The review
is correlated with the same model family. Historical qualified E is unchanged;
all 32 F cases/Gate F remain NOT_RUN; G is locked. Full runtime READY/mapping and
separate exact execution FREEZE ACKs still precede integrated services/scenarios.
No peer/runtime/interface/default/dependency change or human action is required.
