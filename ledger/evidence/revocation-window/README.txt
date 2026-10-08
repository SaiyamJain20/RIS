Revocation-window OWNER measurement (A1-0045 W-3 / A1-0046). Owner evidence, not C-E2 or gate evidence.
Agent 1, 2026-10-09 ~04:16-04:20 IST, agent 1's machine; Foundry/Anvil v1.8.5, CPython 3.13.5 venv; agent 2 8b7caf5 (production = E1 pin 465aff5,
manifest d16ddad8.. verified, unmodified). Private Anvil pair, BOTH chains --block-time 1 (interval mining).
Command: <venv>/bin/python -I ledger/tools/revocation_window.py --protocol <agent-2 archive>/protocol --out <dir>  -> exit 0, 220 s.
Method (repaired-e, one World, trust restored between trials): fresh Alice request (TTL 30 s) forwarded and certified by the adapter
(checkpoint C1, decision D1); H1 CRL revoking serial 101 installed at T0 (PBC block timestamp); the runner accepts the next checkpoint
(adapter collect_checkpoint -> KSSC.acceptState) once DBC time >= T0 + d; every 0.5 s consumeDecision(request, D1) is probed with
eth_call AT AN EXPLICIT DBC BLOCK NUMBER (non-consuming); W = that first refusing block's own timestamp - T0. With 1 s blocks every
block is probed; the probe sees exactly the timestamp/state of the block it names (A2-0025's "latest on an idle chain" concern does
not arise with interval mining; with automining probe at `pending` or mine first).
Results (summary.json):
  d=0      barrier block +2 s   first refusal = barrier block, STALE_STATE   W=2 s
  d=5      barrier block +6 s   first refusal = barrier block, STALE_STATE   W=6 s
  d=10     barrier block +11 s  first refusal = barrier block, STALE_STATE   W=11 s
  d=20     barrier block +21 s  first refusal = barrier block, STALE_STATE   W=21 s
  never    no barrier           first refusal at request.expiresAt exactly, EXPIRED   W=26 s (= TTL left at T0)
  every trial: a NEW Alice request after T0 -> PSC AccessDenied REVOKED (immediate at the PBC)
  paper-strict contrast: the relay's policyEnf for a tuple forwarded before T0 would grant at T0+5, +35 and +65 s (the request had
  expired at T0+27): no ledger bound; only relay behaviour limits it.
Reading: repaired-e W = min(time until the DBC accepts a post-revocation checkpoint, remaining request/decision TTL) <= 30 s; the
barrier takes effect in the very block that accepts it. W's size is therefore a runner/witness cadence parameter, not a ledger constant.
Limits: one machine, one trial per delay; second-level block granularity (+~1 s submission latency of the barrier transaction);
T0 (PBC) and refusal (DBC) are two chains following the same host clock (no clock manipulation in these chains).
