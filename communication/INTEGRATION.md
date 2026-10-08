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

Owner READY is now reviewed: ledger A1-0028 at91add8c/407c8633.. and service A2-0014 at34de384f/30f76dda..; neither is an integration FREEZE ACK. Bootstrap signed Alice/Bob fixture producer is pending A3-0024. No ports/PIDs allocated, no deployment/state directory created, no integration result.
