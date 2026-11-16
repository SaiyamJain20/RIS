# agent 2: protocol-scope review evidence for interface-v2 candidate 1 (A2-0054)

Not part of the F0 set: `protocol/f0/MANIFEST.sha256` (`097d8ed8..`, the revision-7 design pin) and every file under `protocol/f0/` are untouched. Nothing here changes a
production byte; the E manifest `protocol/evidence/source-manifest.sha256` (`005c8448..`) does not list this directory. Same-model review of a candidate made by the same model
family: correlated. These scripts measure and compare; they prove nothing about a future implementation.

Verify this directory: `cd protocol/v2-review/candidate1 && sha256sum -c MANIFEST.sha256` (the manifest does not list itself).

Candidate bytes (agent 3, origin/agent-3 `4de6274`, `interfaces/proposals/v2/MANIFEST.json` sha256 `6acceadf35b9f01833642f61ca7ae7bc05158e5499fb3e06c1d66fb2bbde3aee`) are
not copied here. Extract them and run, from the repository root, with Python 3.13 and `jsonschema==4.26.0`, `eth-account==0.14.0` (`protocol/requirements.txt`):

```
git archive 4de6274 interfaces/proposals/v2 | tar -x -C "$DIR"
cd protocol/v2-review/candidate1
for s in check_schema_and_vectors check_b_shape_differential check_signatures probe_schema_semantics; do python3 -B $s.py "$DIR/interfaces/proposals/v2"; done
```

Every script first verifies the candidate manifest hash and the hash of every listed file, then refuses to run on any mismatch. `outputs/` holds my runs (CPython 3.13.13,
jsonschema 4.26.0, eth-account 0.14.0, one host, no services, no network use by the scripts) and `outputs/exit-codes.txt` their exit codes.

| Script | What it does | Exit 0 means |
|---|---|---|
| `check_schema_and_vectors.py` | schema validity; all 16 wire/success responses validate against `AdapterResponse`; my own semantic wire checker (`protocol/f0/vectors/check_wire_examples.py`) run on a copy of SUCCESSOR-WIRE.md carrying the candidate's 12 examples; reason table equality; D50 owner vectors equal mine; `recorded`/`collection` accepted only by the owning operation | every check passed |
| `check_b_shape_differential.py` | my D50 reference validator versus the candidate's `DeploymentBindingDocument` over 997 corruptions of the E and F documents | always (a measurement; read the printed differences) |
| `check_signatures.py` | production E encoder (`hmbc_protocol.eip712`, imported read-only): label-to-address derivation, six signing vectors (digest recomputed, signatures recovered), every report/certificate/outcome address in the 12 wire and 4 success vectors recovered under the HMBCState domain | all 99 checks passed |
| `probe_schema_semantics.py` | which of BOUNDARY's mandatory semantic rules the schema itself enforces (13 single-corruption probes) | always (informational) |

Limits: the recoveries check synthetic signatures made with public fixture keys; the 997-case corpus is mine and finite; "both accept" cases include decimal truncations that stay valid
and are filtered from the printed list; no Solidity, no ledger, no pool, no witness, no timing.
