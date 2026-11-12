# Anchored public observations (A2-0077 F1) — 2026-11-12

Classification: tested reconstruction result (evaluator bug fix). Paper-derived
reconstruction; synthetic RPC only; no service, chain or F case was run.

Finding (reproduced by reading source, not by a live run): `public_observations_v2.collect`
read only `eth_getBlockByNumber ['latest']`, while `binding_context_v2` requires the
BindingExport anchor to equal the observation anchor. The export anchor is fixed at
store init, so the join fails once either chain has moved (A2-0077 S6b measured 4/4
refusals; S6c 4/4 accepted with an anchor-answering shim). This was a defect on the
evaluator side, not in the accepted F0 export text.

Change: `collect(..., anchors=None)`. With `anchors` = exactly `pbc`/`dbc` ->
`{number: canonical decimal string, hash: 0x + 32 bytes}` every code/getter read uses
that block and the node's hash must equal the requested hash. Inventory is validated
before any I/O or output directory. Default (`None`) behaviour is unchanged.

TDD record: 11 of 12 new cases RED first (TypeError, keyword missing); the
characterization case "no anchors on a moved chain" passes before and after. First
GREEN run had 1 failure caused by my test (fixture pbc hash collided with the chosen
wrong hash); test corrected, not the code. Three deliberate mutants (hash check
removed; `latest` restored; shape check removed) are detected (2/2/1 failures).

Commands (cwd repo root, `.venv` Python 3.13.13):
- focused: `.venv/bin/python -m pytest evaluation/tests/test_public_observations_v2.py evaluation/tests/test_binding_context_v2.py -q` -> 164 passed, exit 0.
- root: `.venv/bin/python -m pytest -q` -> 2956 passed in 742.71s, exit 0
  (previous root 2944 + 12 new). Started 12:11:14Z, ended 12:23:37Z. No repo file was
  added while it ran.

Hashes (SHA-256): `evaluation/public_observations_v2.py` 43f7d87e99ed2938ff857c3e4526d056707e6f3bc287782f771f0b512bca28f4;
`evaluation/tests/test_public_observations_v2.py` 53de89d0d4297b0c5df1f093ef2986f2a601ec81fa46b8f4a9bc32f5e7221a01.
Base HEAD 6358f7c8c4f997db51369dc7043fa6442400a1cd.

Limits: synthetic transport only. Whether a real node serves historical state for the
export anchor is A2's measurement (Anvil keeps it; a production node needs archive
state), not re-measured here. No runner calls `anchors` yet; no BindingExport join
has run on live evidence by me. Correlated same-model review; no extra agents.
