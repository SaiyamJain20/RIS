# agent 3 (proxy): handoff

Paper-derived HMBC2020 reconstruction. Synthetic only.

Phase: E / RQ1, solo mode (A1-0059, `../PLAN.md`, `../PROTOCOL.md`). Gate E NOT_RUN. F and G locked.

## Current task state

P0 read-only preparation is complete. **Nothing was executed:** no tests (agent 1 owns the P1
baseline), no services, no Git writes. The deliverables are S3-0001..S3-0003 in `outbox/`.

## Key facts for restart

**Catalog progress.** 12 of the 56 comparisons have actual integrated evidence (agent 3, 8e5a6dd):

| Rows | Evidence | Message |
|---|---|---|
| crash after intent / after send × 3 profiles | `evaluation/evidence/e2/expiry-live-20261009/`, `recovery-live-20261009/` | A3-0036, A3-0038 |
| duplicate outcome × 3 | `duplicate-live-20261009/` | A3-0040 |
| identical replay × 3 | `grouped-replay-live-20261009/` | A3-0045 |

- Four of the crash rows (the paper ones) are classified BLOCKED/unproved.
- 44 rows are NOT_RUN.

**Runner.**

- `evaluation/e2.py` supports only the expired-retry, duplicate-outcome and nonce-replay probe flags.
- `evaluation/access_execution.py` is the single flow driver. It hard-codes nonce 1 and TTL 30 s.

**Portability blockers** (S3-0001 section 4):

1. The ACK verifier accepts only A1/A2/A3 IDs and branches (e1.py:49, 103-133).
2. Tool paths point to `/home/karma`. The binaries on this host have the same hashes (`~/.foundry/bin`, `~/.svm`).
3. The DBC port is hard-coded to 28545 (e1.py:58), outside the 18545-18599 range.
4. `gate.py:43` always blocks.

**Do not edit:**

- `evaluation/toolchain.json`: it is the source of the frozen copy `interfaces/v1/toolchain.json`.
- Any `interfaces/v1` bytes.

**Toolchain.**

- Python: `.venv`, 3.13.5 (the frozen toolchain records 3.13.13).
- Foundry 1.8.5 at `~/.foundry/bin`.
- solc 0.8.37 at `~/.svm/0.8.37/solc-0.8.37`.
- ProVerif 2.05: agent 1 built it locally (`../evidence/host-toolchain/`, binary bc2cd5ed.. vs frozen c1087205..). Its outputs are not yet compared with A3-0033.

**Pins.** E2 owner pins: ledger 933d2a7 (195 entries, c7b7dd51..) and protocol 0716a8e (108 entries,
d16ddad8.., hook f0ab2400..). Ledger `src` is unchanged since the pin; only rehearsal and window
tools were added. Protocol is unchanged since the pin.

## Next allowed actions

Run these only after agent 1 assigns them:

1. SL0 portability: evaluator-only changes, test-first.
2. SL1 subject substitution: completion collector, plumbing and a separate control deployment.

Then the FREEZE (S3), the ACKs (A1 and S2), the live run, and the result.
