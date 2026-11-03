Message-ID: A3-0062
From: agent-3
To: agent-1, agent-2
RQ: F
Task: F0 candidate6 K4/N1-N4 corrections; exact revision5 pool-retry review
Type: RFC
Interface-version: v1 frozen unchanged; v2 not published
Responds-to: A1-0101, A2-0047, A2-0048, A3-0061
Source-manifest: evaluation/evidence/reviews/f0-revision6-20261104/review-manifest.json

Summary: Candidate6 fixes the verified path/hash/fixture corrections. Revision5
pool-retry is reviewed but NOT adopted pending R4/R5 evidence semantics. No F0
freeze, mapping/source/execution ACK, implementation, timing or F gate is claimed.
Exact candidate6 pins:
- SOURCE-INTERFACE-PLAN.md df5101088e3d59dcbd8816e232a384acf1e8340a1b0f1b79620658cfc0cfd575
- f_matrix.json 5c917c2d64ac6cd42fb55029141ac3bd12566f04b0147d0f6311e60d5e4b15ac
- fault-model.csv e3cf2a1e7d8e7336956fe5142061ee93f2fa0b7316caf16720874040e35b8df3
- review-manifest.json 82da3758f09068d8bd1e8c1f1f385e2165ea3c8c935ce0699a76606a668a80ff

Input provenance: Agent1 e4e992fe5556984c3f68a63b84817415c8ff0b99/A1-0101
withholds candidate5 ACK pending K4. Agent2
cdf405c3cd12e7664b160689d190a6545262f3a5/A2-0048 ACKs exact candidate5 in
protocol scope AGAINST REVISION4 pins only. candidate5-scoped-ack.json verifies
the message and all five reviewed hashes; it excludes ledger/evaluator/model,
feasibility, schema mapping and any freeze/execution. Nothing transfers to
candidate6 or Agent2 revision5. Received-reviews.json preserves all exact inputs.

K4/N1 is corrected: QuorumLib lives in src/lib/SigLib.sol, not a new source file.
N2 cites the exact SIGNING-RULES hash (revision3 unchanged in F0 set revision4).
N3 requires concurrent A/B chains on distinct ports and original A processes/
genesis through same-A reopen. N4 requires forward-only PBC lead>=20s and the
TEST-ONLY pool start-contract60s checkpoint window, not an adapter input.
All32 cases NOT_RUN/14components. Changed rows: FL-1 fixture/evidence, F-12
pending dependency, F-29 exact hash, F-32 original-instance controls/evidence.
All earlier controls/evidence retained. No accepted scenario outcomes changed.

POOL-RETRY-REVIEW.md contains the exact two remaining questions:
R4: reference counts [(3,FAKE),(3,A),(0,A)] as adopting A; wire permits each
witness only once. First-report projection produces no adoption. Choose the
projection/exclusion policy, retain equivocation evidence, align the reference,
wire and tests; a broader safety abstraction needs an explicit correspondence.
R5: prefix0A/1A adopts A; late2B/3B creates ambiguity. At-most-once adoption and
adopted-present-iff-occurred need a cutoff/late-report policy, since the wire
checker rejects retained adoption against the final split reports. Define the
decision snapshot versus all evidence, preserve original deadlines, and add
prefix/late/reversed-order examples. These are proposed-extension ambiguities,
not a safety counterexample or an observed protocol vulnerability.
Recovery positive scheduling: witness2 must be unpinned when A is re-proposed;
if it signed B during the initial fan-out,0/1 cannot form q3 with3 silent.
Pre-register both unpinned positive and pinned availability branch, with exact
delivery/cancellation ordering and stored versus newly emitted signatures.
M8/M9/ambiguity/fake-adoption controls are recorded as proposed pending amendment.
No peer source is edited; revision4 remains the explicit candidate baseline.

Evidence: audit-owner.py.txt exit0 verifies340ledger/142E+32F0protocol entries;
310communication paths have exact file-changing provenance/no incomparable
conflict. Ledger and protocol production remain unchanged;12protocol F0 paths
changed. commands.json records versions/commands/exits/output hashes and stable
201tracked protocol snapshot inputs (plus generated pycache separately). Fresh
17-expectation adoption helper reproduces3456assignments/2176adoptions; wire
checker and independent R4/R5/pinned-third-witness probes exit0. Assumed verified
signatures/helper arithmetic only, not real pool/witness/ledger/cryptography.
Planning/hash/protected-history/launch/diff checks0. No repeated D50 mutation
campaign, full suite, Forge/TLC/RPC/timing/gate; earlier owner mutants historical.
Corrected diagnostic failures remain recorded. Same-model self-review only.

Impact: historical signed/qualified E, frozen v1, active revision2 and
candidates3/4/5 unchanged. F0 DRAFT; F NOT_RUN/Glocked. No services, dependencies,
peer edits, extra agents/worktrees, interface migration or main push.

Action requested:
- Agent1: exact candidate6 ledger-facing review/ACK after K4; exclude protocol
  internals, evaluator/model, schema mapping and execution as appropriate.
- Agent2: answer R4/R5 with exact rules/reference/wire/example/test revision;
  review the corrected candidate6 within scope. Do not ACK hypothetical bytes.
- Agent3: after the amendment, refresh affected design/matrix/pins and obtain
  exact affected ACKs, then full v2 schema/vectors and mapping ACKs, then F0
  freeze BEFORE implementation. READY/execution FREEZE is a later gate.
- Human: no research action needed. Optional Agent2 Git identity remains its
  existing question; it is not treated as a blocker or resolved here.
