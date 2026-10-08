# Phase 1 / E0 progress — 2026-10-07

**Status: E0 PARTIAL, E1 NOT UNLOCKED, gate E NOT RUN.** **Current checkpoint: receipt/deployment candidate revision3; both peer branches present. Read the latest section below; earlier dated sections are historical.** This report is a restartable progress record, not the RQ1 conclusion or an interface freeze. The user confirmed `/home/karma/Documents/RIS`, `SaiyamJain20/RIS`, branch `agent-3`, independent machines, and review of latest communication files across all branches.

## Source and choices

`evaluation/evidence/source-map.csv` maps 37 source/property rows; `assumptions.csv` separates 27 paper assumptions, ambiguities, reconstruction fills and deliberate deviations. PDF page 1 is journal page 134393. Source provenance hashes and visual checks of Figures 5/6 and Tables 2/3 are recorded in `evidence/e0/source-provenance.json`.

The source supports the six contract roles, GID possession, signed issuer-owned trust lists, long-term/temporal combinations, log-first access processing and isolated temporal key use. It does not give our EIP-712 wire formats, nonce/checkpoint rules, atomic cross-chain delivery logging or precise cryptographic split. The complete-details versus hash-only logging interpretations, optional System-mediated policy, wildcard issuer interpretation and majorityConsent placement remain explicit ambiguities. No JANUS finding/code is used.

A3-0002 proposes the conservative same-issuer emergency fixture, signature-authorized submission, issuer-scoped admin rules, paper latest-appended lists, shared paper-profile relay hop, repaired checkpoint/epoch equality, measured clock skew and expiry-bounded cached retries. A1-0007 ACKs the ledger items for D20-D22; agent-2 agreement is pending. A1-0008 revision 2 supersedes the old receipt proposal; agent 3 ACKs the exact RFC in A3-0005. D23 remains OPEN until agent-2 confirms capability/semantics. No receipt schema field migration or implementation is authorized yet.

## Original checkpoint evidence (unchanged historical scope)

| Check | Result | Scope |
|---|---|---|
| Evaluation suite | 57 passed, 0 failed | Schema/vector/oracle/preflight/evidence tests; no live protocol integration |
| Independent eth-account/eth-abi vector cross-check | 333 checks; 8 signed vectors; 70 mutations; 1 record-array vector; no mismatch | Encoding/signature recovery only; incomplete/empty packs rejected |
| Candidate schema fixture validation | 47 cases, no mismatch | Signed/bundle fields and numeric overflow/unknown-field negatives; exact count in schema-vector-check.json |
| Pinned agent-1 Forge suite | 151 passed, 0 failed | Ledger-only module evidence, source snapshot f643805 |
| Pinned Cast cross-check | 166 checks, no mismatch | Peer tool using independent Alloy encoding, reproduced locally |
| Pinned ledger mutant suites | 6/6 detected; expected property failures only | Deliberate check removals, not original-paper vulnerabilities |
| Pending E03 ledger control | exit 1, expected failure | Current repaired-e records an outcome without DBC grant evidence; repair pending |
| ProVerif 2.05 smoke | public token reachable; private token unreachable | Toolchain functionality only; not E correspondence/secrecy proof |
| Runner and gate preflight | exit 2/BLOCKED | Rejects missing freeze/services; no synthetic PASS |

The source/input/output hashes, exact commands, tool versions and failures are attached under `evaluation/evidence/e0/` and `toolchain.json`. The ledger READY manifest has 86 entries and SHA-256 `4d7802b70d731cf5ba3ac3b38fac32ffddaf0400d5b0e7fccfb9117815bfd577`; every entry still matches after local tests. Sample deployment traces remain agent-1 evidence. No integration services were started here.

The vector verifier's first attempt missed the AccessRequest domain dependence on sourceChainId/psc; both were corrected and rechecked. Initial missing-module/stub failures and later behavior RED logs are retained. ProVerif's first build failed at the optional GUI ocamlfind dependency; the command-line core was rebuilt successfully with `-nointeract native`. A Foundry signature-cache warning appeared on the first run; compilation/tests still passed. No failed experiment is labelled REFUTED or omitted.

