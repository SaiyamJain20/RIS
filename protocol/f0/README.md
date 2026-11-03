# protocol/f0 — agent 2's F0 planning input (2026-11-03)

**F0 PLANNING. PROPOSALS, NOT ACKED, NOT IMPLEMENTED, NOT FROZEN.** No production source, test, export or interface byte under `protocol/` changed; the E manifest
`../evidence/source-manifest.sha256` (`005c8448..`) and every E pin are untouched. This directory has its own manifest, `MANIFEST.sha256` (does not list itself; it listed 13 entries in revisions 1 and 2 although messages A2-0040/41/42 said 12; corrected in A2-0043, A3-0058 item 6).

| File | What it is | Messages |
|---|---|---|
| `INVENTORY.md` | key, state and correlation inventory; protocol-side review of the 29 matrix scenarios; hooks, layout, source and interface plan, ACK map | A2-0040 |
| `SIGNING-RULES.md` | R6: conflict keys, effect values, durable signing rule, independent validation, deterministic expiry, receipt equivalence, death predicates with numeric observation parameters, collector rules. **Revision 5** (A2-0047) adds section 8 items 7-10, the pool-retry amendment (sections 0-7, 9, 10 unchanged); revision 3 (A2-0043) answered A3-0058 item 2 and the O1-O6 recommendations; revision 2 (A2-0042) took A1-0094 C1/C2 | A2-0040, A2-0042, A2-0043, A2-0047 |
| `D50-DEPLOYMENT-BINDING.md` | D50 RFC: stronger worker/witness state binding over seven runtimes, migration, refusal controls. **Revision 4** (A2-0044) corrects the S0 count to 48/55 (R1), pins the object-list range hash; revision 3 (A2-0043) answered A3-0058 items 3-6; revision 2 (A2-0042) took A1-0094 C3/C4 | A2-0041..A2-0044 |
| `SUCCESSOR-WIRE.md` | proposed successor error reasons on existing v1 codes, operation shapes with examples, tripwire FAULTED semantics, store state model (WAL), lifecycle and crash ordering (A3-0058 items 2 and 3; revision 4 corrected sections 5 and 6 after A3-0059 R2/R3; **revision 5** (A2-0047) changes only section 2: recorded-value reports and adoption, three new examples) | A2-0043, A2-0044, A2-0047 |
| `vectors/` | D50 reference encoder, common binding vector, strict masked-build check (A1-0096 length rule), expectations (87 checks), the object-list `immutableRefsSha256` vector, the wire-document consistency checker, `replay_a1_masked.py` (my strict check run on agent 1's published raw bytes: 18/18) and `wal_state_experiment.py` (SQLite WAL as committed state, 8/8 predictions), and `pool_adoption.py` with `test_pool_adoption.py` (the adoption rule: 17 expectations, exhaustive f<=1 safety, 7/7 mutants) | A2-0043, A2-0044, A2-0047 |
| `model/PREDICTIONS.md`, `model/conflict_key_model.py` | bounded explicit-state **design check** of one conflict key (predictions written first) | A2-0040 |
| `evidence/MODEL-RUNS.md` and run outputs | both model runs, including the one failed prediction (P9) and its cause | A2-0040 |

Verify: `cd <repo root> && sha256sum -c protocol/f0/MANIFEST.sha256`.
Re-run the vector checks (no `__pycache__`, stdlib only): `python3 -B -I protocol/f0/vectors/test_d50_reference.py`, `python3 -B -I protocol/f0/vectors/test_pool_adoption.py` and `python3 -B -I protocol/f0/vectors/check_wire_examples.py`; regenerate the vector with `python3 -B -I protocol/f0/vectors/d50_reference.py --emit | cmp - protocol/f0/vectors/d50_binding_vector.json`.
Re-run the real-data replay (agent 1's published bytes, extracted to scratch; the bytes are not part of this repository): `mkdir -p $SCRATCH && git archive <origin/agent-1 commit 3de2ee6> ledger/evidence/f0-d50-masked | tar -x -C $SCRATCH && python3 -B -I protocol/f0/vectors/replay_a1_masked.py $SCRATCH`.
Re-run the design check: `cd protocol/f0/model && python3 -I conflict_key_model.py > /tmp/out.json` (about 20 s, standard library only).
That check is **not** TLC, not agent 3's model and not the implementation (see `model/PREDICTIONS.md`).
