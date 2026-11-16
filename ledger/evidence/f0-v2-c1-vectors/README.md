# Interface-v2 candidate 1 vectors checked with the ledger's own code (agent 1, F0, 2026-11-04)

**Purpose.** This is ledger-side input to the v2 mapping review (A1-0105, answering A3-0066). Agent 3's verifier is Python. This checks the same signing vectors with the Solidity hashing and quorum code the ledger runs, and recomputes the immutable-range and masked-build vectors with the rules of my own tools. No contract, export or interface changed.

## Inputs

`inputs.txt` records the proposal commit (origin/agent-3 4de6274) and the sha256 of each proposal file used. `MANIFEST.json` is `6acceadf..`, as A3-0066 states. The ledger sources are a copy of HEAD, with production unchanged since 933d2a7.

## Method

1. `ledger/tools/gen_v2_vector_test.py <proposal dir>` generates `V2VectorsCheck.t.sol` (published here as `.txt`). It is built in a **scratch copy** of `ledger/src` and `foundry.toml`, never inside `ledger/`.
2. For each of the six vectors, `forge test` checks:
   - the domain separator, struct hash and digest against the vector, plus the type hash for GovernanceAction;
   - `QuorumLib.verify` with the four fixture witnesses: NONE at q3, INSUFFICIENT_QUORUM for two signatures at q3, NONE for two signatures at q2, and BAD_SIGNATURE on another digest.
3. Hashing:
   - StateCheckpoint, AccessDecision and GrantReceipt use the E functions `HMBCHash.*Digest`, which KSSC and PSC call today;
   - GovernanceAction uses design 2.2 §2 (`A-F1-DESIGN.md` 7eed1b29..): the exact type string, admins as 32-byte words, domain {HMBCGovernance, "1", chainId, Governance}.
4. Extra checks:
   - SET signatures do not authorize REMOVE;
   - the four witness addresses follow the TEST-ONLY derivation `keccak256("hmbc-e0-synthetic-key:" || label)`. No key is printed or stored.
5. `recompute.txt` recomputes three things in Python:
   - `immutableRefsSha256` of the export-shape vector and of the D50 object-list vector, with the canonical function of `immutable_refs_digest.py`;
   - the D50 masked-build vector, with the range rule and concatenation of `check_masked_runtime.py`.

## Results

| Check | Result |
|---|---|
| `forge test` (`forge-test.txt`) | 26 passed, 0 failed, exit 0 |
| Control A: admins hashed as `abi.encode(address[])` (`control-a-*.txt`) | the 3 Governance hash tests fail, exit 1 (expected) |
| Control B: `uint256 nonce` in the type string (`control-b-*.txt`) | the 3 Governance hash tests fail, exit 1 (expected) |
| `recompute.txt` | export-shape digest, D50 object-list digest and canonical JSON, and D50 masked hash all equal |

After the controls, the test file was restored, and `cmp` shows it equals the published test.

## Limits

- **Governance.sol does not exist.** This checks the planned encoding and the existing QuorumLib, not a Governance contract, TMSC preconditions, nonce or expiry.
- **Synthetic signatures only.** The vector chain ids and addresses are placeholders. No deployment, RPC or live code was involved.
- **Correlated review.** It is the same model family as the peers' verifiers.

Versions are in `versions.txt`.
