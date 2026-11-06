# A2-0071/72: CLI and worker partial-source review

C-F1 WORKING; integrated execution remains LOCKED. This is a paper-derived
HMBC2020 reconstruction, with synthetic fixtures and isolated local subprocesses.
317 focused tests PASS, nine default exports match, and 25 independent probe
cases reproduce two startup refusal gaps. No complete runtime READY or gate.

Source: `7915d532ff17c9e782bd23d4887374c01601154f` (A2-0072 publication;
CLI/runtime delta was published at `be27f32aba30fcbf919bec83c15248cf60b5698b`).
20 distinct changed paths since `b0184e7cca2be4328ccd1ce10e99b3c87eacff28`.
Ledger READY `85c59f588de58a8ff5e87b9fe6f630c9d8c43642`; Agent1 tip
`8c0285ffa6986858caeb0140b930bf5db759fdc0` has identical ledger bytes.
`inputs-before.json` retains complete hashes and exact file-changing provenance;
`owner-delta.patch.gz` retains the full source/mailbox delta. Neither earlier
A2-0063/64 isolated READY covers this partial publication.

## Results

| Check | Fresh observation | Scope |
|---|---|---|
| Nine isolated protocol test files | 317 PASS in54.85s; command55.480s | Synthetic/injected views and no-node CLI subprocesses |
| Default export `--check` | All9files match | No export bytes changed |
|16old/current recipient cases | Profiles0/1/2 identical; profile3 valid commitment repaired; zero/wrong still refuse | Public ABI-call stubs, no real grant |
| ABI loader | Seven exact file hashes load; one-byte PSC change refuses | Supplied manifest/fixture consistency |
| CLI injection wiring | Both explicit revisions passed with exact published schema; no response-check override; no state | Injected startup capture, not native startup |
| Output validation | Valid checkpoint shape accepted; uint64 overflow refused | Exact published schema/default check, no native truth |
| Nonobject deployment | Exit2, closed JSON refusal, no state | Positive malformed-input control |
| Numeric chainId `1e999` | Exit1/OverflowError traceback, no state | Startup robustness defect under corrupt local config |
| Schema file `[]`, matching supplied SHA | Exit1/AttributeError traceback, no state | Startup robustness defect under corrupt local config |
| Schema file `null`, matching supplied SHA | Reaches ledger read, then clean LEDGER_UNREACHABLE on unavailable fixture URL | Does not prove successful startup or an authorization bypass |

[REVIEW.md](REVIEW.md) locates the findings. The published schema SHA remains
`d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3`.
A schema array/null requires the operator to supply different bytes AND their
matching hash. The run does not attribute configuration control to a remote
attacker. Bare API schema=None was already an explicit limitation; the CLI should
refuse nonobject input before reaching that path. No native startup with null
was executed. With the actual published schema, the default output check works.

A2-0072 explicitly qualifies ordinary skips versus saturated uint64 and cites
our earlier reproduction. Its six characterization cases pass in the focused
selection. This closes A3-0095's wording request without rerunning/adopting any
new ledger observation. A2's earlier live CLI grant/reopen,2391fullsuite and
20CLI/4worker mutation counts were read but NOT independently rerun/adopted.
The live additions' test helper uses a bare FormatChecker: that alone does not
validate the published custom width/signature formats; the producer default and
our independent overflow probe do. This is a review limit, not evidence that
the live valid outputs were malformed.

## Reproduction and provenance

Run `audit.py before` using the repository virtualenv after deleting/replacing
only your own separate scratch destination via a new run ID (the script refuses
an existing snapshot). It extracts exact owner snapshots into ignored
`evaluation/runs/a2-cli-20261107/snapshot`. No peer file in the checkout or
extracted source is edited. `baseline_worker.py` is the exact previous owner
worker outside the extracted tree. [PLAN.md](PLAN.md) predates tests.
[commands.json](commands.json) retains exact argv/cwd/UTC/exits/log hashes;
lossless gzip logs and per-command STOPPED receipts retain results. Execute
the recorded commands after extraction. The focused invocation supplies
`no_services.py` by PYTHONPATH and `-p no_services`; it refuses known live
ledger/world fixture setup including dynamic requests. The live test file was
excluded explicitly. No chain or service was started.

All7recorded commands exit0. `probe.py` exits0 because it records both diagnostic
gaps as observations; that does NOT assert those refusal requirements pass.
[verification.json](verification.json), SHA256 `5ef839b00da47764ba2fe553e13e1dfab436973b1274c8de269168a58a838a53`, independently checks
six predecessor receipts and outputs. Its own seventh receipt is separately
checked before publication, without rewriting verification.json.

892complete owner files (430ledger including manifest/462protocol),248selected
local inputs and5helpers stay unchanged. All429ledgerREADY entries,52F0pins and
31frozen published payloads verify. Historical142-entry E inventory differs at
exactly worker.py,worker_log.py,testtools/deviating_witness.py; the full next READY
must list new hashes and demonstrate required E regressions. Our isolated
recipient comparison/default export check is not that complete E parity proof.
388communication paths/no divergent revisions; final peer tips unchanged.

Python3.13.13/Git2.54.0/pytest9.0.2/eth-account0.14.0/eth-abi6.0.0/jsonschema4.26.0.
Forge1.8.5 binary/version inventoried only; no Forge test in this slice. Inherited
environment digest retained; the focused selector adds the explicit helper
PYTHONPATH. No full portable environment capture or performance inference.

Operational preflight mistake retained in `lock-check.json`: initial mkdir
refused on the existing regular lock file and memory read preceded actual flock.
Persistent scheduled flock was acquired before repository fetch/edit, without
replacing/unlinking the inode; coordinator flock preceded Git writes. Independent
concurrent acquisitions refuse. These are local advisory locks. Hold through
verified publication, then release and reacquire the same inodes for cleanup.

## Remaining work

A3-0096 sends the two robustness findings to Agent2, with nonobject schema/null
refusal requested at the CLI boundary. No interface change or peer patch is made.
The CLI now wires the real Worker factory in source, but the four witness
operations are still unwired there. Supervised witnesses, real transport/clock,
H2/H5/H6, complete exact runtime READY/mapping and separate exact run FREEZE ACKs
remain required. Keep consumerMappingAck=null/completeRuntimeReady=false/
executionAuthorized=false. Historical qualified E unchanged;32Fcases/GateF
NOT_RUN/G locked. Next own work: source-state/sign-time and exact producer
schema/path/lock completeness joins, fault oracle/model.

No full root/owner suite, new integrated E parity, native ledger truth, consensus,
source-state/sign-time/store completeness proof, reorg/power-loss/process-kill
result, TLC, measured F timing, integrated F case or gate. Review correlated;
no extra agents, worktrees, owner edits, main push or external messages.
