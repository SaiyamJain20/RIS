# D50 RFC: deployment-bound private state (worker and witnesses) — for review

Author: agent 2. Date: 2026-11-03 (revision 2, 2026-11-04, after A1-0094). **PROPOSAL, NOT ACKED, NOT IMPLEMENTED, NOT FROZEN.**
Revision 2 takes A1-0094 C3 (wiring held in storage that no code hash covers), C4 (sealed state) and folds in agent 1's measured masked-runtime check. Revision 1 is commit 39af20f (file sha256 `f615e0f9..`). Answers D50 (DECISIONS.md), A3-0051 and the D-2 item of A2-0039; covers all seven runtimes
of the F deployment (A3-0055/0056/0057). Claim classes as in `INVENTORY.md`: **[src]** read from source, **[prop]** proposal, **[meas]** measured earlier (A2-0039).

## 1. Problem [src, meas]

`Worker.__init__` binds a state directory to one deployment by hashing `{pbc: [chainId, PSC, RSC], dbc: [chainId, KSSC, ACSC]}` (`worker.py:63-67`) into `meta('deployment')`.
That value does **not** include the profile, the mutation bits, the code, the witness sets or the thresholds, and the addresses of a fresh Anvil pair are the same on every run
(deterministic deployer nonces). A2-0039 measured the same fingerprint `9886222d..` for repaired-e (twice), `mutant-no-nonce`, `mutant-no-receipt-binding`, paper-strict and paper-minimal on fresh
chains [meas]. The E runs were still correct because the runner uses one **new** state directory per deployment; the guard does not enforce it. For F the stakes are higher: four witness stores hold the
single-signing records that the quorum argument relies on, and a record created under one deployment must never be honoured, or silently reset, under another.

The exporter `worker_log.py` copies `meta('deployment')` into `deploymentFingerprint` (line 48-51) and agent 3's `worker_evidence.py` requires exactly that closed field set and an equal
fingerprint (`worker_evidence.py:43-47`). Any new field in the exporter's default output would break that strict check.

## 2. Proposed binding

Keep the old value and add one stronger value. For every private store (worker store and each witness store):

| `meta` key | Value | Role |
|---|---|---|
| `deployment` | the existing v1 fingerprint, **same formula, same bytes** | exported unchanged, so the evaluator's recomputation keeps working |
| `binding_v2` | `sha256( "hmbc-deployment-binding/v2\n" \|\| canonical_json(B) )` | the stronger identity |
| `binding_v2_doc` | `canonical_json(B)` | forensic diff when a refusal needs explaining |
| `owner` | `"worker"` or `"witness:0x<address>"` | one store, one role, one key; kept **outside** `B` so all stores of one deployment share one `binding_v2` |
| `schema` | integer, 2 | store layout version |

`canonical_json` = Python `json.dumps(B, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`; integers are decimal strings; addresses and hashes lowercase `0x` hex.

`B` (field set; E deployments omit the Governance entries, F deployments include them):

```
interfaceVersion          manifest.interfaceVersion
profile                   {name: manifest.profile, enum: manifest.profileEnum}
chains.<pbc|dbc>:
  chainId                 manifest chain id (also checked against eth_chainId, as chain.py already does)
  genesisHash             hash of block 0, read live
  deployBlock             {number: manifest.deployBlock, hash: hash of that block, read live}
  contracts.<Name>:       address                       manifest, lowercase
                          codeSha256                    sha256(eth_getCode(address, "latest")), read live
                          abiSha256                     manifest (already compared with the bundled ABI by ledger.py)
                          runtimeSha256                 manifest (compiled runtime, immutable slots zeroed)
immutables.<Name>:        {profile, mutations}          read live through the public views of TMSC, PSC, KSSC, ACSC (and Governance: mutations)
witnessSets.<psc|kssc|governance>:
                          {version, threshold, witnesses[]}   read live from the contract (storage, so not covered by any code hash), contract order, lowercase
wiring (storage set by wire(); no code hash covers it, A1-0094 C3):
                          {ksscForChain: PSC.ksscForChain(dbcChainId), acsc: KSSC.acsc(), kssc: ACSC.kssc(), pscRelay: ACSC.pscRelay(),
                           tmsc: {psc: TMSC.psc(), rsc: TMSC.rsc()}, lsc: {rsc: LSC.rsc(), tmsc: LSC.tmsc(), psc: LSC.psc()},
                           governance (repaired-f only): {tmsc: TMSC.governance(), target: Governance.target()}}
                          PSC.rsc/tmsc/lsc and RSC.tmsc/lsc are immutables, so the code hash already covers them; they are still cross-checked against the manifest addresses (cheap).
```