## What remains mandatory

1. Agent 1 supplied the scoped non-receipt candidate ACK (A1-0009) and corrected READY (A1-0010), now reproduced as described below. Complete receipt/adapter/operation/result/deployment schema agreement and any new exact revision ACKs remain required; this is not a whole-interface freeze.
2. Agent 2 must publish `agent-2`, review source/key/credential flow, propose dependencies, reproduce digests/signatures/mutations and agree to exact schemas, clocks/retry rules and receipt capability.
3. Resolve operation-specific JSON-lines input/result/deployment schemas and ABI/error/retry ambiguities. The envelope's opaque result is explicitly not a fully validated internal record. Agent 3 agrees with A1-0007 that deployment ABI unsigned values stay decimal strings; agent-2 and the full deployment schema review remain pending.
4. Only after three exact ACKs and module smoke checks: freeze `interfaces/v1`, publish INTERFACE_READY, unlock E1 and implement the real adapter runner/service lifecycle against reviewed public exports.
5. Run Alice/Bob/wrong-issuer controls across actual two-chain services; then E2 case matrix/recovery, correspondence model and negative control, repaired receipts, RQ1 report and E3 freeze/ACK gate.

No F/G feature has been implemented. Phase 1 is not complete. Agent 3 has exhausted the currently independent E0 work identified here; the next normative step needs peer artifacts/ACKs. Hourly branch monitoring resumes on meaningful new support. Author self-review is recorded; no independent reviewer was launched because the project explicitly prohibits extra agents.

## A1-0007 review follow-up

Reviewed owner messages from file-changing commit 589a05331a1a9a9cfe99eee2da70b980a44e5317. A1-0007 SHA-256 7489f8ec3b5b196573bb1748ed43faa208802eb9048c384bd878e992d8f61e49; A1-0008 SHA-256 c42d064ce31a6c482f26640e67d1c541e3681db7239b89147b10e6b2e35aefea. The full across-branch provenance snapshot and peer manifest inspection are under evaluation/evidence/e0/review-a1-0007/. No new agent-2 branch was present.

S-1: explicit EIP-712 encodeType annotations and RoleCertificate property order match owner vectors; S-2: empty CredentialBundle is MALFORMED; S-3: direct/nested zero-GID temporal entries are MALFORMED. Ten regression cases failed before fixes and passed afterward (31 schema tests). S-4 is an owner-side change reported as 154 ledger tests; this count is not independently reproduced for the newer unready revision. Historical 151-test evidence remains tied to f643805.

M-1 corrects implemented E validation/update/registration functions. M-2 adds explicit certificate-time, paper-grant lifetime/recipient, partial replay and log-variable fills. M-3 fixes signed CRL wording and ACSC page 10–11. M-4 records registration attempt/success logging-order ambiguity. Rows S33–S37 and assumptions A23–A27 are gap fills/ambiguities, not discovered paper vulnerabilities.

No integration or formal correspondence claim follows from these revisions. Author self-review only; receipt revision 2 and complete interface freeze still need agent-2 support. Final owned verification and the revised candidate hash are recorded by the subsequent READY message A3-0006.

Current follow-up verification: full owned suite 67 passed; independent vector checks333/0; schema fixtures53 (10 valid/43 invalid), zero mismatches; prompt/diff checks exit0; runner/gate expected2/BLOCKED. Checks SHA-256 08a26fa290feed61f024dac17f18a751841f126ca60502d9eb49c9ef6ce0a10e. Revised 16-file candidate manifest SHA-256 e2dde1994fb1146e0df979a955cc2c2ada7ce05e88eb55bf26c26fdf91a815c7. Packaging metadata is added after stable command inputs; no runtime/fixture changes follow verification.

## Corrected ledger READY and scoped candidate ACK

