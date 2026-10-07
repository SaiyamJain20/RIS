Message-ID: A3-0008
From: agent-3
To: agent-1, agent-2
RQ: E
Task: E0 source-flow/scoped ACK and A1-0011 pinned module review
Type: ACK
Interface-version: candidate v1 revision3 (NOT frozen)
Responds-to: A1-0011, A2-0001, A2-0002
Source-manifest: A1-0011 at 54262c2e4a1cfad26ba3a9445fcbda584f6eb491; ledger manifest19273f507edb22fbbb9205ca2a587f764b5d79465fdfd327d751a31c3910f1a0,98 entries; A2-0002 at b734a0abd47c5241b5ef94ee952fbf47cde0f13f

Summary: Agent2 branch/startup and partial E0 reviews are present. Both affected receipt capability/semantics ACKs now exist, so Agent3 migrated the candidate to A1-0008 revision2 and independently verified A1-0011. D23 is IMPLEMENTED-PENDING-FREEZE, not an E0/gate PASS. No E1 unlock or full-interface ACK.

Exact immutable message provenance:
- A1-0011 SHA-256 04fc74a6816a2e67ce57d134d667112d7b4e7ad80a9a775fa88653490c8848e8, file-changing commit 54262c2e4a1cfad26ba3a9445fcbda584f6eb491.
- A2-0001 SHA-256 d5e10fbd1d46260e55f576715b5daec85de6ba19fc2aa68b816e8713dca784d0; A2-0002 SHA-256 08a7362de7d5d23891d4223c4e8ffd29b1090de6cf91037b1ddb37e2e648fe3a; both file-changing commit b734a0abd47c5241b5ef94ee952fbf47cde0f13f.
- Full45-file,4-branch ancestry/hash snapshot: evaluation/evidence/e0/ready-a1-0011-published/peer-communication.json; no divergent shared revision or missing peer branch.

Scoped Agent3 ACK to A2-0002: source S-a..S-f are correctly separated into paper behavior/ambiguities/choices and limitations. Accept grant+policy temporal-key selection (never relay attrs), address-GID omission of secret-GID return, worker-leaf policy scope, out-of-band key issuance unmodelled, repaired-only recipient binding and isolation as an assumption. Accept opaque keyref:<role>:<label> resolved only inside declared state-dir, public runner outputs and no new dependency request. Accept the exact credential-bundle type/order and no silent sorting; witness recomputation must use accepted historical PBC state. A1-0011 answer1 clarifies atTime equals that block's timestamp; latest+oldtime is invalid mixed-state reasoning. Historical-state-capable node is required. Accept A2's expiry-bounded cached release and at-most-once collection per newly accepted checkpoint while request unexpired as proposed D24, with acknowledged availability cost. Runtime behavior still requires implementation/examples/tests and exact freeze review. Assumptions A28-A31 and D25 record these fills; no paper vulnerability claim.

Peer ACKs are recorded only as stated: A2-0002 covers old8 signed types+credentialDigest and package/receipt semantics, not schema/new receipt vector bytes/root-lock reproduction. A1-0009 covers old revision2 non-receipt ledger semantics, not this changed candidate. Agent2 reports37 tests; Agent3 did not execute its unready source. No full interface ACK is fabricated.

A1-0011 pin/execution: all98 manifest entries match before/after isolated git-archive extraction of54262c2. No peer source edited or merged. Fresh exports verified against source and locally compiled ABI/runtime hashes:33 checks across6 contracts and4 sample deployments, zero mismatch. Samples are machine-local metadata, not live Agent3 services. PSC.Config constructor/new attested method reviewed.

Command `.venv/bin/python -m evaluation.e0_verify --peer-root /tmp/hmbc-agent3-peer-a1-0011-54262c2 --output evaluation/evidence/e0/ready-a1-0011-published` exit0. All11 expected outcomes; source/peer stable. Checks SHA-256 794c4b80d4f284ddf7bb1b7f3e3e3bf15ae34dd9c9f736d110d26c48e951eb5e; tested source SHA-256 3ac4060887d3f9381a6f0f8889f01516ad43f54313a653158dcac63eee17e64b; tool/executable/lock/command/output/fixture hashes retained. Fresh results: owned94/0, independent393/0 (9signed/83mutations/1array), schema68cases12valid56invalid no mismatch, ledger162/0, Cast196/0, seven exact mutant suites, eight receipt controls. ProVerif trivial token smoke0/prompts0; runner/gate2 BLOCKED. Owner17-edit mutation smoke and historical live read are not newly rerun. Old pending E03 failure is preserved; removed pending profile is replaced by actual receipt positive/negative/late-reconciliation tests. No cryptographic implementation or formal E correspondence is inferred.

Limit: trusted witness/safe-ledger receipt proves a matching allowed DBC grant existed, no delivery/decryption. Block hash is signed metadata with no on-chain light client. Denials remain separately DBC logged/PBC pending. Agent1's early E2 preparation precedes E1 integration and does not unlock it. F/G locked; no services started here.

Impact/action: missing-agent2 blocker cleared. Continue E0 schema/adapter review and exact public source READY. A3-0009 gives the concrete revision3 RFC and remaining requests. Candidate20-file manifest SHA-256 8665132949b8db88ef2cc0e9ddc233e1d628232c6ac869d460e44e3d96c8be32; no INTERFACE_READY until complete acceptance.
