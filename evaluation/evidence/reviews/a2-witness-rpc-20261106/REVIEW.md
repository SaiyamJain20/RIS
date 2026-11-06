# Findings, controls and boundaries

Classification throughout: **tested reconstruction result**. This is not an
original HMBC paper vulnerability report. No wrong signature, grant, request
binding or authorization decision was demonstrated.

## Reproduced refusal-handling gap

At pinned source 0e58f1d, rpc_witness_view.py:179 obtains the transaction through
_guard. The real carried Chain.get_transaction returns any non-null result without
checking it is an object. At line 181, forwarding_call invokes tx.get outside
_guard; the local except list at line 183 does not include AttributeError.

Synthetic RPC results `[]`, `"bad"`, `4` and `true` therefore escape as
AttributeError rather than the documented LedgerUnreachable. The public witness
signing methods' _guarded wrapper converts LedgerUnreachable and store errors,
not AttributeError (witness_service.py:293-299). This review executes the view
boundary, not an end-to-end crashing process. There is no signature/release
result from these malformed replies and no measured process-availability result.

Agent 2 should validate the transaction result as an object and normalize an
unusable node shape to LedgerUnreachable at the owned boundary. Preserve valid
request decoding and undecodable-call handling; add a regression through the
view and public service error path. A null real transaction currently causes
LedgerUnreachable in Chain, although forwarding_call's docstring promises None
for not found; align the description or deliberately specify/test that choice.
No carried E helper or peer file is changed by this review.

## Permissive carried parsing: separate limit

RpcWitnessView delegates to the carried Chain/Contract codecs, rather than
RpcBindingView's recently tightened parser. Real Chain.get_block normalizes
`0x1_0`, `0x01`, `0xA` to decimal 16, 1, 10. Real Chain.call strips the first
two characters without validating the `0x` prefix, so `zz` plus a valid ABI word
decodes as that word; a canonical word with a trailing word also decodes.

These five accepted encodings are diagnostic gaps under a strict refusal
expectation; this module does not independently establish canonical raw RPC/ABI
bytes. They do not reopen A3-0092's closed findings in RpcBindingView, which is
unchanged, and no altered value or unauthorized grant was demonstrated. Agent 2
should document the trust/normalization limit or enforce the chosen refusal
contract locally before claiming strict canonicality for this witness view.
The present code's docstring does not itself make a full canonicality claim.

Refuted suspicions: `0x-1`, `0x+1`, `0x 1` are refused as LedgerUnreachable;
an integer ABI result also refuses correctly. Fourteen controls retain canonical
observations, numbered blocks, nonce 7, authority true/false, missing numbered
block, missing/undecodable transactions, transport/chain/quantity/ABI/log/header
failures. Probe success means execution and these controls passed; it does not
mean the nine diagnostic refusal properties passed.

## Owner progress and remaining prerequisites

A2-0067/0068 and their exact live test/evidence bytes were read. They report
37/38 tests, honest checkpoint/governance/decision/receipt certificates accepted
by real contracts, threshold/signature controls, and an idle-chain staleness
observation. Those are owner-run results, not this coordinator's live experiment.
Preserve their failed first runs and the 42/44 initial mutation result: one
equivalent case was removed and one test gap was repaired by Agent 2. Fresh
coordinator mutation evidence here is the final 43/43 result only.

Current-state calls are explicitly unpinned to observe's block, and there is no
reorg bracket. Block production/expiry requires a real runtime recipe; mining
first in an owner test is not an evaluator timing experiment. The production
docstring still says decision/receipt are untested here despite A2-0068's later
owner test; update that stale local sentence when next editing the module.

Full CLI/Worker factory, supervised independent witness processes, real pool
transport/clock and H2/H5/H6 remain pending. A direct collection of signatures
from service objects is not a networked witness pool or a consensus experiment.
Require the exact published schema, enabled response validation and validated
handler behavior in the final runtime recipe. Complete exact source READY/mapping
and separate full source/tools/config/run FREEZE ACKs remain mandatory.

Agent 3 next: source-state/sign-time joins and exact producer schema/path/lock
choreography for row completeness, then independent fault oracle/finite model.
Current helpers do not prove native source truth, store/export completeness,
power-loss durability, independent hosts, real timing or consensus. Preserve legal
A->B->A recurrence, revision-9 ordering/equal hashes, fault/clear labels and
bit1/bit5 death exclusions. No phase or gate is advanced.
