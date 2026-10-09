# SL1 actual run: E01 subject substitution ×3, all PASS

Paper-derived HMBC2020 reconstruction. Synthetic only. Symbolic adapter, with safe-ledger,
trusted-worker and one-trusted-witness assumptions. E/RQ1 is active; gate E is NOT_RUN; F and G are
locked.

**Solo phase (A1-0059):** agent 1, agent 2 (proxy) and agent 3 (proxy) are the same model, so every
review and ACK is **correlated self-review**.

## Run

**Authorization:**

- Plan `evaluation/evidence/e2/sl1-subject-runner-20261009/integration-plan.json`, SHA-256
  `6fd5809b3b79963ea7094ca63c04b60c8991313ac94bb8823320939d663f1f96`.
- FREEZE S3-0005 (commit aabed5b). ACKs A1-0062 (aabed5b) and S2-0004 (77a7c1f).
- `acks.json` was verified by the evaluator's solo verifier before any snapshot or service. It
  checks committed blobs, ancestry of HEAD 77a7c1f, headers and the exact plan hash.

**Command:**

```
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl1-subject-runner-20261009/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl1-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl1-run/real-e2-output
```

**Result:** exit **0**, `E2_SUBJECT_SUBSTITUTION_SLICE_PASS`, 2026-10-09T19:43:44Z to 19:48:00Z
UTC (2026-10-10 IST), **255.73 s** wall. Stderr is empty. Details in `real-e2.json`.

**Configuration:**

- Each row ran on a fresh Anvil 1.8.5 pair: PBC port 18545 (chain ID 18545), DBC port 18546 (chain
  ID 28545). Automining, cancun.
- Owner pins: ledger 933d2a7 (195 entries) and protocol 0716a8e (108 entries), materialized from Git
  blobs.
- Python 3.13.5 (frozen 3.13.13). Agent 1 aligned the `.venv` transitive packages to `uv.lock`
  before the run.

## Results against the frozen catalog (`catalog-coverage.json`, catalog 438fa38d..)

| Row | Frozen expected | Observed | Class |
|---|---|---|---|
| E01-subject-substitution-paper-strict | CONDITIONAL / SPEC_GAP | Paper flow, see below; release margin 29 s | **SPEC_GAP** |
| E01-subject-substitution-paper-minimal | CONDITIONAL / SPEC_GAP | Same; release margin 28 s | **SPEC_GAP** |
| E01-subject-substitution-repaired-e | REJECT / REPAIR_SUPPORTED / WRONG_SUBJECT | Mined status 0, `Rejected(2)` WRONG_SUBJECT, no logs. Whole grant, request, nonces, access count, both chains' histories and idle worker unchanged. No release | **REPAIR_SUPPORTED** |

**What was observed in each paper row:**

- **Mined `policyEnf` (status 1)** issuing `GrantIssued` with:
  - gid = Bob (0xac5a…);
  - recipient 0;
  - expiry = issuedAt + 30 s.
- **One `AccessLog`** with `allowed=true`, gid = Bob and Alice's credential digest. Exactly two new
  DBC events and no PBC change.
- **Alice's original request** stays FORWARDED. Both subjects' nonces are unchanged.
- **Release routing:** registered PBC recipient keys are Bob 0x5fe3…, Alice 0x98d7… (A35 values).
  One production release went to Bob's key, with worker intent 1, send 1 and attempts 1/1.
- **Completion:**
  - the same response decrypts for `keyref:user:bob` (decryptable);
  - `keyref:user:alice` returns WRONG_SUBJECT;
  - the completions changed nothing native or worker-side;
  - no outcome was reported.

**Controls in every row** (deployment D1):

- wrong-admin rejected with code 16 (baseline issuer restriction, not a repair; also re-checked in
  the D2 bootstrap);
- registered Alice: allow, then release, completion and one outcome;
- registered Bob: policy denial (9).

The stress ran on a **fresh second deployment D2** on the same chain pair, with disjoint contract
addresses, its own bootstrap, its own adapter process and 0700 state.

**Timing:**

| Row | Stress stage wall time | Release clock to grant expiry |
|---|---|---|
| paper-strict | 8.3 s | 29 s |
| paper-minimal | 8.2 s | 28 s |
| repaired-e | 7.9 s | – |

These are single samples, not distributions.

## Integrity, processes and evidence custody

- **Sources stable.**
  - The plan still verifies after the run.
  - The runner's own source bracket is stable (`sourceStable: true`).
  - The independent bracket covers 1965 files, aggregate 6a6ccb1d.. both before and after
    (`source-bracket.json`).
  - HEAD was 77a7c1f before and after.
  - Owner snapshots are stable in every profile.
- **Cast checkpoints** (D-5b): all OK, 10-24 per chain per row; labels are construct, run-start,
  read-group, submit and run-end.
- **Processes:**
  - All 12 owned processes exited 0, and their PIDs are absent: 6 Anvil and 6 adapters (D1 and D2
    in each row).
  - Ports 18545 and 18546 are free after the run.
  - No unrelated process was touched.
- **Commands:** 37 captured owner/export commands, all exit 0. 2983 RPC CLI calls, all exit 0
  (`live-result-audit.json`).
- **Public evidence:** 133 selected redacted JSON files under `run/`.
  - Manifests, deployments, checked bootstraps, command rows, exchanges (tokens replaced by
    digests), results, before/after snapshots, native views and transactions, process records and
    Cast checkpoints.
  - Selection refused any `token`/`private*` field or runner TEST-ONLY key material; none was found
    (`selected-manifest.json`).
  - Raw logs, private adapter state, owner snapshots and full RPC transcripts stay in
    `tmp/p3/sl1-run`. They are hashed in `external-public-inventory.json`.
  - The selection and audit helper is kept as `select_audit.py.txt` (scratch script, read-only on
    the run).

## Classification and limits (do not overstate)

- **Paper rows are SPEC_GAP.** The paper's forwarded tuple carries no source-decision binding (Fig. 6
  forwards verified attributes), so a **compromised configured relay** can make the DBC authorize
  the relay-asserted subject with the original subject's credentials. Under the reconstruction
  choice D35/A38, the symbolic response goes to that subject's registered key.
  - The stress lies outside the paper's secure-isolation assumption (A01). It is a specification
    dependency, **not an HMBC exploit**, and not the authors' implementation.
- **Repaired-e is REPAIR_SUPPORTED.** The signed decision binds the original request digest, giving
  DecisionVerifier step 4, WRONG_SUBJECT. This is a tested reconstruction result.
- **Other limits:**
  - delivery unknown;
  - symbolic decryptability, not ABE;
  - one trial per row; single-host Anvil, no consensus;
  - grouped RPC checks cannot detect a transient reorg restored between boundaries;
  - the D2 relay/CA-admin balance reset is a test-harness action.
- **Remaining work:** 41 catalog comparisons, live mutants, the revocation window, RQ1-E.md and the
  gate. Gate E stays NOT_RUN.
