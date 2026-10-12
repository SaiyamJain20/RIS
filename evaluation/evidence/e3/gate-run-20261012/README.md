# Gate E run `E-gate-20261012`: published evidence (selected copy)

Paper-derived HMBC2020 reconstruction, not the authors' implementation. Synthetic fixtures, TEST-ONLY
keys. Solo phase: every review and ACK is correlated self-review (A1-0059). Publisher: agent 3 (proxy).

**Exit 0 and manifest status PASS are not gate E PASS.** Gate E is decided by the `communication/GATES.md`
checklist and three same-source ACKs (A1-0082 P4-3/P4-4). `evaluation/gate.py` stays fail-closed.

## The run

- **Command** (FREEZE S3-0021; plan `evaluation/evidence/e3/gate-plan-20261012/integration-plan.json`,
  sha256 `c00860192aaa69fd2e5f7baf132f5ebf10bf14ebba377edada31c1d9372b6bb9`; ACKs A1-0083 and S2-0021;
  ACK index `acks.json`):

  ```
  export PATH="$HOME/.foundry/bin:$PATH"
  .venv/bin/python -m evaluation.e_gate \
    --plan evaluation/evidence/e3/gate-plan-20261012/integration-plan.json \
    --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/gate-run/acks.json \
    --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/gate-run/out
  ```

- **Launched by agent 1** on this host, detached, on agent 3 (proxy)'s FREEZE S3-0021.
  - Start 2026-10-12T07:01:35+05:30 at HEAD 21b37fb (`run.meta`).
  - End 08:20:46+05:30, **exit 0** (`run.exit`).
  - `run.log` is the command's stdout summary. All four wrapper files are copied as-is.
- **Result** (`manifest.json`):
  - status PASS, failure null;
  - rows 56 PASS, 0 FAILED, 0 NOT_RUN;
  - ProVerif matched;
  - sourceStable, worktreeUnchanged and planReverified all true;
  - 112 services started.

  `gate-evidence.json` has 7 criteria VERIFIED. RQ1-report and three-matching-acks are PENDING by
  design.
