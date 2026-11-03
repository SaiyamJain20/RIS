# protocol/f0 — agent 2's F0 planning input (2026-11-03)

**F0 PLANNING. PROPOSALS, NOT ACKED, NOT IMPLEMENTED, NOT FROZEN.** No production source, test, export or interface byte under `protocol/` changed; the E manifest
`../evidence/source-manifest.sha256` (`005c8448..`) and every E pin are untouched. This directory has its own manifest, `MANIFEST.sha256` (does not list itself).

| File | What it is | Messages |
|---|---|---|
| `INVENTORY.md` | key, state and correlation inventory; protocol-side review of the 29 matrix scenarios; hooks, layout, source and interface plan, ACK map | A2-0040 |
| `SIGNING-RULES.md` | R6: conflict keys, effect values, durable signing rule, independent validation, deterministic expiry, receipt equivalence, death predicates with numeric observation parameters, collector rules. **Revision 2** (A2-0042) takes A1-0094 C1/C2 | A2-0040, A2-0042 |
| `D50-DEPLOYMENT-BINDING.md` | D50 RFC: stronger worker/witness state binding over seven runtimes, migration, refusal controls. **Revision 2** (A2-0042) takes A1-0094 C3/C4 | A2-0041, A2-0042 |
| `model/PREDICTIONS.md`, `model/conflict_key_model.py` | bounded explicit-state **design check** of one conflict key (predictions written first) | A2-0040 |
| `evidence/MODEL-RUNS.md` and run outputs | both model runs, including the one failed prediction (P9) and its cause | A2-0040 |

Verify: `cd <repo root> && sha256sum -c protocol/f0/MANIFEST.sha256`.
Re-run the design check: `cd protocol/f0/model && python3 -I conflict_key_model.py > /tmp/out.json` (about 20 s, standard library only).
That check is **not** TLC, not agent 3's model and not the implementation (see `model/PREDICTIONS.md`).
