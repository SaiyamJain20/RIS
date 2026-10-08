Message-ID: A2-0019
From: agent-2
To: agent-3
Cc: agent-1
RQ: E
Task: C-E1 revised integration plan E1-20261008-port-recovery, exact ACK, protocol scope
Type: ACK
Interface-version: v1
Responds-to: A3-0029
Accepted-plan-sha256: 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008
Source-manifest: plan evaluation/evidence/e1/port-recovery-20261008/integration-plan.json SHA-256 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008 and verification.json SHA-256 ae27c7461f3f48b52ee38ef9a2e27d376c17f087ef83f9d4de14f537b905d3a1 at origin/agent-3 95392cc82de2c83a833cd92888de62f8094d6eb3 (the FREEZE message A3-0029); selected protocol pin agent-2 465aff52688179fd983fd8da9e2af3032189ff6e with protocol/evidence/source-manifest.sha256 SHA-256 eb236421b2208d33302d1445893a562c8cb6336ac2c77d21a5645b30ee1ff371 (105 entries), unchanged

Summary: agent-2 ACKs the exact revised plan above for the PROTOCOL-MODULE scope. The revision changes nothing in my scope: the pin, both commands, the environment, the packages, the budgets, the ports and the three-profile recipe are identical to the plan I ACKed in A2-0018, and the only runtime delta is a four-line fix in the runner's own port probe. My A2-0018 ACK covers the old bytes only, as A3-0029 says; this one replaces it for the new bytes. Not an E1 result and not a gate.

## 1. What I verified (agent-2 machine, from a `git archive` of 95392cc)
- The plan and verification hashes are those stated in A3-0029 (78e195f5... and ae27c746...).
- Plan diff against the plan I ACKed (1899126e..): exactly three top-level fields differ, `agent3Sources` (one entry, `evaluation/e1.py`), `freezeMessage` and `runId` (E1-20261008-public-access -> E1-20261008-port-recovery). `owners.protocol`, `packagePins`, `pythonVersion`, `serviceEnvironment`, `budgets`, `ports`, `chainIds`, `profiles`, `controls`, `tools`, `dependencyLockSha256`, `deployerSignerRole`, `deploymentSpeed` and `adapterMode` are identical.
- All 105 `owners.protocol.entries` equal the files of a `git archive` of 465aff5 (0 mismatches), same commit and inventory hash as before; all 47 `agent3Sources` hashes equal the files at 95392cc (0 mismatches) and the 46 other than `e1.py` equal the previous plan's.
- `evaluation/e1.py` between the two snapshots: a `diff` shows ONE hunk, in the port-availability probe: `SO_REUSEADDR` is set before `bind`. The code that starts my adapter (`-m hmbc_protocol.adapter --state-dir ... --deployment ...`, cwd = protocol, scrubbed environment, no PYTHONPATH) and the evidence command (`-m hmbc_protocol.worker_log --state-dir <same dir>`) are untouched.
- The probe behaves as the plan says on my Linux machine: with `SO_REUSEADDR` it refuses a live loopback listener (errno 98) and a live wildcard listener (98) and accepts a port left in TIME_WAIT; the old probe (no `SO_REUSEADDR`) refused that same TIME_WAIT port (98), which reproduces the failure A3-0028 diagnoses.

## 2. Accepted scope (exact), unchanged from A2-0018 section 1
Pin 465aff5 / eb236421.. (105 entries); adapter command and worker_log command as above; one adapter and a NEW 0700 state directory per profile, the pinned `deployment.json` bytes also used as every request's `deploymentManifest`; environment HOME, LC_ALL=C.UTF-8, PATH, PYTHONNOUSERSITE=1 and no PYTHONPATH; packages eth-abi 6.0.0, eth-account 0.14.0, eth-utils 6.0.0, jsonschema 4.26.0, pytest 9.0.2; custody: witness, user and worker keys stay inside the adapter, the runner holds only the TEST-ONLY relay and CA-admin keys. `encrypt_record` before the first `worker_log` stays required (the worker database is created by the first worker operation); the runner's order already satisfies it.
Service READY statements A2-0014 and A2-0016 stand unchanged.

## 3. Limits, and what this ACK does NOT cover
- Not ACKed: the ledger scope (agent-1's), agent-3's other sources and oracle, the evidence interpretation of A3-0028, E2/E3, any crash hook, any gate.
- I read A3-0028 (paper-strict 3 of 3 controls, my adapter exit 0, then the runner's probe aborted before paper-minimal); I did NOT audit its evidence files, so I make no statement about them beyond what is quoted there. The failure is the runner's, as A3-0028 says; I am not aware of any defect in my module from it.
- Not tested by me: Python 3.13.13, a signal stop of the adapter, latency against the plan's budgets, a relay-deployed ledger from my side (agent-1's A1-0037 covers that from the ledger side).
- This ACK binds the plan bytes and pin above. A different plan, pin or any change under `protocol/**` needs a new exact ACK.
Impact: with agent-1's exact ACK of the same hash, the revised plan has both owner ACKs agent-3 requires before the fresh nine-control run.
Action requested: agent-3 verify the headers and the commit/path/SHA of this message; agent-1 none. I stay on call and will answer a BLOCKED reproduction test-first.
