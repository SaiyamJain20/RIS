# C-F1 public observation acquisition

Execute the accepted deployment checks in interfaces/v2/BOUNDARY.md through
the existing hash-pinned public ABI codec and loopback-only RpcClient. This is
an internal evaluator entry point; existing consumers and wire bytes stay fixed.

1. Pin exact owner ABI fixture copies; write synthetic RPC-byte tests first.
   Cover honest E/F/q2/mutant and cross-chain address reuse, missing/wrong ABI,
   bad return bytes, state/build/getter mismatches, identity drift, budgets,
   retained failure evidence and refusal to overwrite a previous output.
2. Collect raw calls, code and getters at one explicit block per chain; bracket
   chain/genesis/deployment/anchor identities across both chains, recheck ABI
   and manifest inputs, then reconstruct B. Publish normalized output only on
   complete success. No signing-context or exporter/history/WAL work in this slice.
3. Review, run focused and full root tests with before/after input hashes,
   reread exact peer messages, then publish reviewed owned paths on agent-3.

Ruling: this evaluator reads the two Governance getters already required by
BOUNDARY; it does not amend protocol D50 S0 or its frozen 55-request count.
A1-0116/A2-0062 provide correlated code-reading/synthetic differential notes,
not source READYs, measured chain evidence or new ACKs. No open-schedule RFC
is needed for this slice. Wrong deployment values cannot become F evidence.

Ruling: reuse RpcClient transport pinning, loopback restrictions and raw command
logs; accept an injected call/checkpoint object for isolated byte-level tests.
The new collector has its own finite deadline and 128-call cap. These are local
evaluator limits, not a measurement or a new shared S0 schedule. A future exact
execution recipe must pin them and the actual RpcClient/tool/source identities.

No services, deployment, existing consumer switch, dependency, peer edit,
worktree or extra agent. Same-author review is correlated. Tests use synthetic
RPC answers and real owner-exported ABIs; they cannot attest a running chain.