Contract sets: PBC `LSC, TMSC, RSC, PSC` (+ `Governance` under repaired-f); DBC `ACSC, KSSC`. That is the **six** E runtimes and the **seventh** (Governance) for F.

Deliberately **excluded** because governance changes them at run time and they would make the identity drift: the authority list, CA-admin sets, revocation lists and ACLs, `authEpoch`, `policyVersion`,
checkpoints, nonces, grants, the governance nonce. The binding identifies the deployment, not its current state.

## 3. Where each value comes from and what is trusted [prop]

The **pinned manifest** is the runner's trusted-setup statement (E: Option A, the runner deploys and pins). The **chain** is trusted under the safe-ledger assumption through the loopback RPC the adapter is pinned to.
At open, in this order, fail-closed:

1. Read every value of `B` live from the two chains.
2. Compare each manifest-asserted value that is also readable live (addresses have code; profile name/enum; `mutations`; the manifest witness set against `PSC/KSSC/Governance.witnesses()`, `threshold()`, `witnessSetVersion()`; ABI hashes as today).
   Also require (A1-0094 C4) `configured() == true` on all six contracts (Governance has no bootstrap): an unsealed deployment can still be rewired after binding. And require the wiring above to be **bidirectionally consistent** with the manifest addresses, in particular `TMSC.governance() == Governance` and `Governance.target() == TMSC`: a Governance whose target is not the TMSC that trusts it, or the reverse, would otherwise still bind.
   Mismatch refuses **before any store is opened**, with the existing closed error classes: deployment, code, wiring or unsealed state `WRONG_DESTINATION` (the closest closed class; agent 3 confirms the mapping), profile `WRONG_PROFILE`, set or version `STALE_STATE`.
3. Require that PSC, KSSC and Governance hold the **same** witness addresses, threshold and version (this is A1-0088 L11, which the E witness checks only for the version, `witness.py:41`), and that the store's key is a member of all of them.
4. Compute `binding_v2`. Open the store. A fresh store inserts `binding_v2`, `owner` and `schema`; an existing store must carry equal `binding_v2`, `owner` and `schema`, else refuse.

Compute once when the adapter starts with `--deployment` (the runner pins the deployment after bootstrap, so the chains are up) and cache the result. Per operation, re-verify only `genesisHash` and the stored `deployBlock`
hash, which the witness observation tripwire (`SIGNING-RULES.md` section 6) already reads. The cost is **unmeasured**: roughly 35 JSON-RPC reads at start and none extra per operation; the implementation task measures it.
**Timing risk to state:** E's tightest recorded margin was 3.44 s at a repaired-e release (A2-0038). The start-time computation must not fall inside a timed window; per-operation work must stay at the existing RPC count.

## 4. Immutable handling

- Immutable constructor values (profile, mutations, chain ids, addresses, threshold) are embedded in the deployed code, which is why `runtimeSha256` in the manifest (compiled code with immutable slots zeroed, `export_abi.py:59-65`)
  cannot be compared with `eth_getCode` directly. The identity above uses the **live code hash**, which includes the immutable values, and also reads the immutables through their public views.
  That is sufficient to separate any two deployments that differ in a profile, a mutation bit, a threshold or any contract byte.
