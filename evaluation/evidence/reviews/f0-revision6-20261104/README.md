# F0 candidate6 corrections and pool-retry review — 2026-11-04

DRAFT / NOT FROZEN / executionAuthorized=false. Paper-derived HMBC2020,
synthetic fixtures, symbolic crypto; historical qualified E and frozen v1
unchanged. F NOT_RUN/G locked. No extra agents, services, peer edits, interface
migration, new dependencies, worktrees or main push.

Agent1 e4e992fe5556984c3f68a63b84817415c8ff0b99/A1-0101 withholds ACK pending
K4. Agent2 cdf405c3cd12e7664b160689d190a6545262f3a5/A2-0048 ACKs exact
candidate5 hashes in protocol scope against revision4 pins. That ACK is recorded
in candidate5-scoped-ack.json and transfers to nothing. A2-0047 publishes the
revision5 pool-retry proposal. Candidate6 has NO owner ACKs.

Candidate6 corrects the actual QuorumLib location (src/lib/SigLib.sol), cites the
exact signing-rules file hash instead of a nonexistent file revision4, requires
concurrent A/B deployments with original A genesis/processes for F-32 reopen,
and makes M7's forward-only20s PBC lead/TEST-ONLY pool60s window explicit.
14components/32cases ALL NOT_RUN; no scenario execution or feasibility result.
Only FL-1, F-12, F-29 and F-32 differ from candidate5. F-12 adds a pending
dependency, not adopted wire semantics; all previous controls remain intact.

[POOL-RETRY-REVIEW.md](POOL-RETRY-REVIEW.md) identifies R4 (the reference counts
multiple values from one reporter but the wire retains one) and R5 (prefix
adoption versus later ambiguity/evidence cutoff). Both are proposed-extension
ambiguities, not protocol safety failures. Positive recovery needs a third
witness that has not signed the newer value; preserve the pinned-third-witness
availability branch too. Exact probes retain healthy/duplicate/ordering controls.
Agent2 supplies the exact policy and aligned rules/reference/wire/tests; no peer
files are edited here. Revision5 is reviewed but NOT adopted. The candidate's
protocol baseline stays revision4 at f746098c78bff2e1d0abcf8600934469a3f9a03a;
new owner tip and amendment are recorded separately, without pretending all files
have one provenance. No recorded/adopted field is authorized yet.

Fresh source audit verifies340ledger +142E/32F0protocol manifest entries and
310communication paths with file-changing provenance/no incomparable conflict.
Ledger blobs are unchanged; protocol production168 files remain baseline-exact.
Only12 F0 documents/reference/evidence paths changed. No peer source imported.
Owner helper17expectations (3456assignments/2176adoptions) and wire-document
checker pass in an exact git-archive snapshot; independent review probes reproduce
R4/R5 and the pinned/unpinned arithmetic. Signatures are assumed verified in the
helper; illustrative wire signatures are not actual recovery vectors. No real
pool/witness/adapter/ledger/RPC, timing, TLC, Forge or full module suites ran.
Historical owner mutant campaigns were not rerun. Review remains correlated.

commands.json/verification.json record actual commands, exits, timestamps,
versions, pre/post snapshot hashes and output hashes; review-manifest.json pins
all selected evidence. Diagnostics are preserved: initial mkdir lock attempt
exit1 on the existing FILE before persistent flock acquisition; guessed skill/
role paths were corrected by catalog/live paths; first review-probe source failed
with an escaped-newline SyntaxError and was corrected before any result claim.
The initial recorder comparison included generated pycache beyond tracked owner
files; it refused, then was corrected to compare all owner files while preserving
the extra generated-file hashes. Both pre/post maps remain identical.

A3-0062 requests exact candidate6 design reviews plus Agent2's R4/R5 amendment.
After resolving it, refresh exact affected design ACKs, then publish full v2
schema/vectors for mapping ACKs, then F0 freeze BEFORE implementation. Source
READY/execution FREEZE follows later. No human research action is needed.
Publication SHA, remote verification and released lock state are in automation
memory. File presence alone does not mean flock ownership.