A1-0009/A1-0010 from file-changing commit e351be5 resolve the prior metadata blocker. A1-0009 ACKs exact candidate e2dde199.. for non-receipt ledger semantics only; its stated exclusions remain open. A1-0010 pins ledger589a053/hash1c4f4fc8.. (87 files), superseding A1-0006. Agent3 now independently reproduced ledger154/0, Cast166/0 and six mutant suites; owned67/0/vector333/0; source/peer hashes stable. E03 pending test still exits1, runner/gate2 BLOCKED, PV trivial smoke only. All ten expected outcomes match, checks SHA-256 1b9283db8d6b08d80234e60eacad3067aaa0a981cce7f7e8e93af3a1c795cf8c under evaluation/evidence/e0/ready-a1-0010/. No15-edit source mutation smoke, current deployments, E correspondence or real integration was rerun. Candidate bytes remain unchanged; no full freeze. Missing agent2 and complete schema/receipt agreement still prevent E0 completion/E1 entry.

## Current checkpoint — A1-0011 and A2-0002, candidate revision3

Both agents are available. Agent1 is READY at54262c2 with implemented success-only receipt and fresh ABI/deployment exports. Agent2 is WORKING atb734a0a; source/key/bundle/package/timing and old-vector review is present, but schema review/adapter samples and executable READY are pending. The old missing-agent2 blocker is cleared. Its37 encoder tests are owner-reported, not executed by agent3. No full-interface ACK is inferred.

D23 now IMPLEMENTED-PENDING-FREEZE after both affected receipt-semantics ACKs. The schema migrates exact A1-0008 fields; one new required producer signed vector has13 mutations. All first9 historical vector objects are unchanged. Past-grant late reconciliation is valid; dynamic grant/request/membership checks stay ledger responsibilities. Outcome receipts cannot prove release/delivery/decryption; E trusted-witness/safe-ledger assumptions remain explicit.

Agent3 drafted strict LedgerDeployment from all4 current owner samples (4positive/11negative tests), including unsigned decimal strings and compiler/runtime numeric metadata, exact nested keys and E profile/witness/TTL constants. The proposal is not frozen; sample addresses are machine-local. Added maxLength to Address/Hash/FileHash after3 RED regressions showed regex dollar anchors accepted a final newline. No peer module was modified.

Latest owned94/0; independent393checks/0 (9signed,83mutations,1array); wire schema68cases (12valid,56invalid), no mismatch. Agent1 pinned98-file manifest verified unchanged; ledger162/0; Cast196/0; seven mutant suites detected exactly; eight receipt controls pass. Separate33 static export checks confirm six compiled ABIs/runtime hashes and4 samples match source. No live chains/services or formal correspondence proof were run by agent3; owner17-edit mutation smoke and historical read demonstration remain owner evidence. Historical pending E03 failure preserved; new implemented receipt controls replace the removed pending profile. ProVerif token smoke0; promptcheck0; runner/gate2 BLOCKED.

Exact commands/exits/fixtures/source/tool/output hashes and before/after stability are in ready-a1-0011-published/checks.json; RED/GREEN logs in receipt-revision-2/. Final candidate20-file manifest and checks hashes are in current STATUS/HANDOFF and A3-0009. Source map37; assumptions31; D24/D25/A28-A31 explicitly capture bounded checkpoint retry, opaque keyref custody, historical state/timestamp consistency and grant+policy key selection. These are choices/limits, not author implementation discoveries.

Mandatory remaining work: Agent2 six-operation adapter examples/executable READY, receipt-vector reproduction and exact schema/toolchain review; exact LedgerDeployment consumer ACKs; operation input/result/ScenarioResult definitions; complete three-agent E0 ACK/freeze acceptance. Then E1 real positive/denied two-chain service flows; E2 cases/recovery/models; E3 report/gate. Phase1 remains incomplete and F/G locked. A3-0008/0009 communicate scoped review and concrete RFC via agent3 only.

## Latest check — 2026-10-08: peer dependencies supplied

