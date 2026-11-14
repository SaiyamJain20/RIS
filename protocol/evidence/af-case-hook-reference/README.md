# Executable hook reference for agent 3's F runner (agent 2, 2026-11-13)

PAPER-DERIVED RECONSTRUCTION; TEST-ONLY hooks; synthetic TEST-ONLY keys; one host; correlated same-model review. **No hook behaviour is claimed here**: `tests/test_hook_reference.py` STARTs each documented form for real on a real Anvil pair with agent 1's F ledger and asserts the start (a well-formed adapter response, or one closed refusal) — if a line stops parsing, that test fails, so this reference cannot silently rot. The BEHAVIOUR of each hook is pinned by the live hook tests named in `protocol/evidence/af-case-hook-inventory/README.md`.

## The one command shape
Every variant is a flag of the TEST-ONLY alternate adapter entry `testtools.faulty_adapter_v2`, which serves `hmbc_protocol.adapter_v2_main` byte for byte and, in its own process only, installs the fault:

```
python -m testtools.faulty_adapter_v2 \
  <the six adapter flags> [--allow-governance FILE] \
  --witness-variant I=SPEC ...     # repeatable, one per witness index 0..3
  --mutant-tree ID=ABSOLUTE_DIR ...  # one per mutant:ID variant
  --worker-variant compromised --claims FILE   # the H5 symbolic worker
```
The six adapter flags (from `protocol/tests/fixtures`): `--deployment <F deployment json> --abi-dir <agent1-85c59f5-abi> --schema agent3-v2.1-hmbc.schema.json --schema-sha256 d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3 --schema-revision v2 --state-dir <new dir>`. A run with NO variant flag ends exactly as the production entry does.

## Witness variant SPECs (all verified to start by `tests/test_hook_reference.py`)
| Flag | Meaning | F rows (per the inventory) |
|---|---|---|
| `I=crash:before_commit` / `I=crash:after_commit` | H4: witness I exits 86 at that named store point | F-13 |
| `I=delay:MS[:kind[:before\|after]]` | H6: real-time hold, MS 0..60000, kind checkpoint/decision/receipt/governance | F-20, M7 fixture |
| `I=mutant:ID` + `--mutant-tree ID=DIR` | G3: a DELIBERATE source mutant (M1 M2 M3 M4 M6 M7) as a real supervised process from that tree; M5 is the whole adapter from its tree | F-12, F-13, F-29, FL-1, FL-5 |
| `I=byz:SPEC` | G1: real-process Byzantine witness, SPEC `withhold` \| `garbage` \| `repeat:N(2..8)` \| `equivocate` \| `impersonate:J(0..3)` \| `poison:FIELD` | FL-4, FL-5/F-22, FL-7, F-12 |
| `I=view:SPEC` | G2: real witness with a diverging view, SPEC `authEpoch:N` \| `policyVersion:N` \| `witnessSetVersion:N` \| `headLag:N` (N 1..50) | F-16, F-17, F-18, F-31 |

Building a mutant tree (G3):
```
python -m testtools.mutant_tree build M2 --dest /absolute/new/dir     # one verified single-site edit; writes MUTANT.json
python -m testtools.mutant_tree list                                  # the registry
```
M5 is an ADAPTER-role mutant: start the whole entry from its tree with `python -m testtools.mutant_run --tree /dir --mutant M5 --module testtools.faulty_adapter_v2 -- <the adapter flags>`.

## Refusal forms (also verified)
- `--worker-variant compromised` without `--claims FILE` → one closed line `{"error":{"code":"MALFORMED","message":"refusing: --worker-variant needs --claims FILE"}}`.
- `I=mutant:ID` without its `--mutant-tree`, a tree of another mutant, a tampered tree, or an ADAPTER-role id as a witness variant (`I=mutant:M5`) → the entry's one closed `refusing:` line, nothing spawned.
- A deployment that does not declare TEST-ONLY synthetic keys → refused whatever the variants.

## What this is not
It does not run any F case, does not judge what a hook produces, and does not claim the hooks are complete: the deviations from the F plan (a real-process Byzantine ADVERSARY rather than a second node for H3; a VIEW divergence inside the process for G2) are stated in `protocol/evidence/af-case-hook-inventory/README.md`. The live forms are one start each on one host; a heavily loaded host can still make a start slow.
