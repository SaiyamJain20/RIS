# Cross-module contract v0

Owner: agent 3. Status: proposed; **E0 must freeze v1 with byte-exact test vectors acknowledged by agents 1 and 2**. Fields reserved for F/G are fixed constants in E. This document specifies the team's extension, not a wire protocol claimed to exist in HMBC.

## 1. Types and encodings

- `Address`: a 20-byte Ethereum address. JSON uses lowercase `0x` plus 40 hexadecimal digits.
- `Hash`: 32 bytes; JSON uses lowercase `0x` plus 64 hexadecimal digits. Use Keccak-256 for Ethereum commitments, SHA-256 for file manifests; never confuse the two.
- Unsigned integers use decimal strings in JSON, concrete `uint*` types for ABI/EIP-712. Reject negatives, floats, overflow, unknown fields and missing fields.
- Signatures are 65-byte secp256k1 Ethereum signatures; use a reviewed recovery library with canonical signature checks. Verify a recovered signer, not a caller-supplied identity label.
- EIP-712 is the signed encoding. JSON is transport only; no ad hoc hash of JSON serialization. Freeze Solidity/Python matching digests in `interfaces/vectors/` before service integration.
- Schema, fixture, error and profile names are case-sensitive. Timestamps are seconds in the experiment's controlled clock.

### AccessRequest — exact field order

```text
AccessRequest(uint256 sourceChainId,uint256 destinationChainId,address psc,address kssc,address gid,bytes32 dataId,uint8 action,uint64 policyVersion,uint64 authEpoch,uint64 keyEpoch,uint256 nonce,uint64 expiresAt,bytes32 recipientKeyHash)
```

The EIP-712 domain is `{name: "HMBCRequest", version: "1", chainId: sourceChainId, verifyingContract: psc}`. `action=1` means read. `gid` is the registered user's signing address; RSC registration must prove possession and bind the recipient encryption key hash. Authority-issued role certificates refer to that GID. The destination KSSC address and chain are also part of the signed payload.

`requestDigest` is the complete EIP-712 digest. The profile, authorities and trusted keys come from the deployment manifest; a request cannot change them. In E/F `keyEpoch=0`; in E `witnessSetVersion=1` and exactly one configured witness is required.

### AccessDecision

```text
AccessDecision(bytes32 requestDigest,uint8 result,bytes32 credentialDigest,uint64 stateSequence,uint64 witnessSetVersion,uint256 sourceBlockNumber,bytes32 sourceBlockHash,uint64 expiresAt)
```

Domain: `{name: "HMBCDecision", version: "1", chainId: destinationChainId, verifyingContract: kssc}`. `result=1` is allow; `result=0` is deny. `credentialDigest` commits to a fixture-defined, ordered list of verified issuer/role/status records; E0 fixes that structure in the schema/vectors. Its records accompany the decision so ACSC can evaluate the policy and rehash them. Do not accept relay-asserted attributes with no decision binding.

Witnesses sign only a decision they independently recompute from the accepted source state. A source block hash in a message is not a light-client proof: the receiver's trust is in the configured witnesses plus their source-ledger assumption.

`DecisionCertificate` is `{decision, signatures}`. Signatures must recover unique configured witnesses; sorted signer order is mandatory. q=1 of 1 in E; q=3 of 4 in F/G. Reject duplicates, unknown signers, wrong destination, a wrong request digest, stale state and an old witness-set version. A rejected certificate changes no authorization/nonce state; a valid deny may produce a denial audit record but never a grant.

### StateCheckpoint

```text
StateCheckpoint(uint64 sequence,uint64 authEpoch,uint64 policyVersion,uint64 keyEpoch,uint64 witnessSetVersion,uint256 sourceChainId,address psc,uint256 sourceBlockNumber,bytes32 sourceBlockHash,uint64 expiresAt)
```

Domain: `{name: "HMBCState", version: "1", chainId: destinationChainId, verifyingContract: kssc}`. The same profile quorum authenticates it. Each accepted sequence is strictly increasing. Epochs/versions cannot decrease. A checkpoint expires after at most **60 seconds**; a request and decision expire after at most **30 seconds** from the signer's observed experiment time and may not outlive the checkpoint. These are proposed experiment parameters, not HMBC constants. Test boundary equality: `now >= expiresAt` rejects.

The current checkpoint is the DBC's explicit state view. **Revocation becomes effective for new grants when the DBC accepts the checkpoint containing it.** Before that barrier, an old certificate can still be valid; measure this window. Previously consumed grants are already authorized operations and may complete until their expiry. This protocol does not promise instantaneous revocation across asynchronous chains. Report PBC-to-DBC checkpoint lag separately.

### Contract-facing methods

Agent 1 defines the ABI with these conceptual operations; E0 freezes concrete Solidity tuple types and ABI JSON:

```text
RSC.register(gid, recipientKeyHash, possessionSignature)
TMSC.updateTrustAnchor(authority, version, validUntil, anchorDigest, issuerSignature)
PSC.requestAccess(request, userSignature, credentialBundle) -> requestDigest
KSSC.acceptState(checkpoint, signatures)
KSSC.consumeDecision(request, decisionCertificate, credentialBundle) -> grantId
KSSC.getGrant(grantId) -> (requestDigest, dataId, gid, keyEpoch, expiresAt, allowed)
LSC.recordOutcome(requestDigest, grantId, outcomeDigest)
```

RSC is called by the authorized issuing/registration path; the possession signature proves control of `gid`. Trust-anchor updates are scoped to their issuer. The TMSC method binds an action-specific signature, not an untyped challenge. Do not allow a registration signature to authorize anchor changes. Contract events may supply return values when a transaction cannot synchronously return them to an external client.

