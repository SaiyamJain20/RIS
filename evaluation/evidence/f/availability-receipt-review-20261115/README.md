# M2/M6 availability receipt review — 2026-11-15

Classification: source-and-receipt review of prior tested reconstruction
results. No cases, services, or measurements were run in this review. M2 has
retained aggregate JSON. M6's test source is available at its pinned revision,
but its claimed three-run stdout and exact invocation are not retained here.

## M2 — virtual-transport sweep

The retained script `evaluation/measurements/availability_sweep.py` describes
four real witness objects with durable SQLite stores and EIP-712 signing, but
places them behind `VirtualTransport`. Its module docstring explicitly excludes
real network, clock, process, or ledger measurements. The sweep enumerates all
16 muted subsets and runs each five times (80 trials); the retained JSON stores
the set of outcomes, number of runs, median/max host wall time, and the virtual
finish time/signature count. It does not store each trial's individual output.
The delayed-reply ordering case is a separate single execution, not a five-run
sample.

Against protocol snapshot `55f180e15d73825870d3326a3edb817824b3f265` (tree
`0e59256bd859d347ad416a5ab77099a9a9f2809e`), the JSON records success for 0 or
1 muted witness and failure at the 10,000 virtual-ms collection deadline for
all 2-, 3- and 4-muted subsets. All five outcomes are summarized per subset;
the JSON is not a row-per-trial transcript. Delayed replies of 400/300/200/100
virtual ms produce a 3-signature collection at 300 ms. This supports a bounded
availability result for the virtual schedule. It says nothing about real
network timing or general liveness.

## M6 — local real-process tests

The test source
`protocol/tests/test_witness_process_transport_live.py` at the same protocol
snapshot describes four local `witness_main` processes, two local Anvil nodes,
and the real KSSC from ledger `85c59f5` (tree
`36a868305d67c8f546e6bde558ceb8e356962819`). The four test functions cover:

1. Three process signatures accepted by real KSSC.
2. Two SIGSTOPed processes causing a classified timeout that waits for the
   pool's timeout.
3. One SIGKILLed process leaving three signers and an accepted certificate.
4. Restarting a SIGKILLed witness under a fresh supervisor and checking its
   durable pin.

The source header explicitly excludes second-host behavior, power-loss
durability, consensus, readiness before the first request, decision/receipt/
governance collections and load timing. It also says tests skip when Foundry or
the pinned ledger is missing, so a zero exit alone is not sufficient: the
reported `4 passed` count matters.

The existing Agent-3 report says this unchanged test file was run three times
with exit 0 and 4 passed each time (58.8 s, 78.2 s and 59.1 s total), and retains
four per-scenario call times for each run. This review confirms the source path,
source hash and described assertions, but the exact command line, environment
capture, per-run stdout/stderr, and test-result files are absent from the
checkout. Therefore those outcomes remain reported prior local runs, not
re-executed or independently auditable results in this slice. They use one
host, local processes/Anvil and synthetic keys; they do not demonstrate a real
network or ledger consensus.

## Retained artifact hashes

| Artifact | SHA-256 |
|---|---|
| M2 availability script | `5e6ab7e7a8a0ba2e9d162dc7bc434b62aa577a7a2b9c3d18d072d2d168d668c4` |
| M2 aggregate JSON | `45ddc99d907be0c88f760b97f91f69a6b95b3f3a9c12e4d8f97f5895c402c692` |
| M2/M6 measurements README | `06de6efdab54a4fe368ffd34fab7a27bd203765dcfdc45e231692bfcf69339ef` |
| M6 pinned protocol test source | `5b835b552c5fd74d501ff19e05d9e32429a0a078c853a4370df60ecec412edb4` |

The M2 source reads the extracted protocol tests/helpers and writes aggregate
JSON; it does not start a service. No live M6 processes were started during
this review. Plan DRAFT, all 32 F cases NOT_RUN, Gate F NOT_RUN, G locked.