- **Raw output** stays in job tmp at `tmp/p3/gate-run/out`.
  - It now holds 78299 files, 737,548,346 bytes (apparent size).
  - At the end of the run it held 78177 files (agent 1's count). The 122 extra files are SQLite side
    files: 61 empty `worker.sqlite-wal` and 61 `worker.sqlite-shm`. They appeared in the private worker
    directories after the run, first at 08:29:09 IST, when readers opened the worker databases read-only.
    That includes this selection, which used `mode=ro` and touched the `-shm` files.
  - No `worker.sqlite` file changed after the run: all mtimes fall within the run, and every `-wal` file
    is empty.
  - The private state is never published. The scan now opens the databases with `immutable=1`, which
    writes nothing.

## What is published

| Part | Files | Content |
|---|---|---|
| Gate top level | 20 | `manifest.json`, `gate-evidence.json`, `catalog-coverage-56.json`, `verify-freeze.json`, `versions.json` + `versions/*.txt` (8), `bracket-pre.json`, `bracket-post.json`, `proverif/` (`access{,_mutant}.{stdout,stderr}`, `summary.json`) |
| Catalog | 2092 | `catalog/<slice>/manifest.json` and `catalog/<slice>/<case>/<profile>/...`; layout unchanged for agent 1's review tools |
| Run wrapper | 4 | `run.log`, `run.meta`, `run.exit`, `acks.json` (as-is) |
| agent 3 (proxy) | 9 | this README; `selected-manifest.json`, `external-public-inventory.json`, `live-result-audit.json` (written by the selection); `publication-check.json`, `thin-row-margins.json`; `select_gate.py.txt`, `publication_check.py.txt`, `thin_row_margins.py.txt` |
| Scan record | 1 | `never-publish-scan.json` (written last) |

- The selection copied 2112 files (26,300,644 bytes) byte-identically from the raw output: 0 refused,
  0 copy mismatches (`filecmp`, `shallow=False`).
- Per slice: recovery-expiry 181, duplicate-outcome 76, nonce-replay 82, sl1-subject 127, sl2-relay 261,
  sl3-audit 221, sl4-receipt 280, sl5-trust 241, sl6-barrier 361, sl7-destination 262.
- The final directory count and size are in S3-0022.

**What each catalog row keeps:**

- `deployment.json`, `bootstrap.json`, `bootstrap-checked.json`, `commands.json` and `manifest.json`;
- `{pbc,dbc}-native/{views,transactions}.json`;
- `{pbc,dbc}-service/process.json`, `adapter*/process.json`;
- `alice/` and `bob/`: `exchanges.json`, `result.json`, `worker-{before,after}.json`;
- the early-row directories `recovery/`, `expired-retry/`, `alice/duplicate-outcome/` and
  `alice/nonce-replay/`;
- `<kind>-instance/{deployment,bootstrap-checked,bootstrap}.json`, `<kind>-instance/{pbc,dbc}-native/*.json` and
  `<kind>-instance/adapter/process.json`;
- every `<kind>-stress/*.json` (stress transaction, before/after state, blocks, exchanges, timeline,
  result), plus `destination-stress/source/*.json` and `subject-stress/*/`.

## What is excluded, and why

| Excluded | Files | Bytes | Why |
|---|---|---|---|
| `snapshots/` | 22166 | 594,850,280 | owner sources materialized from Git blobs at the pins; reproducible from Git |
| `pbc-rpc/`, `dbc-rpc/` | 52047 | 108,409,896 | raw RPC transcripts. Also the RPC command records and cast checkpoints (224 files, about 50 MB) that the SL1-SL7 publications kept. Agent 1's tools do not read them. They are summarized in `live-result-audit.json` (51823 RPC calls, 0 non-zero; 1629 cast checkpoints in 112 files, all OK) and hashed in the inventory |
| `private-adapter-state/` (D1, D2 and B) | 248 | 4,317,184 | worker databases with raw release tokens; never published, never hashed, counted only (103 directories, 62 worker databases) |
| `*.log` | 333 | – | service and adapter logs |
| raw tool outputs `*.txt` (except top-level `versions/*.txt`) | 689 | – | raw owner-tool, worker-export and deviating-witness outputs, incl. `receipt-deviate-NN.txt` |
| `*.txt.process.json` | 689 | – | process records of those tools |
| `<kind>-sign-list-NN.json` | 15 | – | raw producer records; no historical selection rule kept them |

Counts are from `selected-manifest.json` (`excludedByCategory`). Every non-private excluded file is
listed with its sha256 in `external-public-inventory.json`, except files under `snapshots/` and `*-rpc/`,
which appear there as one aggregate per directory (file count, bytes, and the sha256 of the sorted
`<path>\t<sha256>` lines).

**`manifest.json` `resultFiles`:** 376 entries.

- 264 are published and hash-equal.
- The other 112 are `snapshots/{ledger/ledger/exports,protocol/protocol}/abi/manifest.json`, one pair per
  row. All 112 have sha256 `cea42704..`, equal to the Git blob at both pins
  (`git show 933d2a7:ledger/exports/abi/manifest.json`, `git show 0716a8e:protocol/abi/manifest.json`).

## Selection

- **Script:** `select_gate.py.txt`, sha256 `dcca1e2b..`.
  - An earlier proxy-3 attempt drafted it before a usage limit; that draft was unreviewed (8d2f52b3..).
  - Before the selection, proxy-3 read and checked it and made these changes:
    - refusal and scan messages carry no key or token prefix;
    - an extra-file scan.
  - After the selection, proxy-3 made three more changes (the selection itself ran without them):
    - read-only `immutable=1` database opens when the WAL is empty (the selection used `mode=ro`);
    - the `deployer` label key added to the forbidden set;
    - every 64-hex private-key value of the repository's `**/vectors/*.json` files added (the selection
      read `interfaces/v1/vectors/eip712-agent1.json` only).

    The last two align the set with agent 1's scans (13 label keys including `deployer`). The vector files
    add no new key. So the selection-time refusal check lacked only the `deployer` key; the final scan below
    has it.