`consumeDecision` checks all bindings before consuming `(gid, nonce)`. Success commits the nonce and grant event atomically on the DBC. `grantId = keccak256(abi.encode(requestDigest, kssc, destinationChainId))`. ACSC is invoked by the KSSC/authorized DBC path. Replay returns the existing grant through a read API; it cannot execute a new state transition.

`recordOutcome` validates the configured outcome reporter and binds the original grant/request; arbitrary users cannot forge another user's audit event. F requires the configured quorum authorization for security-relevant updates. Agent 1 documents exact call permissions for all six contracts, including functions omitted from the minimal reconstruction.

## 2. Key worker and client boundary

Agent 2 provides a Python API behind a thin local JSON-lines adapter. Agent 3's runner depends only on that adapter and declared artifacts, not internal Python imports.

```python
prepare_request(request: dict, signing_key_ref: str) -> dict
collect_decision(request_digest: str, deployment: dict) -> dict
release(grant_id: str, deployment: dict) -> dict
encrypt_record(record: dict, policy: dict, key_epoch: int) -> dict
finish_decryption(response: dict, user_key_ref: str) -> dict
rotate_epoch(target_epoch: int, deployment: dict) -> dict
```

E/F `encrypt_record` and `finish_decryption` operate in `adapterMode="symbolic"`; their results assert modeled decryptability only. The G real adapter uses `adapterMode="abe-real"` and reports its scheme/version/parameters. `rotate_epoch` returns `NOT_IMPLEMENTED_IN_PHASE` before G; no fake successful rotation.

Key references are private local handles; JSON never carries a master secret, temporal key or plaintext key to the runner's public report. `release` independently loads the committed grant, verifies its current validity and input bindings, and durably stores intent/cache state before transmitting the response. Repeated calls return the same encrypted response while permitted. A first call after grant expiry fails. Return cached material only according to the frozen retry policy; do not silently extend its authorization lifetime.

Output response binds `{schemaVersion, adapterMode, requestDigest, grantId, dataId, keyEpoch, ciphertextDigest, recipientKeyHash, responseEnvelope}`. The encrypted envelope's concrete scheme/AAD and the ABE ciphertext/partial-decryption schema are frozen in G0 with test vectors. E0 may use symbolic payload tokens; that choice cannot leak into G results unnoticed.

## 3. Module command boundary

These commands are **planned interfaces**, not installed commands today. Agent 3 supplies the root Python environment/lockfile; agent 1 supplies the ledger dependency locks.

```bash
# Agent 1: isolated contract suite
forge test --root ledger

# Agent 2: isolated service suite
python -m pytest protocol/tests -q

# Agent 3: independent oracle and integration suites
python -m pytest evaluation/tests -q
python -m evaluation.run --rq E --profile repaired-e --output evaluation/runs/<run-id>
python -m evaluation.gate --rq E --run evaluation/runs/<run-id>
```

`evaluation.run` supports E/F/G and every declared profile only when implemented. It starts dedicated processes through adapter manifests, runs the fixture list, captures exit codes, and cleans up only processes it created. Default integration ports are PBC 18545, DBC 28545; acquisition/ownership is recorded in `communication/INTEGRATION.md`. Never kill a process just because it occupies a chosen port. Unit tests use in-process/mocked providers or different allocated ports.

Ledger output: `ledger/exports/abi/*.json` and deployment manifest with schema version, chain IDs, addresses, compiler/dependency/source hashes, profile, witnesses and epochs. Agent 1 is its sole writer. Agent 2 reads it. Generated exports have stable schema; volatile build caches are ignored.

Protocol output: `protocol/exports/adapter.json` describing supported operations/modes/schema version. Agent 2 is its sole writer. Agent 3 reads it. Agents publish sample manifests early so peers can implement against fixtures.

The evaluation JSON-lines runner request is `{schemaVersion, operation, input, deploymentManifest}`; response is `{schemaVersion, ok, result, error}` with exactly one of result/error populated. Unknown operation or mode fails explicitly. No request includes arbitrary executable code or shell commands.

Error codes: `BAD_SIGNATURE`, `WRONG_SUBJECT`, `WRONG_DESTINATION`, `UNKNOWN_AUTHORITY`, `STALE_ANCHOR`, `STALE_STATE`, `EXPIRED`, `REPLAY`, `POLICY_DENIED`, `INSUFFICIENT_QUORUM`, `DUPLICATE_SIGNER`, `WRONG_EPOCH`, `NOT_COMMITTED`, `ADAPTER_UNAVAILABLE`, `NOT_IMPLEMENTED_IN_PHASE`. Tests assert a stable reason class, not compiler-dependent text.

## 4. Scenario and evidence records

`Scenario` fields: `id`, `rq`, `profile`, `sourceRefs`, `assumptions`, `fixture`, `faultSchedule`, `expectedClass`, `expectedEvents`, `expectedError`, `adapterMode`. Timing comes from an injected clock; probabilistic schedules record a seed. An oracle's expectation is written before the implementation result is observed.

`RunManifest`: `runId`, `rq`, `profile`, `interfaceVersion`, `adapterMode`, `sourceManifest`, `toolVersions`, `commands`, `inputHashes`, `seed`, `startedAt`, `endedAt`, `exitCodes`, `resultFiles`.

`ScenarioResult`: `scenarioId`, `classification`, `observedEvents`, `assertions`, `latencyMs`, `gasUsed`, `encodedBytes`, `limitations`, `evidencePaths`. Failed/time-out trials remain in denominators. Public event evidence uses hashes; full synthetic fixture records can be private run artifacts.

The fields above are mandatory but not a substitute for JSON Schema. Agent 3 creates versioned schemas and valid/invalid vectors in E0; agents 1/2 acknowledge them. Unsupported extra fields reject by default. Breaking changes require a new version, an RFC and renewed integration acknowledgment.
