# E symbolic correspondence slice — expectations before execution

PLAN C-E2 / SPEC E01. Paper-derived reconstruction; not the authors' implementation.
HMBC2020 III-D3/III-E2 and Figure 6 describe verified attributes being forwarded
from PSC to ACSC. They do not specify this signature protocol. The model represents
our explicit repaired-e completion with one honest user and one trusted witness.

Before observing ProVerif output, require:
- Every symbolic grant has a prior user request AND witness decision agreeing on
  request identity, subject, data, source (chain/PSC), destination (chain/KSSC),
  action, policy and nonce.
- A legitimate allowed grant is reachable. A policy-denied data grant is unreachable.
- Removing destination from the witness certificate, while preserving all other
  bindings and signature verification, admits a destination-substitution trace.
  Agreement on the seven remaining fields still holds and legitimate access remains.

Model choices: public adversarial transport; perfect symbolic signatures; fresh
request identities/nonces; uncompromised user/witness keys; trusted witness checks
an abstract allow/deny policy. Source/destination chain-contract pairs and policy
versions are atomic public names. UserRequest abstracts authenticated request
admission; WitnessDecision abstracts honest PBC observation plus DBC policy checks.
These events do not reproduce chain storage or transactions. No quorum/F work.

Queries are NON-INJECTIVE: signature/certificate replay is intentionally possible.
No nonce consumption, mutable trust/revocation state, timestamps/expiry, worker
intent/send/recovery, audit reconciliation, EIP-712 encoding, hash collision,
implementation correspondence, computational cryptography or ABE proof is modeled.
The mutant is a deliberate abstraction mutation, not the deployed ledger mutant
and not a paper vulnerability. Full catalog execution and real recovery still
require a separate exact integration freeze and both peer ACKs.

Reproduce with the pinned ProVerif 2.05 executable in evaluation/toolchain.json:
`proverif evaluation/models/e/access.pv`
`proverif evaluation/models/e/access_mutant.pv`
The pytest check executes the real pinned binary and verifies its SHA-256, query
verdicts and reconstructed counterexample, rather than grepping model source.
