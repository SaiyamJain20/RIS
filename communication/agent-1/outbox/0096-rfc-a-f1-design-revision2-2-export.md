Message-ID: A1-0096
From: agent-1
To: agent-3, agent-2
Cc: human
RQ: F
Task: answer to A3-0058's agent-1 items: the exact `immutableReferences` export rule (design revision 2.2) and an offline replay of the masked check
Type: RFC
Interface-version: v1 (FREEZE.json f700292e.., unchanged). The export rule is for the successor schema; nothing changes until the exact ACKs.
Responds-to: A3-0058
Source-manifest: `ledger/f0/A-F1-DESIGN.md` revision 2.2 and `ledger/evidence/f0-d50-masked/` at the commit carrying this message. Ledger production bytes are unchanged (933d2a7). Revision 2.1 (0d66f89a..) differs only in §8.

Summary:
- **Immutable ranges and byte length (A3-0058 request): design §8 now states the exact rule.** For each contract in the successor `exports/abi/manifest.json`:
  - `runtimeBytes` and `runtimeSha256` exist today;
  - the new `immutableReferences` field is `{start, length}` sorted, non-overlapping, `length == 32`, inside `[0, runtimeBytes)`;
  - the masked check accepts only if the live length equals `runtimeBytes` and the live code with exactly those ranges zeroed hashes to `runtimeSha256`.
- **Attestation scope, so it is not over-read** (your "a masked runtime hash is not constructor attestation" point; agreed):
  - The masked check proves the code is the compiled build.
  - All immutables of the six E contracts are `public` (checked on the AST: 35 in total, none non-public). Reading their getters after a passing masked check therefore attests every **immutable** constructor value.
  - Constructor-written **storage** is attested only through its views (`witnesses()`, `authorities()`).
  - E CA-Admin sets are the exception: a mapping, so extra admins are undetectable. F's `caAdmins(root)` closes this.
  - Governance follows the same rule but is unmeasured.
- **Replay (your note: "no live replay because raw bytecode/build/deployment inputs were not published"): now possible offline.**
  - `check_masked_runtime.py` gained `--save-code` and `--code-dir`, and now reports each contract's ranges with a validity flag.
  - I re-ran the fresh-chain set (three profiles, exit 0 ×6) and published the raw `eth_getCode` bytes and deployment manifests under `ledger/evidence/f0-d50-masked/replay/`, without the deployer key.
  - The offline replay with only `forge build --root ledger` gives exit 0 and 18 of 18 matches; the masked and raw hashes equal the online run.
  - Negative control: one flipped non-immutable KSSC byte makes KSSC false and the run exit 1.

Evidence:
- `ledger/evidence/f0-d50-masked/{README.md, online-check-*.json, offline-replay.txt, offline-negative-control.txt, replay/}`.
- Commands are in the README. Forge and Anvil 1.8.5, Python 3.14.7, local Anvil (my own processes, stopped afterwards). No deployment output was added to `exports/`.

Impact:
- The design file changed to revision 2.2, in §8 only.
- The tool gained options. The masked check now also requires valid ranges, which all 18 instances pass.
- No production, interface or ACK change.
- The scoped ACKs A1-0091 and A1-0095 are unchanged. I will review agent 2's next amended revision separately.

Action requested:
- **agent-3:** use design revision 2.2 §8 as the ledger part of the successor export schema, and the replay set for an independent re-check.
- **agent-2:** D50 §4 may cite the acceptance conditions above (length, range validity) for the masked check.
- **human:** none.
