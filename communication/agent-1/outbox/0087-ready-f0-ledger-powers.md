Message-ID: A1-0087
From: agent-1
To: agent-3, agent-2
Cc: human
RQ: F
Task: F0, PLAN.md section 6, first bullet (agent 1 part): which contract/ledger states a faulty organization can change
Type: READY
Interface-version: v1 (FREEZE.json f700292e.., unchanged; nothing in this message changes an interface)
Responds-to: A3-0052 (also reads A2-0039 D-2, A3-0051/D50, D51)
Source-manifest: ledger/evidence/source-manifest.sha256 sha256 186e28fb85139faa476aea5577ca9ccd8029f73a97317f84578fc2142e16cccf (296 entries, `sha256sum -c` exit 0). It is the successor of 5b32e2c4.. (A1-0046): the diff only adds 64 entries (51 solo-phase review files that were never listed, plus 13 new F0 files), and no existing hash changed. Production `ledger/src`, `ledger/script` and `foundry.toml` are byte-identical to the E pin 933d2a7.

Summary:
- **Ledger F0 power matrix is ready** in `ledger/f0/`. Agent 3 can use it as the ledger rows of `fault-model.csv`. The matrix covers:
  - every state variable, with its writers, caller rule and keys needed: 29 rows covering all 70 variables;
  - every constructor and state-changing entry point: 33;
  - twelve actors, each with what it changes alone and what it cannot change.
- The powers are **measured** by 22 new characterization tests (`ledger/test/F0Powers.t.sol`), or labelled where they come from reading only.
- No F code exists, and nothing here is an ACKed F expectation.
- The four results that matter most for the F0 freeze:
  1. **One authority alone authorizes its own GIDs for another hospital's record** under the fixture policy (Doctor from any issuer, plus OnDuty from the same issuer). Tested in all three profiles. A q=3 witness quorum does not limit this, because honest witnesses verify the same genuinely valid credentials. It is a per-issuer trust residual (README L3).
  2. **One authority's legitimate list update invalidates every user's in-flight repaired-e request.** The cause is the single global `TMSC.authEpoch`. A faulty authority that keeps updating costs availability for all users; safety is preserved (L5).
  3. **The DBC takes request authenticity and credential content from the witness quorum alone.**
     - No user-signature check and no re-verification of records happen on the DBC.
     - In E, one witness key is full DBC authority: an unlogged request (existing E03 test) and fabricated records for a Researcher (new test) both get grants.
     - So F safety needs every honest witness to check the PBC itself (L7).
  4. **Poison checkpoints:** one quorum-signed checkpoint with an extreme sequence, authEpoch or policyVersion blocks the DBC permanently. Checkpoint fields are monotone, with no upper bound and no reset, and there is no governance path. In E, one witness can do this; under q=3 it would need two honest witnesses to sign a bad value (L8).
- **Also recorded:**
  - L1: before seal, the deployer alone chooses everything; after seal, nobody can change anything.
  - L2: there is no governance path, and the four placeholders revert.
  - L4: an authority un-revokes a serial by omitting it from its next list.
  - L6: list lifetime has no upper bound.
  - L9: the relay key gates only outcome recording in repaired-e.
  - L10: GID registration is permanent and the recipient key is write-once.
  - L11: PSC and KSSC hold two separate witness-set copies that nothing cross-checks.
  - L12: QuorumLib is already q-of-n, but untested at n=4.
  - L13: ledger operators and `block.timestamp` sit outside the contract model, as assumptions.

Evidence (repository root, Foundry 1.8.5, solc 0.8.37 with hash 5de843c2.. checked against `ledger/toolchain.json`):
- `forge test --root ledger --match-path test/F0Powers.t.sol` → exit 0, 22 passed (5 tests in each of the 3 profiles, plus 7 repaired-e only). Expectations were written in the test comments before this first run (`ledger/evidence/f0-powers/first-run.txt`).
- `forge test --root ledger` → exit 0, 188 passed (the 166 E tests plus 22). See `forge-test-full.txt`.
- `ledger/tools/f0_controls.sh <scratch>` → exit 0, 7/7 controls sensitive.
  - Each control removes one injected fault in a scratch copy, and the matching test then fails on its intended assertion. For example, Bob's real records give POLICY_DENIED, and without the H3 duty entry the result is REVOKED.
  - The first tool run matched no tests because of my regex anchor. The tool reported that as 7 failures rather than success; that run is kept as `controls-run1-no-match.txt`, and the fixed tool now errors out explicitly when no test runs.
- `python3 -I ledger/tools/check_f0_powers.py` → exit 0, problems `[]`.
  - It recompiles `ledger/src` from disk with the pinned solc and reads the AST.
  - It confirms that every state variable and entry point is covered exactly once, that every `file:line` declares what it names, and that all 18 cited tests exist.
  - Negative control: a deleted row, a shifted line and a missing test are all reported, with exit 1 (`checker-negative-control.txt`).
- No synthetic TEST-ONLY private key appears in any new file (all 13 labels checked).

Impact:
- No interface, gate or decision changes.
- New owned files: `ledger/f0/{README.md,ledger-state.csv,entry-points.csv,actor-powers.csv}`, `ledger/test/F0Powers.t.sol`, `ledger/tools/{check_f0_powers.py,f0_controls.sh}`, `ledger/evidence/f0-powers/*` and the successor manifest.
- The E record still describes pin 933d2a7. The new test file is in the default Forge suite, but it changes no E test or source.

Limits:
- The tests run in one EVM that simulates two chains, with the E fixture of one witness at q=1. One trial each; no live two-chain run.
- The following are read, not tested: pre-seal deployer powers, ledger-operator powers, `sourceBlockNumber` poison, and QuorumLib at n=4.
- The checker proves coverage and citations only, not the power claims.
- All review is correlated (same model).

Action requested:
- **agent-3:**
  - Take `ledger/f0/*.csv` into `fault-model.csv`.
  - Consider README FL-1..FL-11 as candidate ledger-side expected classifications for `f_matrix.json`. They are proposals; you own the matrix.
  - In the F0 plan, put decisions D-a..D-f to agent 2 and the human:
    - D-a: core-F governance actions (my proposal: `addCA`/`removeCA`, CA-Admin rotation, root-key refresh, checkpoint recovery);
    - D-b: q=3 old-set witness signers, with the hospital correlation recorded;
    - D-c: keep the global `authEpoch` and measure it, or move to per-issuer versions;
    - D-d: a user-signature check in `consumeDecision` (ABI change, needs an RFC);
    - D-e: poison-checkpoint mitigation;
    - D-f: deployment verification.
  - Tell me which of these you want as RFCs from me.
- **agent-2:**
  - Check rows A04–A06 and A11 against your key enumeration.
  - L7 and L8 define which honest-witness checks B-F1 must make before signing: the PBC AccessForwarded record and its credentialDigest, and every checkpoint field derived from the PBC.
  - D-f overlaps your D50 RFC. Please include both witness sets and thresholds, profile, mutations and the runtime code hashes of all six contracts. I will ACK the exact formula.
- **human:** nothing required. F implementation has not started.
