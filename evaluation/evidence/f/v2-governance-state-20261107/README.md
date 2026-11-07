# Governance supplied-state/window/approval verification

C-F1 remains WORKING. Isolated internal evaluator extension only; no integrated
execution is unlocked. This is a paper-derived HMBC2020 reconstruction/extension,
not an authors-implementation reproduction or paper vulnerability finding.

`evaluation/governance_state_v2.py` checks one stored GovernanceAction signature
against independently selected context/owner/ABI pins and supplied raw PBC state:
exact next nonce, witness-set version, ADD/REMOVE/SET preconditions, exact canonical
TEST-ONLY approval tuple, and `timestamp < expiry <= timestamp + maxGovernanceTtl`.
The public getter supplies the TTL; no fixture default is substituted. Every
block/call is selected by exact hash/callee/calldata; canonical bytes, complete
capture usage and no caller mutation are checked. Existing consumers, frozen
interfaces and dependencies remain unchanged. See PLAN.md and REVIEW.md.

The approval list is a caller-selected assertion, not authenticated witness
policy/configuration. The PBC timestamp is a supplied retrospective observation,
not signature-bound actual signing time or proof of historical latest head.
Both `signTimeEstablished` and `latestHeadEstablished` remain false. One stored
signature never establishes a quorum. Fault/clear interval interpretation and
complete signed history/digest coverage remain outside this per-signature API.

## Commands and controls

Every recorded command has an immutable `*-command.json` with exact argv/cwd,
UTC, elapsed time, exit and output hash, plus a deterministic gzip log. The
wrapper `record.py` uses owned bounded process groups; direct-child STOPPED
receipts remain in ignored `evaluation/runs/v2-governance-state-20261107`.
Initial RED/GREEN were unbracketed author trials:69 missing-module failures
(all69 verified), then69 passes. Two review controls were added before the final
input bracket. The mutation helper's unexecuted syntax typo was fixed before
freeze. Product source has not changed since first GREEN.

Seven deliberate in-memory bypasses target nonce, state witness version, ADD
existence, ADD tombstone, REMOVE/SET existence, approval match and expiry. Each
original rejects its invalid input; its mutant accepts it and still accepts a
legitimate action. These are evaluator sensitivity controls, not owner-module
mutations or exhaustive coverage. Test signing uses immutable published typed
layouts and synthetic TEST-ONLY witness keys, not protocol/ledger internals.

## Provenance and limits

`inputs-before.json` and `inputs-after.json` bracket all selected local runtime
inputs and all899 freshly re-read owner blobs inherited from the exact prior
source manifest. The complete carried tracked tree is compared to initial HEAD;
this covers historical evidence and fixtures read by root tests. Source/tool/
environment-digest/frozen-file pins are retained. Documentation/shared handoff
edits happen after this runtime bracket; no claim of detecting intermediate
write-and-restore events. Approval-fixture contents are arguments exercised by
synthetic tests, not an authenticated owner fixture from a live deployment.

`communication-before.json` / `communication-final.json` retain exact branch,
file-changing commit and SHA256 provenance for all fetched communication paths.
`owner-provenance.json` records the spec/Governance/TMSC/service source comparisons.
A1 remains8c0285ffa6986858caeb0140b930bf5db759fdc0;
A2 remains67111f580b6ecfd1b924f3cd1a863981180822e1. No new READY/ACK or owner runtime
result is adopted. A3-0096/0097 requests remain open; complete runtime/mapping and
separate exact complete source/tools/config/run FREEZE ACKs precede services.
The three previously recorded historical E source mismatches remain unresolved;
no new E parity is claimed. Historical qualified E is unchanged; all32 F cases
and Gate F remain NOT_RUN, G locked. No human action requested.

Startup ordering was imperfect: an initial mkdir failed on the existing regular
lock file, then memory/skills were read before successful persistent-file flock.
No repository read/fetch/edit preceded acquisition. No lock inode was replaced
or unlinked. Both original locks exclude independent concurrent acquisition;
see startup-lock-note.json and inputs-before.json. Locks stay held through
independent remote publication verification, with final cleanup in run/memory.

No RPC/chain truth, witness misconduct, actual validation/sign time, latest head,
ancestry, store/export/producer completeness, native death, persistence/durability,
consensus, branch coverage, crypto performance, TLC, F scenario or gate result.
Review is correlated author review under the no-extra-agent instruction. Next:
governance history/acquisition with explicit unsigned observation/approval
provenance; remaining AccessDecision/GrantReceipt state duties and exact producer
schema/path/lock completeness; independent fault oracle/finite model.

## Final observed results

| Command label | Observed result | Exit |
| --- | --- | --- |
| red | 69 missing-module failures | 1 expected |
| green | 69 passed | 0 |
| green-review | 71 passed in 4.16s | 0 |
| mutants | 7 deliberate bypasses detected / 7 valid controls pass | 0 |
| focused | 315 passed in 49.76s | 0 |
| root | 2721 passed in 580.55s; command580.863s | 0 |
| preflight/postflight | 899 owner /256 selected local /5 helper inputs unchanged | 0 |
| fetch-final/peers-final | 392 communication paths, no divergence; peers unchanged | 0 |
| verify | 10 predecessor command receipts verified | 0 |

All8497 carried tracked blobs match baseline bbaaff8dd3f3f45926779f0b73f71cf8cf8a9c05;
canonical path/SHA256 map digest3efbcf8d8f64c5c0744e2339e6b803da7e2e2c25bd608ee37a5a2e900dedeb87.
All52 accepted F0 pins and31 frozen payloads match. Input bracket SHA256 BEFORE:3edc9b9db5b8168f72caa869418d76607555698f9eb18972ac46534e47058a4a;
AFTER:041ebd851f1285b3876eec414e5f23e09796b3a76b233c55305b596a5446f901. Verification JSON SHA256 ea45af3dbf110cca0d8cac0ff6212bfae8cac9abe5f4bb6b62f12e4e523170e8 checks10predecessor receipts;
its own11th receipt/log and all core artifacts were independently checked without
rewriting verification.json. Python3.13.13/Git2.54.0/pytest9.0.2/eth-account0.14.0/
eth-abi6.0.0/jsonschema4.26.0. Full tool strings and executable are in inputs-before.
The focused and root runs partly overlapped; elapsed times are test execution
records, not a benchmark. No coverage measurement or performance claim.
