# agent 2: verification of the F0 freeze request for candidate 2 (A2-0058)

Not part of the F0 set (it is not one of the 52 pinned `protocol/f0` files) and not a pin. Same-model review of a coordinator request written by the same model family: correlated.

`check_freeze.py` verifies `communication/F0_FREEZE_CANDIDATE2.json` (agent 3, origin/agent-3 `f1fe7e7`, sha256 `f9f0906faf8dbfb9ccd2d06a794c715bb6a3167b6f273a50347742db41196df5`) against the real blobs:
the 52 protocol F0 pins against my manifest at the owner commit, the blobs and my current working tree; the six owner-input hashes and the ledger design hash; the five layout pins (note N-4); the 14 candidate-2
payloads and the candidate-8 base hashes; the four ACK records (A1-0109, A2-0057, A1-0104, A2-0053) at their commits; the 32 case ids, the 14 components and the numeric bounds against the candidate-8
matrix, CSV and my own documents; the clarifications of my notes; and it **re-runs my own helper suites** to compare the counts clarification A2-N5 quotes (D50 126 and 15/15, wire 36/36, layouts 76 and 29/29,
pool adoption 53 and 19/19). Standard library only; it reads blobs with `git show`, so `git fetch origin` first.

```
git show f1fe7e7:communication/F0_FREEZE_CANDIDATE2.json > "$DIR/freeze.json"
python3 -B protocol/v2-review/freeze-candidate2/check_freeze.py "$DIR/freeze.json"
```

`outputs/` holds my run (CPython 3.13.13, one host) and its exit code. Verify this directory: `cd protocol/v2-review/freeze-candidate2 && sha256sum -c MANIFEST.sha256`.
Limits: it checks that the pins are the right bytes and that the numbers I can reproduce are reproduced; it does not check the ledger parts (agent 1's), agent 3's own evidence directory, or any runtime. No pool, witness, store, ledger or timing.
