# protocol/f0 — agent 2's F0 planning input (2026-11-03)

**F0 PLANNING. PROPOSALS, NOT ACKED, NOT IMPLEMENTED, NOT FROZEN.** No production source, test, export or interface byte under `protocol/` changed; the E manifest
`../evidence/source-manifest.sha256` (`005c8448..`) and every E pin are untouched. This directory has its own manifest, `MANIFEST.sha256` (does not list itself; it listed 13 files in revisions 1 and 2 although messages A2-0040/41/42 said 12: corrected here, A3-0058 item 6).

| File | What it is | Messages |
|---|---|---|
| `INVENTORY.md` | key, state and correlation inventory; protocol-side review of the 29 matrix scenarios; hooks, layout, source and interface plan, ACK map | A2-0040 |
| `SIGNING-RULES.md` | R6: conflict keys, effect values, durable signing rule, independent validation, deterministic expiry, receipt equivalence, death predicates with numeric observation parameters, collector rules. **Revision 3** (A2-0043) answers A3-0058 item 2 and the O1-O6 recommendations; revision 2 (A2-0042) took A1-0094 C1/C2 | A2-0040, A2-0042, A2-0043 |
| `D50-DEPLOYMENT-BINDING.md` | D50 RFC: stronger worker/witness state binding over seven runtimes, migration, refusal controls. **Revision 3** (A2-0043) answers A3-0058 items 3-6; revision 2 (A2-0042) took A1-0094 C3/C4 | A2-0041, A2-0042, A2-0043 |
| `SUCCESSOR-WIRE.md` | proposed successor error reasons on existing v1 codes, operation shapes with examples, tripwire FAULTED semantics, store lifecycle and crash ordering (A3-0058 items 2 and 3) | A2-0043 |
| `vectors/` | D50 reference encoder, common binding vector, strict masked-build check (A1-0096 length rule), expectations (69 checks), the wire-document consistency checker, and `replay_a1_masked.py` (my strict check run on agent 1's published raw bytes: 18/18) | A2-0043 |
| `model/PREDICTIONS.md`, `model/conflict_key_model.py` | bounded explicit-state **design check** of one conflict key (predictions written first) | A2-0040 |
| `evidence/MODEL-RUNS.md` and run outputs | both model runs, including the one failed prediction (P9) and its cause | A2-0040 |

Verify: `cd <repo root> && sha256sum -c protocol/f0/MANIFEST.sha256`.
Re-run the vector checks (no `__pycache__`, stdlib only): `python3 -B -I protocol/f0/vectors/test_d50_reference.py` and `python3 -B -I protocol/f0/vectors/check_wire_examples.py`; regenerate the vector with `python3 -B -I protocol/f0/vectors/d50_reference.py --emit | cmp - protocol/f0/vectors/d50_binding_vector.json`.
Re-run the real-data replay (agent 1's published bytes, extracted to scratch; the bytes are not part of this repository): `mkdir -p $SCRATCH && git archive <origin/agent-1 commit 3de2ee6> ledger/evidence/f0-d50-masked | tar -x -C $SCRATCH && python3 -B -I protocol/f0/vectors/replay_a1_masked.py $SCRATCH`.
Re-run the design check: `cd protocol/f0/model && python3 -I conflict_key_model.py > /tmp/out.json` (about 20 s, standard library only).
That check is **not** TLC, not agent 3's model and not the implementation (see `model/PREDICTIONS.md`).