Agent1 A1-0012 at60b35cb and Agent2 A2-0003/0004/0005 ate1b4322 supply scoped revision3 ACKs and public protocol E0 artifacts. Agent2 explicitly requests nothing further from Agent1 for this handoff. Agent3 independently reproduced235 protocol tests/1 documented FileHash skip and7 generated exports under root Python3.13.13/uv.lock;32 original READY inputs unchanged. Latest33-file evidence-only successor manifest also verified directly against fetched blobs. Commands, hashes and exact file-changing provenance are under peer-review-20261008/. No relay/witness/key-worker/live service integration, formal correspondence, E0 freeze or E1 unlock. Owner second-machine ledger/live smoke and402 extra schema mutation evidence are recorded with owner-only scope.

The main next owner is Agent3: strict operation/envelope/input/result/ScenarioResult proposals, explicit nested symbolic layouts and selected ordering/canonical fixtures, followed by exact affected-party review/common E0 acceptance. D26/D27 record instance-local deployment facts and accepted adapter error choices. All20 revision3 candidate files remain unchanged, preserving the peer scoped ACKs; previous adapter/READY/vector review requests are satisfied. A3-0010 communicates this dependency change.

## Current Agent3 proposal — 2026-10-08 revision4

Agent3 has filled the previously open operation/request/result/ScenarioResult schema gaps. The candidate has78 definitions/29 reviewed files, manifest c8cf819f811e26c7444f386b55c36dc554bbf9e3caa84392afc4f8c45623b4a1. It retains every prior signed definition/vector/source map/tool/lock byte, closes the opaque AdapterResponse result, and adds only legacy-v0/frozen-v1 metadata compatibility to LedgerDeployment. Nested symbolic record/policy/token choices are explicit OPEN proposals (D28/A32/A33); strict observations/finite nullable measurements and39 prospective E cases are D29/A34. All case executionStatus values are NOT_RUN. No E1 worker, actual encryption, integrated result or E2 executor is claimed.

Evidence: boundary35/0, owned129/0, signed393checks/0, schema515cases (92positive/423negative) with0 mismatch, deterministic fixture generation/prompt/diff checks0. Pinned ledger98 entries stable,162tests/196Cast/7expectedmutants/8receipt controls; PV token smoke0 only; runner/gate expected2 BLOCKED. RED logs retained for missing boundary definitions/strict success/parser, case catalog, and v1 deployment label, then GREEN. Checks e411702583b9e46c47e1466516bbe38459d5528b559197a75bd98ab03caf98f6, source stable during commands. Final review is author self-review only; exact peer review remains required.

A3-0011 publishes the exact new/old fields and requested scopes. Agent3's implementation dependency has become Agent1/Agent2 exact revision4 acceptance, not missing Agent2 exports. See interfaces/proposals/v1/BOUNDARY.md and ACCEPTANCE.md. The full E0 freeze and E1 unlock are still pending; Phase1 remains incomplete. No branch merge/main push or peer module/mailbox edit.


## 2026-10-08 revision5 after peer review (not frozen)

A1-0013/A2-0006 are scoped revision4 acceptance with change requests. A1-0015/A2-0007 close the symbolic recipient convention. A2-0008 and A1-0016 identify/confirm the missing checkpoint/receipt signature operations; A1-0017 specifies policy-aware denials. Revision5 implements only owned E0 proposal/oracle corrections, preserving normative v0, existing signed bytes,37 source rows and tool/lock pins. It adds collect_checkpoint/attest_grant, closed crash hooks/count expectations, explicit native-outcome joins and repaired Bob checks; primary record/policy now match P1/H2/HMBC.role.*.48 synthetic schedules are NOT_RUN, not observed E2 results.

Fresh command `.venv/bin/python -m evaluation.e0_verify --peer-root /tmp/hmbc-agent3-a1-ready-e6cf4ff --output evaluation/evidence/e0/revision-5-review/complete-e0` exited0:148 owned tests,393 independent signed checks,68 legacy schema verdicts,166 ledger tests,196 Cast checks,7 expected mutant suites,8 receipt controls. All100 peer manifest entries stayed identical; source stable. Checks SHA-256 `b1f2e8b126d85ae52456cdebb7436d25d603ce41ca1a10bf27d45f3c7462c7c6`, tested source-manifest hash `c36beb423d149032cd3a707c95a6b699b860f44af47e45608c0120b8c59ba80c`. Static source/ABI/runtime/deployment check33/0; no current RPC-state claim. Tools remain Python3.13.13, Foundry1.8.5/solc0.8.37, ProVerif2.05 with fresh binary/lock hash verification in boundary-checks.json. ProVerif checks only public/private-token smoke. Runner/gate remain2/BLOCKED.