- **Rules:** the union of the per-slice rules of the historical publications:
  - the SL2-SL7 `select_audit.py` rule (SL1's is a subset);
  - the pre-solo early-row files: `bootstrap.json`, `recovery/worker-*`, `expired-retry/native-*`,
    `duplicate-transaction.json`, `replay-transaction.json`;
  - the gate's top-level files.
- **Command:**

  ```
  .venv/bin/python -I -B tmp/p3/gate-run/scripts/select_gate.py select . tmp/p3/gate-run/out tmp/p3/gate-run \
      evaluation/evidence/e3/gate-run-20261012
  ```

  Exit 0, 25.4 s wall, 197 MiB peak RSS. The paths are under the job tmp directory.
- **Differences from the historical slice publications** (`publication-check.json`):
  - The three pre-solo slices match file for file (181, 76, 82).
  - SL1-SL7 add `bootstrap.json` for D1 and each stress deployment, from the early-row rule.
  - SL1-SL7 drop the per-row `{pbc,dbc}-rpc/{commands,cast-checkpoints}.json`.
  - Nothing else differs.

## Checks

- **Agent 1's review tools, pre-check by agent 3 (proxy)** (`publication-check.json`). This is not agent
  1's review, which is A1-0084.
  - The eight pre-registered tools (A1-0083; sha256 199dd936.., 3e180ac4.., 98a97c63.., f02cbec4..,
    5fa5a7c9.., 13c10d1d.., 9edc3eb2.., 9e788ce9..) were run unchanged with `python -I -B` on this copy.
  - Each tool exits 0 and reviews 56 rows in total, with 0 rows with failures.
  - The output on this copy is byte-identical to the output on the raw output.
- **Thin-row margins** (`thin-row-margins.json`, from the published result files and native records):
  - **SL6 expired duty, repaired-e:** consume 1791772821, 1 s after duty end 1791772820. That is 7 s
    before the binding request and decision expiry 1791772828. `expiredStep` 13.
  - **SL7 expiry boundary, repaired-e:** consume = `r.expiresAt` = `d.expiresAt` = 1791773444.
    - The checkpoint expiry 1791773475 puts the checkpoint's DBC now at 1791773415.
    - The DBC read before the clock pin was 1791773416.
    - So the witness's own DBC now + 30 was at least 1 s past `r.expiresAt`, and the request expiry bound
      the decision.
    - `firingStep` 9.
  - **Nonce replay, repaired-e:** replay block 1791769487, 25 s before `r.expiresAt` 1791769512. The
    release was 23 s before it.
  - **Recovery, repaired-e:** the last send was 23 s before the original expiry (after_intent and
    after_send). The expired cached retry was observed at expiry + 1 and gave EXPIRED.
  - **Paper rows:**
    - recovery and nonce replay: 27-29 s;
    - SL6 expired duty: granted at DBC time = duty end (0 s by construction), 8 s and 7 s before the
      request expiry;
    - SL7 expiry boundary: granted at exactly `r.expiresAt`.

## Never-publish scan

- **Forbidden set:**
  - the TEST-ONLY private key, keccak256('hmbc-e0-synthetic-key:' || label), of 18 labels:
    - the 15 base labels of the SL4-SL7 helpers: relay, alice, bob, H1-H4 root and CA admin, and
      witness-1..4;
    - `deployer`, which agent 1's scans include;
    - the two `recipientKeyLabel` values named in the deployments.

    This is a superset of agent 1's 13 label keys;
  - every 64-hex private-key value, including `signerPrivateKey`, in the 11 `**/vectors/*.json` files of
    the repository. There are 3 distinct values, and all three equal label keys (alice, H1-root,
    witness-1);
  - the 61 release tokens read from the 62 worker databases of the raw output.

  That is 18 distinct keys plus 61 tokens.

  Matching is on lower-case hex without `0x`, as substrings.
- **Selection-time checks:** every selected JSON file was also refused if it had a `token`, `*private*`
  or `secret` field. 0 files were refused.
- **Scan record:** `never-publish-scan.json` comes from the last `select_gate.py.txt scan` run. That run
  covers every other file in this directory, plus `evaluation/reports/RQ1-E.md` and
  `evaluation/reports/fill_gate.py.txt`. Its result is required to be 0 hits.
