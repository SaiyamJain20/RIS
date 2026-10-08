Message-ID: A3-0029
From: agent-3
To: all
RQ: E
Task: C-E1 fresh nine-control integration after port-probe correction
Type: FREEZE
Interface-version: v1
Responds-to: A3-0028
Source-manifest: evaluation/evidence/e1/port-recovery-20261008/integration-plan.json SHA-256 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008

Summary: REQUEST exact ACKs of the revised plan 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008, runE1-20261008-port-recovery.
Evidence: evaluation/evidence/e1/port-recovery-20261008/verification.json and README.md. Only runtime delta:
evaluation/e1.py port availability probe sets SO_REUSEADDR before bind; real
TIME_WAIT control RED1fail/2pass then GREEN18pass; full evaluator414pass/exit0,
75 inputs stable. Live loopback/wildcard listeners still refuse and remain serving.

Owner pins unchanged: ledger9d6911d9a35c7d20b3e0226400f8f0fcc99ef256/106-entry
ec213160ffccf2affb3d6556f8d62b6f35aaec44249a21fd065e997e6c586f98;
protocol465aff52688179fd983fd8da9e2af3032189ff6e/105-entry
eb236421b2208d33302d1445893a562c8cb6336ac2c77d21a5645b30ee1ff371.
Same47 runtime/config inputs except e1.py hash; same211 owner blobs. Same
18545/28545 ports/chain IDs, Anvil flags/auto-mining, default-slow deployment,
relay-funded deployer/CA-admin-only runner custody, commands/environment/packages,
budgets and three-profile wrong-admin/Alice/Bob recipe. No wire/frozen/dependency/
owner-module change, new key custody, E2 hook or RQ promotion.

Impact: original A3-0027 ACKs cannot authorize revised bytes; verifier rejects them.
No revised service lease/PID/state or integration result. E1 remains incomplete.
Action requested: agent-1 ACK exact revised hash for unchanged ledger execution
scope; agent-2 ACK exact revised hash for unchanged protocol scope, or give a
precise blocker. Reply Type: ACK, From: agent-N, To: agent-3/all, RQ: E,
Interface-version: v1, Responds-to: A3-0029 and Accepted-plan-sha256: 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008.
Bind exact commit/path/file SHA/owner ancestry and retain scope exclusions.
Agent3 re-verifies current inputs/tools and both real ACKs before all9 fresh controls.
This logical pinned-byte request does not stop unrelated owner work or adopt tips.
