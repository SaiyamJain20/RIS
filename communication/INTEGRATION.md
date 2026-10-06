# Integration service and freeze record

Writer: agent 3. State: **INACTIVE**. No services were started by the planning task.

| Field | Current value |
|---|---|
| RQ/run ID | none |
| Freeze message | none |
| Agent 1 ACK/source manifest | none |
| Agent 2 ACK/source manifest | none |
| Agent 3 source manifest | none |
| Interface version | v0 proposed |
| PBC port/PID/owner | proposed 18545 / no process / agent 3 |
| DBC port/PID/owner | proposed 28545 / no process / agent 3 |
| Worker processes | none |
| Started at / expiry of lease | no lease |
| Input manifest / output directory | none |
| Result / source hashes stable | not run |
| Freeze released | no active freeze |

Before a run, record exact PIDs/ports and the freeze acknowledgements. If another process owns a port, choose a new port and publish the deployment manifest. If the coordinator restarts, inspect recorded PIDs and command lines before cleanup; never kill an unrelated process or infer a stale process solely from its port.
