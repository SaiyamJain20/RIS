# C-F1: context-bound signature verification

Added isolated `evaluation/certificates_v2.py` for the HMBC2020 paper-derived
reconstruction's accepted F extension. This is synthetic extension implementation
test evidence, not a finding about the paper, a measured F schedule, an integrated
E regression, module source READY acceptance or a passing research gate.

All131 focused tests pass after131 RED failures against unimplemented stubs.
The helper independently fixes the four message type layouts/domain names and
version, reproduces all six frozen EIP-712 digests and signer lists, and rejects
altered signed fields/domains, noncanonical signatures, wrong witness versions,
unknown/duplicate/out-of-order signers and incorrect counts. It supports explicit
single-witness and q2 negative-control checks; q2 never passes a requested q3 check.
The carried E version1 control is freshly signed using a public synthetic key.

Every declared checkpoint retry report is recovered against its configured index:
pinned single refusal, consistent reports, inconsistent reports and late arrivals.
All12 frozen wire examples are checked; every report path has a mutation control.
The pinned refusal requires the original request's explicit selected index.
The helper checks declared reports only, and separately exposes certificate
verification. Zero reports checked is not a success-certificate verdict.

Fresh full root evaluator suite: **1857 passed in396.51s, exit0** (396.802s
command wall time). The195 local source/schema/vector/config inputs match before
and after the suite. See `inputs-before.json`, `verification.json`, `commands.json`
and retained output. Versions: Python3.13.13, pytest9.0.2, eth-account0.14.0,
jsonschema4.26.0, Git2.54.0. This is the root evaluator suite selected by
pyproject.toml, not the owner protocol/ledger suites or a live integrated gate.

Fresh fetch attempts failed SSH publickey authentication. The exact cached refs
are Agent1 `aef3daa5ebbe434f97b016719f8762d4aaf09441`, Agent2
`5639e8f638645acf0bf122109f8bae2ffc2b6fc4` and remote-tracking Agent3
`2f2af3ca7fd9b9808a8926589b07a6715323e033`. All344 cached communication paths
were reviewed by file-changing ancestry with no incomparable-content conflict.
All418 ledger manifest entries,142 historical protocol entries,52 F0 pins and
14 published v2 payloads verify. No owner code or suites were executed or adopted.
Latest cached owner outboxes remain A1-0110/A2-0058, design-freeze ACKs only.
Current remote state remains unverified. See `fetch-failure.json`; raw failed
fetch output is retained losslessly as gzip with raw/compressed hashes in the
command index. No credentials, remotes or authentication configuration changed.

The helper requires caller-supplied chain/contract/witness/version/count context
from independently anchored observations. Correct recovery authenticates bytes
to configured keys; it does not prove state truth, domain-to-role wiring, runtime
expiry, nonce progression, store history, process isolation, arrival completeness,
timing, actual quorum policy or transaction acceptance. Anchored B/getters/wiring/
fixture reconstruction and exporter history/orphan/WAL/native joins remain next,
before the independent fault oracle/model and separately ACKed execution plan.
See `PLAN.md` and `REVIEW.md` for exact scope and author-review limitations.

Existing E consumers, schema validators, dependencies, owner modules, frozen v1,
all proposals and the published v2 payloads are unchanged. Qualified historical E
remains unchanged; all32 F cases and the F gate remain NOT_RUN, G locked. No live
F service/scenario, new gate, peer edit, extra agent, worktree, deployment or main
push. The earlier local6db8959 checkpoint is preserved. Publication remains
blocked until repository SSH authentication is restored; local notices are not
delivered by a failed push. Exact commit/push/lock cleanup is in automation memory
and its external run record.

Reproduce in the existing environment from the repository root:

```sh
.venv/bin/python -m pytest evaluation/tests/test_certificates_v2.py -q
.venv/bin/python -m pytest -q
```