All565 schema verdicts (108valid/457invalid) pass with0 mismatches in schema-results-retry.json. First run exceeded the default60-second command budget (exit124), preserved in boundary-checks.json/schema-fixtures.txt; unchanged retry with explicit180-second verification budget exited0/source stable after67.00s. This changes neither protocol TTLs nor experimental attacker assumptions. RED evidence:12 boundary/case failures→12pass;3 Bob assertion failures→18 oracle pass;3 added provenance-control failures→15pass;1 P1 owner failure→final full148pass. These are tested reconstruction/control corrections, not discovered paper vulnerabilities.

Current ledger pin is A1-0014/e6cf4ff/manifest5866921a.. (100 entries), verified against exact READY. Agent2 tipada6378 publishes candidate ledger-backed adapter code/policy-aware witness without integration READY; stale STATUS/HANDOFF and owner live claims do not establish gate completion. Agent3 did not execute it or edit peer paths. Historical b9564f0/235-test E0 reproduction remains separate. Final exact revision5 ACKs, matching current exports and E0 acceptance rows are pending; E1/F/G stay locked. Packaging/board/mailbox hashes are reviewed after test source capture and distinguished from tested runtime inputs.

## A2-0009 review checkpoint — 2026-10-08

Eight operation exports and a scoped revision5 ACK are now available at5e203d0; Agent3 independently reproduced618 E0-only tests/101 evaluator-only skips under Python3.13.13/root lock, nine export files and16 schema examples with independent prepare_request digest/recovery.89 owner inputs and32 package files stayed fixed. Current evidence: revision-5-a2-ack-20261008/compatibility.json SHA-256f594c7261953c4bd7eefa5a8ef8612f99e259d060fa9c030b3e4b22fd211d966.66-file communication scan and100 ledger/89 protocol/32 package integrity checks pass. No live services/worker/model/owner mutation execution or gate result. Owner live claims stay owner evidence.

A2 excludes32 paper expectations/internal evaluator structures and explicitly supplies no service READY. Request only protocol-observable expectation review, owner export-label correction and exact supplement review (E0_REVIEW_A2_0009.md/A3-0015). The new nonce control can pre-collect two honest certificates before first consumption; receipt isolation requires an owner-signed inconsistent fixture and is a deliberate witness-deviation control. Both remain proposed/NOT_RUN. Conditional synthetic pre-registration and raw redacted worker evidence are explicit proposed limits; no authentication guarantee invented. Accepted32-file package unchanged; E0/frozen mapping/E1 unlock remain incomplete. Wrapper failures and exact recovery are retained; author self-review only because extra agents are forbidden. No human action needed.

## Revision6 current review —2026-10-08

A2-0010 supplies exact supplement response/export correction/paper expectation review; A1-0021/A2-0011 support option(c). D35/A38 binds paper symbolic responses to grant.gid's PBC-registered key while retaining native grant0 and30s grant-block expiry. Production still refuses paper grants; the owner subclass is a spike. Eight supplementary nonce/receipt/signature/positive controls and48 amended expectations are materialized as NOT_RUN in35-file manifestdf2a306fd77937572346cf5e91e9354536988af63ed660e14d51e04350161c62. Only two case definitions change; existing signed/wire bytes and old48 outcomes/counts/steps remain. Fresh161 evaluator tests,619 selected non-live protocol tests/101 skips,9 exports,393 signing checks and565 schema verdicts/0 mismatches under stable inputs. These are E0 preparation, not a completed RQ. Exact affected delta ACKs and future frozen mapping/owner readiness remain; E1/F/G locked. Evidence: evaluation/evidence/e0/revision-6-review-20261008/.
