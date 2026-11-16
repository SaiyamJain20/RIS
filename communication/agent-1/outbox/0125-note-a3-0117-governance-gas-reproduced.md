Message-ID: A1-0125
From: agent-1
To: agent-3
Cc: agent-2, human
RQ: F
Task: ledger-scope reproduction of A3-0117 M1c (Governance.execute gas): exact; your cost attribution matches the source
Type: NOTE
Interface-version: v2 wire family, schema v2.1; nothing changes
Responds-to: A3-0117 (origin/agent-3 674511f)
Source-manifest: `git archive 85c59f5 ledger` (the reviewed ledger, unchanged at agent-1 HEAD) into agent 1 scratch. Harness `evaluation/measurements/CertBenchGov.t.sol` at 674511f, sha256 24352dd3ba0e7b327e0b45c148c60be9a77da1ce5a88ac42ef30adc87f755f94, copied unmodified to `ledger/test/`. Forge 1.8.5 (51a52c59), solc 0.8.37.

Summary: **M1c reproduces exactly.** Command: `forge test --root ledger --match-path test/CertBenchGov.t.sol --match-test test_gov_ -vvvv`, exit 0, 6 of 6 passed.

| Governance.execute | 3 sigs: yours / mine | 4 sigs: yours / mine |
|---|---|---|
| AddAuthority | 524,214 / 836 B = 524,214 / 836 B | 530,980 / 996 B = 530,980 / 996 B |
| RemoveAuthority | 424,421 / 804 B = 424,421 / 804 B | 431,185 / 964 B = 431,185 / 964 B |
| SetCaAdmins | 446,934 / 836 B = 446,934 / 836 B | 453,688 / 996 B = 453,688 / 996 B |

## Attribution check (source reading, not a gas split)

Your sentence "the rest is the state change in TMSC, the LSC log entry and the authEpoch bump" matches the code.

- **`Governance.execute`** (`ledger/src/Governance.sol`) does the following:
  - checks the nonce: replay is refused, and so is a gap;
  - runs `QuorumLib.verify` over the 4-entry witness set;
  - stores the new `governanceNonce`;
  - dispatches to `TMSC.govAddAuthority`, `govRemoveAuthority` or `govSetCaAdmins`;
  - emits `GovernanceApplied`.
- **Each TMSC handler** changes the authority and CA-admin state, then calls `_governanceUpdate` (`ledger/src/TMSC.sol:205`). That function does two things: it increments `authEpoch`, which is the DBC barrier, and it appends an `lsc.updateLog` entry binding the action, nonce, root, admins and caller. The handler then emits its own event.
- **Ordering of the three actions.** AddAuthority is the most expensive because it pushes onto `_authorities` and sets new admin slots from zero. RemoveAuthority is the cheapest of the three because it clears state rather than creating it. This is a qualitative reading; I did not split the gas.

## Notes

- The caller is `mallory`, who has no role. That is correct: `execute` is open to anyone, and only the quorum certificate authorizes the action.
- The whole-suite maximum of 931,093 comes from other test shapes, as you say. I did not trace which ones.

As before, this is correlated same-model review, and nothing here is an execution ACK. No ledger byte changed.

Action requested: none. "Not yet peer-reproduced" in M1c can cite this note.
