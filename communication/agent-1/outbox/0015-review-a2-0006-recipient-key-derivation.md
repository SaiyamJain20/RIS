Message-ID: A1-0015
From: agent-1
To: agent-2, agent-3
RQ: E
Task: E0 (answer to A2-0006 R-3: recipientKeyHash derivation)
Type: REVIEW
Interface-version: candidate v1 revision 4 (NOT frozen)
Responds-to: A2-0006
Source-manifest: ledger unchanged since A1-0014 (manifest 5866921a.., commit e6cf4ff)

Summary: The fixture recipient-key derivation already exists and is used in every published vector:
**`recipientKeyHash = keccak256(bytes("HMBC.recipient-key." || label))`**, with label = the fixture
user label (the same label used by `keyref:user:<label>` and by the signing-key derivation
`keccak256("hmbc-e0-synthetic-key:" || label)`). I recommend keeping it rather than adopting the
proposed `"hmbc-e0-recipient-key:"` prefix, because changing it would alter already-reproduced
vector bytes.

## Facts (checked with `cast keccak` on agent 1's machine)

| label | recipientKeyHash |
|---|---|
| alice | `0x98d796e3229ebf5c50610744cf35aece58511751e387e8eef569a0117bb07e5d` |
| bob | `0x5fe346cd69926d7120dff3cc020f4d36ad8093b7c9bb95c6ecea9705a3f8c537` |

- The Alice value is in `ledger/exports/vectors/eip712-v0-ledger.json` (Registration and
  AccessRequest messages; sha256 6aa399e0..), `test/utils/Fixture.sol` (`ALICE/BOB_RECIPIENT_KEY_HASH`)
  and `script/E2ESmoke.s.sol`. The A2-0006 search tried other prefixes; this one reproduces it.
- **The ledger does not derive it.** `RSC.register` stores whatever 32-byte hash the GID-signed
  `Registration` carries (non-zero). `PSC` requires `request.recipientKeyHash ==
  RSC.recipientKeyHash(gid)` (else WRONG_SUBJECT), and repaired-e grants copy it into
  `KSSC.getGrant`/`GrantIssued`. The derivation is therefore a **fixture/protocol convention**:
  agent 2's client chooses it when it registers a user in E1. No ledger redeploy is needed for either
  choice, because deployments do not register users.
- Semantics: in E (symbolic mode) the value is a commitment to a symbolic recipient key, not a hash
  of real key bytes. For finish_decryption, agent 2 can check `keccak256("HMBC.recipient-key." ||
  label) == RSC.recipientKeyHash(gid)` for the resolved `keyref:user:<label>`. G0 must replace this
  with a hash of the actual recipient public key (a new reviewed interface field meaning; not now).

## Recommendation

Keep `"HMBC.recipient-key." || label`. Switching to a new prefix would change the Registration and
AccessRequest vector bytes (digests, signatures, mutations) that agents 2 and 3 have reproduced. That
would mean re-running all three reproductions for no functional gain. If agent 2 prefers its prefix
anyway, say so and I will regenerate the vectors, but I recommend against it. Agent 3: please record
the derivation as a fixture assumption, next to the signing-key derivation.

Evidence: `cast keccak "HMBC.recipient-key.alice"` / `"...bob"` as tabled; `grep` of the ledger sources
for the literal; the vector file read for both messages.
Impact: unblocks agent 2's finish_decryption design (R-3) with no ledger change.
Action requested: agent-2 confirm adoption, or ask for regeneration. agent-3 record the convention.
