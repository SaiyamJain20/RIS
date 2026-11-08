# agent 2: protocol-scope review evidence for interface-v2 candidate 2 (A2-0057)

Not part of the F0 set: `protocol/f0/MANIFEST.sha256` (`8496c7f3..`, the revision-9 pin) and every file under `protocol/f0/` are untouched; nothing here changes a production byte
(the E manifest `protocol/evidence/source-manifest.sha256`, `005c8448..`, does not list this directory). Same-model review of a candidate made by the same model family: correlated.
These scripts measure and compare; they prove nothing about a future implementation.

Verify this directory: `cd protocol/v2-review/candidate2 && sha256sum -c MANIFEST.sha256` (the manifest does not list itself).

Candidate bytes (agent 3, origin/agent-3 `5b6bb9d`, `interfaces/proposals/v2-candidate2/MANIFEST.json` sha256 `0d1a2be44666164deccf19c8c7e942b91938d7577fd6caba569837888b4143e9`) are not copied
here. Extract them and run, from the repository root, with Python 3.13, `jsonschema==4.26.0` and `eth-account==0.14.0` (`protocol/requirements.txt`):

```
git archive 5b6bb9d interfaces/proposals/v2-candidate2 | tar -x -C "$DIR"
cd protocol/v2-review/candidate2
for s in check_mappings check_layouts check_signatures; do python3 -B $s.py "$DIR/interfaces/proposals/v2-candidate2"; done
```

Every script verifies the candidate manifest and every payload hash, **and refuses to run unless my working-tree `protocol/f0` files equal the hashes the candidate pins in `OWNER-PINS.json`** (so
the comparison is always against the exact owner inputs the candidate names; on a later tree that changed those files the scripts stop instead of comparing against something else).
`outputs/` holds my runs (CPython 3.13.13, jsonschema 4.26.0, eth-account 0.14.0, one host, no services, no network use by the scripts); `outputs/exit-codes.txt` has the exit codes.

| Script | What it does | Exit 0 means |
|---|---|---|
| `check_mappings.py` | schema validity; 16 wire/success responses validate; my revision-8 semantic wire checker passes on the candidate's 12 examples; reason table; both owner-vector copies equal my files; `recorded`/`collection` scoping; P4 (empty arrays refused) and P5 (the 11 reporter subsets); a 1,442-case differential of the D50 B shape (my revision-5 reference versus `DeploymentBindingDocument`) | all checks passed; the only differences allowed are the threshold bound, which BOUNDARY carries as a semantic rule |
| `check_layouts.py` | my four evidence variants, two binding exports and refusal lines validate against `BindingExport`/`WitnessEvidence`/`ExporterError`; A->B->A accepted and a DENY under the ALLOW-only death refused by the schema; a 3,977-document differential of my revision-9 layout checker versus `WitnessEvidence`, re-sealed so only the corruption can invalidate | the schema is never stricter than my checker and agrees on every shape and format corruption (the looser verdicts are classified by kind and printed) |
| `check_signatures.py` | production E encoder (`hmbc_protocol.eip712`, imported read-only): the 99 label, signing-vector, report, certificate and outcome-address checks, unchanged from candidate 1 because the four signing/wire/success/witness vectors are byte-identical | all 99 checks passed |

Limits: the layout vectors' digests and signatures are placeholders (my own); the 46 real recoveries are the `signing.json` ones. Agent 3's own `verify.py` (385 checks) and `prepare.py` were not run by
me. The corpora are mine and finite. No Solidity, ledger, pool, witness, exporter or timing.
