# Exact review of Agent2 revision5 pool retry — 2026-11-04

Classification: ambiguities in a proposed extension plus tested design-helper
results. NOT observed protocol vulnerabilities, cryptographic results, a runtime
reconstruction result or a gate. Review is correlated, by the same model; no
extra reviewer/agent was launched.

Input: cdf405c3cd12e7664b160689d190a6545262f3a5, A2-0047/A2-0048.
SIGNING-RULES.md SHA-256 46769bee8b2de759c0e013f414b75eddbe28b31ab4d5dfac1eb3b867ce824a17;
SUCCESSOR-WIRE.md 7ae365c9d8e8b00d9a3d982379f4d9c845241e06cb5d469bc49ef278c38a2f1a;
manifest ad2a7780265b43f0de3e95c574ec55818a8c7b27508569fe40e9442345304740.
D50 and the actual witness conflict/death rules are unchanged. This review does
not transfer an earlier scoped ACK or accept an unwritten correction.

The requested essentials are present: retain the original proposal; require two
agreeing distinct authenticated reporters for checkpoint adoption; recompute the
digest/recover the reporter; independently validate on re-proposal; preserve
recorded expiry and original collection/reply deadlines; no signing/death bypass.
The helper reproduces all17 expectations, including3456 assignments/2176
adoptions/zero violations of the stated f<=1 property. The wire checker passes.
Those checks establish neither implemented signature verification nor liveness.

Two exact decisions remain before adopting this amendment into the shared plan
or successor schema. Agent2 owns any reference/rules/wire correction.

**R4 — equivocation and the evidence projection.** The reference explicitly
counts one witness once for EACH value it reports. For input
[(3,FAKE),(3,A),(0,A)] it adopts A. SUCCESSOR-WIRE requires recordedReports to
contain each witness at most once. Choosing the first report instead yields no
adoption; choosing the later report yields A. Neither selection nor exclusion of
an equivocator is specified. This is not an f1 safety counterexample: A has an
honest reporter. It is a mismatch between the reference input and serializable
adoption evidence. Specify the policy, preserve equivocation evidence, and align
the normative reference, wire examples/checker and sensitivity controls. A wider
adversarial abstraction is acceptable, but name it as such and prove/check the
projection to the actual one-report wire rather than claiming identical rules.

**R5 — when adoption is decided and what later reports mean.** A prefix
[(0,A),(1,A)] selects A; adding [(2,B),(3,B)] gives ambiguity/no adoption. Adoption
is at most once, and the wire says adopted is present iff it occurred, yet its
checker recomputes the decision from the entire recordedReports array. Retaining
an earlier adoption plus these late reports fails that checker. The documents
need a deterministic collection/round cutoff and late-report policy. State
whether reports represent the decision snapshot or all received reports, how
late evidence is retained, and whether a later split preserves or cancels an
adoption before submission. Keep original budgets; waiting for four replies may
end in a timeout, not a silently extended window. Add a prefix-then-late-split
example and opposite-order control. No conflicting q3 certificate is demonstrated
by this observation; honest durable single-signing remains the safety backstop.

**Recovery scheduling, not an extra protocol change.** A2-0048's proposed F-12
positive requires witness2 to remain unpinned before re-proposing A. If initial
fan-out causes witness2 to sign B while0/1 report A, with3 silent only0/1 can sign
A; adoption cannot erase witness2's live B. Pre-register both branches: (a) a
controlled schedule in which2 has not signed B and can validate/sign A; (b)2
already pinned B, no q3 until ordinary ledger-observed death permits reuse.
Specify delivery/cancellation ordering and every stored/new signature. Do not
claim the positive from a generic concurrent broadcast, and do not interpret
branch(b)'s bounded availability cost as a safety failure. Actual schedule,
startup/collection budgets and timing remain unmeasured.

Requested owner controls M8 (re-derive instead of retain), M9 (adopt on one report),
2-2 ambiguity, two-Byzantine fake adoption and independent honest refusal are
retained as PROPOSED pending the exact amendment; they are not implemented or
silently inserted into the accepted revision4 wire. Candidate6 corrects K4/N1,
N2/N3/N4 against revision4 pins and explicitly leaves this dependency open.

Reproduction: review-probes.py.txt invokes the pinned helper and the pinned
checker's helper definitions from an exact git-archive snapshot. It checks both
contrasts above and the pinned/unpinned eligibility arithmetic. This is a design
probe, with assumed verified signatures, no real pool, witness, ledger or RPC.
commands.json records actual commands, exits, timestamps, output hashes and
pre/post snapshot hashes. Agent2's previously recorded7/7 and11/11 mutant counts
are historical owner evidence; these mutation campaigns were NOT rerun here.
