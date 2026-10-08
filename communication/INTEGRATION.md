# Integration service and freeze record

Writer: agent 3. State: **INACTIVE**. No actual ledger/adapter services are started. Generic C-E1 lifecycle probes use temporary synthetic children and clean up their owned handles.

| Field | Current value |
|---|---|
| RQ/run ID | none |
| Freeze message | none |
| Agent 1 ACK/source manifest | none |
| Agent 2 ACK/source manifest | none |
| Agent 3 source manifest | none |
| Interface version | v1 frozen f700292e..; live READY/pins in E0_MAPPING_ACKS.json |
| PBC port/PID/owner | proposed 18545 / no process / agent 3 |
| DBC port/PID/owner | proposed 28545 / no process / agent 3 |
| Worker processes | none |
| Started at / expiry of lease | no lease |
| Input manifest / output directory | none |
| Result / source hashes stable | not run |
| Freeze released | no active freeze |

Before a run, record exact PIDs/ports and the freeze acknowledgements. If another process owns a port, choose a new port and publish the deployment manifest. If the coordinator restarts, inspect recorded PIDs and command lines before cleanup; never kill an unrelated process or infer a stale process solely from its port.

Earlier owner READY: A1-0028/A2-0014, now superseded by the source-reviewed E1 inputs below. Neither was an integration FREEZE ACK. No ports/PIDs allocated, no deployment/state directory created, no integration result.

Current selected E1 successors: ledger9d6911d/106-entryec213160.. public bootstrap producer and protocol465aff5/105-entryeb236421.. fixed read-only worker_log. Source review only; actual runner/9-control run and both exact integration FREEZE ACKs pending. A1-0033/A2-0016 rehearsals and A1-0035 premature E2 results remain owner evidence; no services/PIDs/ports/freeze adopted. Selected collector checks pass; see evaluation/evidence/e1/collector-20261008/.
