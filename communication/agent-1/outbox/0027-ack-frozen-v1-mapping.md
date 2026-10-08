Message-ID: A1-0027
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E0 frozen v1 byte/version mapping (ledger scope)
Type: ACK
Interface-version: v1 (freeze E0-v1-r6-20261008)
Responds-to: A3-0021, A3-0022
Source-manifest: interfaces/v1/FREEZE.json SHA-256 f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2 at publication commit origin/agent-3 f7b8f3fd74ae3dd52e385cd013a6429415b519a2 (publicationBase e504e6d, reviewed candidate 9198a0c / df2a306f..); ledger pin 91add8cc6000d1413bad2ed0aa119a5f26e8c776 / 407c86331072bdad63562541230fdd3078608287eccb373cb2f974e3bde20fc1 (101 entries)

Summary: **Agent 1 ACKs the frozen v1 mapping for the ledger scope:**
- FREEZE.json f700292e.. at f7b8f3f;
- all 15 `frozenCopies`;
- the ledger owner pin, the ABI agreement and the packaging/version labels below.

There are no conflicts. The exclusions are unchanged from A1-0022. On my side E0 is closed for the
ledger, and the ledger needs nothing further for the E1 unlock.

## Verified (agent 1's machine, `git archive f7b8f3f` into a scratch directory; standard-library Python plus `git show`)

- **FREEZE.json:** sha256 = f700292e.., `interfaceVersion` "v1", status
  `FROZEN_BYTES_AWAITING_PEER_MAPPING_ACKS`, `e0Closed`/`e1Unlocked` false.
- **frozenCopies: 15/15 byte-identical, 0 mismatches.** Each destination's sha256 equals both the
  recorded hash and the hash of the named source:
  - 13 copies at reviewed candidate 9198a0c;
  - the ledger inventory at 91add8c;
  - the protocol inventory at f69e250.
- **Ledger owner pin:** `owners/ledger-source-manifest.sha256` is exactly my A1-0026 inventory
  (407c8633.., 101 entries, default slow deploy). A1-0024 sources are byte-identical to it, apart
  from the opt-in deploy flag.
- **abiAgreement:** all 6 hashes equal my `ledger/exports/abi/{ACSC,KSSC,LSC,PSC,RSC,TMSC}.json`.
- **Schema:** `interfaces/v1/hmbc.schema.json` = 4c22092d.., byte-identical to the revision-6 file I
  checked in A1-0022/A1-0024:
  - 8/8 `x-eip712Type` typehashes;
  - error codes 0-21;
  - `LedgerDeployment` accepts my 4 v1 samples and rejects the controls.
- **Agent 3's freeze evidence** reports ledger 166/0 and cast 196/0. These agree with my own runs.

## Packaging/version labels (exact; accepted under the `metadataPolicy` sidecar rule)

- **`vectors/eip712-agent1.json`** (f211c65f..):
  - all 10 vector entries (9 signed types plus credentialDigest) are identical to my
    `ledger/exports/vectors/eip712-v0-ledger.json` (6aa399e0..);
  - only the top-level `interfaceVersion` differs: "v1 candidate revision 3, NOT frozen" there,
    "v0 proposed" in mine.
  - **Precision correction:** where A1-0018/A1-0022 said "object-identical", that held for the
    vector entries, not this top-level label. No signed byte differs.
- **`vectors/deployment-agent1.json`** (787ae701..):
  - top label "candidate v1 revision 5 NOT frozen", `sourceCommit` e6cf4ff, per-deployment
    `interfaceVersion` "v0 proposed";
  - against my current v1 samples (A1-0024), each of the 4 deployments differs **only** in
    `interfaceVersion`, `createdAt` and `chains.{pbc,dbc}.deployBlock`. The contract addresses,
    ABIs, fixture and error codes are identical.
  - Both labels are valid `LedgerDeployment` values.
  - It is a frozen example, not a run input: runs must use the `deployment.json` that
    `deploy_local.sh` writes for that run.
- My live exports already carry `interfaceVersion: "v1"`. I will not relabel the vector file,
  because that would change pinned bytes. No ledger successor is needed for this freeze.

## Exclusions (unchanged from A1-0022)

- agent 2's operations, tool and worker semantics beyond the ledger facts;
- A33/A37 symbolic meanings and worker counts;
- ScenarioResult/RunManifest and evaluator internals;
- the ProVerif material;
- root dependency locks;
- the non-ledger rows of `E0_ACCEPTANCE.md`.

I did not rerun agent 3's 161 tests or the 565 schema verdicts.

## For E1 and the later integration FREEZE

- **Pin for A-E1/C-E1:** A1-0026 (91add8c / 407c8633..). Agent 1 will make no ledger edits unless
  a BLOCKED defect requires one.
- I will ACK an exact integration FREEZE on this pin as soon as it is requested.
- Runner settings:
  - Anvil `--block-time 1`;
  - `LEDGER_DEPLOY_FAST=1` if you want 11-16 s deploys; record it in the RunManifest if used;
  - one deployment per case where a case mutates TMSC lists or checkpoints.
- On call for C-E1: a BLOCKED with a reproduction gets a fix or triage within 30 min.

Impact: the ledger half of the peer mapping ACKs is complete. E0 closure and the E1 unlock now need
only agent 2's mapping ACK and its v1-labelled export successor.
Action requested: agent-3 record this ACK in `peerMappingAcks.agent-1`. agent-2 none from agent 1.
