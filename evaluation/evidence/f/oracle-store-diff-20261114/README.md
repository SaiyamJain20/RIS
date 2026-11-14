# Differential check: fault oracle vs agent 2's real WitnessStore — agent 3, 2026-11-14

Classification: tested reconstruction result (my READING of the signing rule vs the owner's store).
Same-model author of both sides; synthetic keys; one host; pin-death logic only; not Gate F.
Source: agent 2 origin/agent-2 55f180e (scratch git-archive extract), `hmbc_protocol.witness_state`
(real durable SQLite store via init_store/sign), helpers from tests/test_witness_state.py.
Script `evaluation/measurements/oracle_store_diff.py` (hashes.txt), `python -I`, exit 0, 0.3 s.

Method: for each of 4 types (StateCheckpoint, AccessDecision, GovernanceAction, GrantReceipt) the store signs
a first effect, then is asked to sign a different effect after an observation grid: timestamp
{exp-1, exp, exp+1} x observed sequence/nonce {key-1, key, key+1} x grant {F,T} x outcome {F,T} x
(earlier result ALLOW/DENY for decisions) = 180 cases. The caller claims the first true death fact (the
store re-checks the numeric ones; grant/receipt are caller-asserted by the store design). Agreement means
store accepts exactly when the oracle reports no violation.

Result: 180/180 agree (142 store accepts, 38 refusals CONFLICT_PINNED; per type accepts/refusals:
AccessDecision 60/12, GovernanceAction 32/4, GrantReceipt 18/18, StateCheckpoint 32/4). Discrimination
check: seven deliberately broken oracles each disagree with the unchanged store (expiry >=->> 20 cases;
receipt never dead 18; decision >->>= 6; drop grant clause 4; grant kills DENY 4; checkpoint >=->> 4;
governance >=->> 4); bytecode cache cleared per mutant, file restored byte-identically, control rerun 180/180.
So my reading of SIGNING-RULES section 6 matches the store's implemented behaviour on this grid, including the
rule that a DENY is never killed by a grant.

Limits: one earlier digest per key (no multiple live digests, no re-sign chains); the store's grant and
executed-receipt facts are asserted by the caller and not verified against a ledger, so this shows rule
agreement, not that a real caller asserts them correctly; observation faults (regression) not covered;
agent 2 has not confirmed my reading in words (A3-0121), the store behaviour is the evidence.
