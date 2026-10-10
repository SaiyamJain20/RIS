# SL5 actual run: E02 trust freshness ×6, all PASS

Paper-derived HMBC2020 reconstruction. Synthetic only. Symbolic adapter, with safe-ledger,
trusted-worker and one-trusted-witness assumptions. E/RQ1 is active; gate E is NOT_RUN; F and G are
locked.

**Solo phase (A1-0059):** every review and ACK is **correlated self-review**.

## Run

**Authorization:**

- Plan `evaluation/evidence/e2/sl5-trust-runner-20261010/integration-plan.json`, SHA-256
  `9e14a148e4e0b61989e107418874aaa7b11a4a011c6a2743a5c9f597283a01b0`.
- FREEZE S3-0015, ACKs A1-0072 and S2-0015, all at 7eed12d.
- `acks.json` was verified by the solo verifier before services.

**Command** (`export PATH="$HOME/.foundry/bin:$PATH"`):

```
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl5-trust-runner-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl5-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl5-run/real-e2-output
```

**Result:** exit **0**, `E2_TRUST_STRESS_SLICE_PASS`, 2026-10-10T17:57:29Z to 18:06:20Z, **531.40 s**.
Stderr is empty. `sourceStable: true`.

## Results against the frozen catalog (`catalog-coverage.json`)

| Row | Frozen expected | Observed | Class |
|---|---|---|---|
| E02-wrong-issuer-paper-strict | REJECT / UNAUTHORIZED_CALLER | fresh H2 CRL v2: H2-admin `eth_call` returns generation 2; H1-admin submission gives `Rejected(16)`, no events, nothing changed | **SUPPORTED** |
| E02-wrong-issuer-paper-minimal | same | same | **SUPPORTED** |
| E02-wrong-issuer-repaired-e | same | same | **SUPPORTED** |
| E02-signed-list-rollback-paper-strict | ACCEPT / SPEC_GAP | v2 (revoke 101) installed: Alice REVOKED(19). Bootstrap v1 replay **accepted** (generation 3, version 1): Alice **un-revoked**. Her request (authEpoch 5) is forwarded with H1 record `anchorVersion` 1 | **SPEC_GAP** |
| E02-signed-list-rollback-paper-minimal | same | same | **SPEC_GAP** |
| E02-signed-list-rollback-repaired-e | REJECT / STALE_ANCHOR | v2 installed: Alice REVOKED. Replay gives `Rejected(5)`, no events, v2 retained. Her request (authEpoch 4) gives `AccessDenied` REVOKED(19), no record, `denialCount` 1 | **REPAIR_SUPPORTED** |

**All 6 rows match the frozen classification, error and outcome.**

### Repaired-e rejection: line 190, not 192

The repaired rejection comes from TMSC.sol:190 (version order), not 192 (list expiry). The replayed
bootstrap list was still valid at replay: `validUntil` 1791741959 > replay block time 1791655576.

### Current authEpoch (A1-0064)

Each request carried the authEpoch read just before it: 5 in the paper profiles, 4 in repaired-e. The
runner re-read it at the request block and it was unchanged.

## Owner producer (`ledger/tools/sign_list.sh`, A1-0034, A1-0061 D-6)

| Rows | Exit | Time |
|---|---|---|
| `crl H2` (wrong issuer ×3) | 0 | ≤ 1.9 s |
| `crl H1 --revoke 101` (rollback ×3) | 0 | ≤ 1.9 s |

- **Pinned bytes:** `sign_list.sh` and `SignList.s.sol` were re-hashed before each call.
- **Same deployment:** the deployment file was the stress adapter's.
- **Artifact checks:** every artifact was checked before use, including the root signature under the
  evaluator's own HMBCTrust encoder.
- **Published:** `trust-stress/signed-list.json`.
- **Not published:** the raw `trust-sign-list-NN.{json,txt}` files. They stay in the private run
  output.

## Worker-DB precondition (D49), every step

The D2 worker was observed at baseline and after every catalog step:

- wrong issuer: WRONG_ISSUER_UPDATE;
- rollback: INSTALL_NEW_LIST, REPLAY_OLD_LIST, REQUEST_ACCESS.

Every observation was the identical verified never-instantiated record. 24 probes ran in total.

## Controls

Every row's D1 passed: wrong-admin 16, Alice allow with release and one outcome, Bob deny 9. Every D2
bootstrap also gave wrong-admin 16.

## Integrity (`live-result-audit.json`, `source-bracket.json`)

- **Processes:** 12 Anvil services and 12 adapters, all exited 0; all PIDs are absent; ports 18545
  and 18546 are free.
- **Per profile:** sources stable, services stopped, and the Cast checkpoint stable (12 checkpoint
  files, all OK).
- **Commands:**
  - 78 owner commands: 0 unexpected non-zero exits, 24 verified never-instantiated probes (exit 1,
    expected), and 6 producer calls (exit 0);
  - 5635 RPC calls, all exit 0.
- **Independent bracket:** 3049 files, 2e444340.. before and after. HEAD was 7eed12d throughout.
  `versions.json` was recorded before the run.

## Never-publish scan (`selected-manifest.json`)

- **Selection:** 253 JSON files, 0 refused, all byte-identical to the run output (checked with `cmp`).
- **Per row, unmodified:**
  - `trust-instance/{deployment,bootstrap-checked}.json`;
  - `trust-instance/{pbc,dbc}-native/*`;
  - all of `trust-stress/*`.

  That is 108 keep-set files.
- **Excluded:** every `.txt` (including producer logs), `private-adapter-state`, snapshots and RPC
  transcripts.
- **Substring scan:**
  - the TEST-ONLY keys of 15 labels, including the H1 and H2 **root** keys used by the producer;
  - every frozen-vector `signerPrivateKey`, including witness-1;
  - the 6 release tokens from the private worker databases (D1 Alice controls only).

  Result: **0 hits**.

## Points stated per A1-0072 (interpretation, not defects)

1. **Wrong issuer is not a repaired-e property.** All three profiles reject at the same line,
   TMSC.sol:181. This is a baseline caller restriction (D-record N-1) and is not counted as repair
   evidence.
2. **STALE_ANCHOR is ambiguous by code, so the line is named: 190, not 192.** The liveness check
   above shows it. The killing mutant, MUT_NO_VERSION_MONOTONE, is deferred to P3.
3. **The paper rollback outcome depends on what v2 changed.** Here v2 revokes Alice, so the rollback
   **un-revokes** her: a revoked credential becomes usable again. The general paper statement is that
   the latest appended list is current, with no version ordering or list expiry.
4. **CRL only.** TempACL rollback has the same `_checkFreshness` path (TMSC.sol:155) but was **not
   run**.

## Limits

- One trial per row. Single-host Anvil, with no consensus or finality.
- The actor is an authorized issuer-scoped administrator. These are reconstruction results, not HMBC
  exploits.
- Symbolic adapter.
