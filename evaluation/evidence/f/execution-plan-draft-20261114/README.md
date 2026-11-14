# F execution plan DRAFT — agent 3, 2026-11-14

Latest technical review: S2-0025 candidate `37ca31c` (protocol subtree
`7566f63d693afe8fa88ab7cc69872082d58d88db`) now reproduces 40/40 K1 detections and
40/40 controls on agent 3's host, plus 81 state tests. Its kill-coverage result is
accepted at isolated scope; see `../../reviews/proxy-k1-20261114/README.md`.
D57 records the human's authorization of proxy-2 and clarification that all agent
numbers are portable work roles. The machine-readable draft now adopts `37ca31c`,
its exact protocol tree and actual publication ref `origin/agent-1`; S2-0024 is
accepted as the protocol role's signing-rule answer. No original-session approval
or duplicate branch push is needed. The preflight checks the declared publication
ref and exact subtree; its legacy `ownerCandidates` field denotes role artifacts.
The plan remains DRAFT and actual exact FREEZE ACKs are still absent. The older
`55f180e` candidate retains its 29/40 result; it does not describe the current
candidate. Older preflight results describe their pinned bytes and do not validate
this revised draft.

DRAFT. Authorizes nothing: no service, no integrated run, no FREEZE. Gate F NOT_RUN; all 32 cases NOT_RUN;
G locked. This is my proposal after the E gate precedent (`evidence/e3/gate-plan-20261012`) and the merged
case coverage map (`case-coverage-map-20261114`). Grouping into families is a planning choice, not a protocol result.

`plan-draft.json` holds the machine-readable form: pins, six case families (8+6+4+8+3+3 = 32, each case once),
stages, preconditions and non-goals. Key points:
- Ledger pin is 85c59f5, not the e4e992f named in f_matrix.json (A1-0127; matrix not edited).
- The current protocol candidate is `37ca31c` / tree `7566f63d..`, published on
  `origin/agent-1`.
  D57 authorizes proxy-2 to act for the portable protocol role, including source
  approval and exact protocol FREEZE ACKs. S2-0024 is accepted as the role's
  signing-rule answer; S2-0025's K1 result was reproduced 40/40 with 40/40 controls.
- Family B uses the fault oracle (`oracles/faults.py`); the oracle needs signing-time observations that current
  captures do not all carry. That gap must be closed by the runner before family B can produce verdicts.
- F-25 and F-26 are residual-inventory analysis items and are NOT_EXECUTED by design; F-17, F-18, F-24, F-19 are
  outside-bound or mutation cases and are expected to show violations or trust assumptions, reported as such.
- Stages mirror the E gate: verify pins, source bracket, isolated baselines as controls, per-family integrated runs
  with positive controls first, result classification, post bracket, manifest and E regression, then RQ2-F.md.
Update 2026-11-14 (A3-0128, incorporating ledger review A1-0129): the test-first runner preflight for stages 1–2 now exists in
`evaluation/f_preflight.py`. It verifies the draft's 32 IDs against the exact frozen revision-8
matrix at `evaluation/evidence/reviews/f0-revision8-20261104/f_matrix.json`; coverage matches
32/32 with no missing, extra or duplicate IDs. The first preflight mistakenly used the current
29-row scenario matrix; that artifact is explicitly invalidated and must not be cited.

The draft now carries exact commit/tree candidates for both owner sources, the ledger source
manifest digest, v2 and v2.1 freeze hashes, v2.1 schema hash, matrix and coverage hashes, the frozen
root toolchain-manifest hash, and the F-only TLC jar hash. Preflight reads the ledger manifest blob
from the exact candidate commit. It treats the root toolchain as the frozen E manifest and records
TLC separately as an F-only tool; this avoids changing the E-frozen toolchain file.

The final r4 preflight exits 2 with `BLOCKED`, starts no service and records all 32 cases as
`NOT_RUN`. Every declared source/blob hash matches exactly. The owner commits are not execution
ACKs. Agent 1's A1-0129 review is a scoped review, not a FREEZE ACK. Protocol K1 and the signing-rule
source reading are closed at the accepted isolated role scope; actual exact execution FREEZE ACKs,
the runner's signing-time/native-generation joins, and stages 3–7 remain open.

A1-0129's ledger-scope details are now explicit in the machine-readable plan: v2.1/schema and
ledger-manifest pins; scratch-archive deployment; profiles, complete-details log mode and chain
IDs; secret exclusion; fresh chain pair per case; exact quorum rejection precedence; FL-6 stale
witness-set result; F-24 poison deployment isolation; F-31 `evm_revert` outside the monotone
safe-ledger assumption; and the F-commit `repaired-e` regression choice. This is still a DRAFT,
not an execution authorization.

Next: implement and verify the offline signing-time/native-generation joins and remaining runner
stages without changing this draft into authorization. Exact role-scope execution ACKs and an
authorized FREEZE are required before services; after those, start with positive controls and family
A, preserving the staged gate sequence. Honest size: the
integrated runner and six families are the bulk of F. Detailed final preflight output and limits:
`../preflight-20261114-r4/README.md`.

## Continuation correction — A3-0131, 2026-11-14

The updates above supersede the older pending-K1 and pending-signing-rule wording.
The live candidate's publication ref is `origin/agent-1`; the preflight checks that
declared ref and exact protocol subtree. D57 makes role continuation portable and
does not require a duplicate push to `agent-2`. Agent 2's branch remains at
`9d44754`, with no new publication on this refresh. S2-0026 is a protocol-role
review, not a FREEZE ACK.

The remaining join gap is now split clearly: `evaluation.signing_event_join_v2`
joins generated/captured RPC signature replies to an exact signed-history digest,
generation and store-reported observation, with 15 focused synthetic tests. It
does not authenticate or establish completeness of a real process transcript, prove that
the service validated a live proposal, or authenticate native ledger facts. The
runner must still acquire real transcript/native captures and preserve those
limits. No integrated cases or services are authorized by this design note; plan
status remains DRAFT, all 32 cases and Gate F remain NOT_RUN, and G remains locked.
