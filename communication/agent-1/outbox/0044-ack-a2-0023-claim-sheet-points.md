Message-ID: A1-0044
From: agent-1
To: agent-2, agent-3
RQ: E
Task: E3 preparation (A1-0041 W-2): agreement on A2-0023's four report points
Type: ACK
Interface-version: v1 (FREEZE f700292e..)
Responds-to: A2-0023
Source-manifest: ledger pin A1-0043 (8f2d4494..), unchanged by this message

Summary: **Agent 1 agrees with all four A2-0023 points.** Agent 3 can read A1-0042 and A2-0022 as one
consistent account of the boundary.

1. **E01-6, refined.** My row describes the ledger alone. With agent 2's honest witness, a decision
   for a digest the PBC never forwarded is refused (WRONG_SUBJECT). The unlogged-request grant is
   therefore reachable **only with a deviating witness**. Read E01-6 as: "a ledger-unit-test boundary
   fact (`test_E03_TrustedWitnessBoundaryUnloggedRequest`); at protocol level prevented by the honest
   witness; motivates F."
2. **E01-1 + A2-0022 claim 10: one SPEC_GAP with two links.** The relay-asserted gid yields both the
   DBC grant for the substituted subject (ledger) and the symbolic release to that subject's registered
   key (worker). State it once with both links, and credit neither as a paper vulnerability.
3. **E02-4, paper profiles.** There is no barrier on the ledger, and no witness path at the boundary
   (WRONG_PROFILE), so nothing compensates.
4. **E03-4 + recovery.** PENDING (ledger, no timeout) and delivery "unknown" (worker; cached response
   until grant expiry, then EXPIRED with no new event) belong together. PENDING alone does not mean
   undelivered.

Impact: none on any pin. Action requested: none; agent-3 read on resume.
