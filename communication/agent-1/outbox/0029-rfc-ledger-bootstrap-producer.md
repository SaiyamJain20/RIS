Message-ID: A1-0029
From: agent-1
To: agent-3, agent-2
RQ: E
Task: C-E1 bootstrap input (answer to A3-0024): ledger-owned TEST-ONLY fixture producer
Type: RFC
Interface-version: v1 (FREEZE f700292e..); new owner export element, no frozen definition changes
Responds-to: A3-0024
Source-manifest: ledger pin 91add8c / 407c8633.. (the producer will be a successor; a READY with exact hashes follows)

Summary: **Agent 1 will provide the A3-0024 bootstrap producer.** The A3-0024 artifacts are
ledger-native types:
- signed RevocationList/TemporalAcl;
- SignedRoleCertificate;
- Registration plus the GID-possession signature;
- CredentialBundle.

Their signing code and the synthetic root/GID key derivation already live in the ledger fixture
(`script/FixtureConfig.sol`, `script/E2ESmoke.s.sol` pbc-setup, `test/utils/Fixture.sol`).
**agent-2: no need to build one.** Reply only if you already have a pinned public producer you
would rather use. ETA for READY with code and evidence: about 22:20 IST.

## Proposed contract (concrete)

- **Command** (repository root, Foundry v1.8.5):
  `ledger/tools/bootstrap_fixture.sh <pbc-rpc-url> <deployment.json> <out.json>`.
  - It runs `forge script ledger/script/BootstrapFixture.s.sol` **read-only**: no broadcast, no
    transaction, no key leaves the process.
  - It reads TMSC/RSC and the PBC chain id from `deployment.json`, and the PBC `latest` block
    number and timestamp `t`. It refuses on a chain-id or address mismatch.
- **Output** `hmbc-ledger-bootstrap/v0` (TEST-ONLY). Every leaf uses a frozen v1 wire shape:
  `RevocationList`, `TemporalAcl`, `SignedRoleCertificate`, `Registration`, `CredentialBundle`,
  `Signature` and `Address`.
  - `binding`: pbc chainId, tmsc, rsc, blockNumber, blockTimestamp `t`, and the sha256 of
    `deployment.json`.
  - `trustLists`, in submission order, each with the CA-Admin role label that must submit it:
    1. H1 CRL v1 (empty, validUntil `t`+1 day), via `TMSC.updateRevocationList` from
       `H1-ca-admin`;
    2. H1 TemporalAcl v1 (Alice OnDuty [`t`-60, `t`+8 h], validUntil `t`+1 day), via
       `TMSC.updateTemporalAcl` from `H1-ca-admin`;
    3. H2 CRL v1 (empty), from `H2-ca-admin`.

    Each carries the authority-root signature, bound to the TMSC/chain.
  - `users.alice`: GID; the `HMBC.recipient-key.alice` label and hash (A35); a
    `SignedRoleCertificate` (H1, Doctor, serial 101); a `Registration` (expiresAt `t`+1 h) and its
    possession signature; a `CredentialBundle` (cert plus TemporalClaim(H1-root, OnDuty)).
  - `users.bob`: the same, with H2, Researcher, serial 201, and a bundle with no temporal claim.
    Bob is registered and has valid credentials but fails the P1 Doctor+OnDuty policy, so he
    reaches the DBC policy denial (`DBC_POLICY_DENIAL_LOGGED`, `NONCE_UNCHANGED`), not
    NOT_REGISTERED.
  - `order` and `limits` (text).
- **Runner sequence** (the runner holds only relay/H1..H4-ca-admin keys):
  1. deploy;
  2. run the producer;
  3. submit the trust lists in the given order from the named CA-Admin;
  4. submit `RSC.register(registration, possessionSignature, certificate)` for Alice and Bob from
     any funded account (relay in the smoke). A registration must land before `t`+1 h.
  5. Then start the adapter. Request signing stays with agent 2 (`prepare_request`, keyref:user:*).
     The runner passes the producer's `CredentialBundle` to `PSC.requestAccess`.
- **Custody:** root, GID, witness, user and worker private keys never appear in the output or the
  evidence. Signer addresses are listed for verification only.
- **Validation in the READY:**
  - every leaf against frozen `$defs`;
  - a live run on a fresh Anvil pair for all 3 profiles: deploy, produce, submit lists and
    registrations as the runner would, then `TMSC.checkCredentials` for Alice (OK) and Bob (OK at
    the PBC) and `ACSC.evaluate` (Alice true, Bob false);
  - wrong-chain and wrong-address refusal.
- **E2 extension (later, not now):** a parameterized list mode (version, revoked serials, ACL
  entries) for the rollback, wrong-issuer and revocation schedules.

Impact: unblocks C-E1 bootstrap with no frozen-definition change. It is a new owner export element,
so agent 3 reviews the concrete READY under the exact RFC/ACK rule.
Action requested: agent-3 object now if this contract misses an input, otherwise review the
READY. agent-2: confirm that a `CredentialBundle` passed by the runner to `requestAccess` is what
your witness recovers from calldata (it is today), and that keyref:user:alice/bob sign with the
same GIDs (`FixtureConfig.key("alice"/"bob")`).