- The live-code identity alone does **not** show that the deployed code is the **compiled build** the manifest names: a deployer could publish a deviating source whose manifest still carries the honest `runtimeSha256`, and the identity would simply bind to that code.
  Closing that is the masked comparison (zero the immutable ranges in `eth_getCode`, hash, compare with the manifest's `runtimeSha256`), which needs agent 1's `immutableReferences` per contract.
  **Measured by agent 1 on the E code (A1-0094, `ledger/evidence/f0-d50-masked/`, one host, one trial per profile, Forge/Anvil 1.8.5):** on fresh chain pairs repaired-e, paper-strict and mutant-no-nonce get identical addresses (reproducing D-2); the raw live code hash differs across the three profiles for TMSC, PSC, ACSC and KSSC; LSC and RSC raw hashes are identical (no profile immutables); the masked comparison equals the compiled and manifest `runtimeSha256` for **18 of 18** instances. Consequence for this RFC: the profile separation of the identity rests on TMSC, PSC, ACSC and KSSC plus the addresses and the storage reads, not on LSC or RSC. Governance (the seventh runtime) is unmeasured because it does not exist yet.
  **Agreed with agent 1 (A1-0094):** `exports/abi/manifest.json` gains `contracts.<C>.immutableReferences` in the successor schema, a sorted list of `{start, length}` in decimal flattened from the Forge artifact's `deployedBytecode.immutableReferences` (AST ids dropped); the algorithm is `ledger/tools/check_masked_runtime.py` (zero the ranges, sha256, compare with `runtimeSha256`, require equal length). Agent 3 owns the schema; the v1 export is unchanged. Once the field exists the witness/worker performs the masked build check at open; until then the build check is **not performed** and the report must say so.
- The v1 `runtimeSha256` values stay in `B` as manifest-asserted strings (not live-derived), so a changed manifest changes the binding even before the masked check exists.

## 5. Old-state migration and refusal [prop]

- A store created by E code has `meta.deployment` and no `binding_v2`. If it holds any row (`records`, `releases`, `events`, or any witness table) it is **refused** with `WRONG_DESTINATION` "unbound legacy state".
  An empty store (schema only) is bound on first open. There is **no adopt command**: E state directories are evidence archives and the runner already uses new directories; adoption would record a weaker provenance as a stronger one.
  (If a future need arises it is a separate, explicit, logged operation with its own RFC.)
- A missing store next to an `INITIALIZED` marker, a failed `PRAGMA integrity_check`, a missing `binding_v2` in a store that has the marker, or a wrong `owner` or key is refused; the witness never creates a replacement store silently. [prop]
- The exported `deploymentFingerprint` and the exporter's default output stay byte-identical. A new opt-in `python -m hmbc_protocol.worker_log --state-dir D --binding` prints `{owner, binding_v2, document}` and nothing else.
  The evaluator may adopt it; nothing breaks if it does not. Agent 3 decides whether the evaluator recomputes `binding_v2` from the manifest and the chains (an independent check) or only reads it.

## 6. Controls a future implementation must pass (test-first, none exists) [prop]

Refusals (each must fail on the unmodified deployment's own store and must not create or modify a store):
same addresses and chain ids with a different profile; with a different `mutations`; with a different witness set, threshold or version in any of PSC, KSSC, Governance; with different code at one address; with a different genesis (chain restarted);
PSC and KSSC disagreeing on witness addresses; a store key not in the set; a witness-3 store opened as witness-2; a legacy E store with rows; a corrupt `meta`; a store missing next to its marker; a manifest whose asserted value differs from the chain;
a deployment with `configured() == false` (C4); `TMSC.psc/rsc` or `LSC.rsc/tmsc/psc` differing from the manifest addresses (C3); under repaired-f `TMSC.governance()` not equal to Governance, or `Governance.target()` not equal to TMSC, tested in both directions (C3); once `immutableReferences` exists, code that differs from the compiled build in one non-immutable byte (masked mismatch).
Positive controls: reopen the same deployment (worker and each witness); restart across adapter processes; `export --check` and the default exporter output byte-identical; a Governance-carrying F deployment binds seven runtimes; the masked build check passes on an honest deployment of every contract (agent 1 measured 18 of 18 on E).
Source-edit mutants for `tools/mutation_check.py`: skip the mutations comparison, the code hash, the genesis check, the owner check, the legacy refusal, the cross-contract set equality, the `configured()` check, the storage-wiring comparison, the Governance/TMSC bidirectional check, the masked build comparison. A mutant that survives is a gap.

## 7. What this does not do

It does not prove the code is the compiled build (section 4), does not bind a store against a **consistent rollback** of the whole directory to an older valid copy (INVENTORY, FM-14), does not authenticate the runner's
manifest beyond what the chain confirms, does not change any E pin, interface-v1 byte or exported field, and does not claim zero evaluator impact (section 3 names two ways it can matter: refused state reuse, added start-up RPCs).

## 8. ACKs requested

| From | What |
|---|---|
| agent 1 | A1-0094 (not yet an ACK) confirmed the views on the six E contracts and the Governance getters against design 2.1, agreed to export `immutableReferences` in the successor schema, and returned C1-C4; this revision takes C3 and C4. Remaining: ACK this exact revision, and add `TMSC.governance()` to design 2.1 if it is not already a public getter there (it is listed in A1-0094 C3 as a view under repaired-f) |
| agent 3 | accept the formula and encoding as the D50 interface; decide whether the evaluator reads or recomputes `binding_v2`; confirm the closed error-class mapping; fold the refusal controls into the F plan |
| both | exact revision (this file's sha256 in the message that carries it) |
