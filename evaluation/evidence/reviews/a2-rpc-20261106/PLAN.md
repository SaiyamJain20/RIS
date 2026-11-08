# A2-0065 source review plan — 2026-11-06

C-F1; synthetic reconstruction/extension review only. No runtime READY or
execution ACK inferred. No extra agents, worktrees, peer writes or chain starts.

1. Pin source/publication 3b86183b8f537e32fc2f2c3be8b650735ab8173a and delta from
   reviewed f2c86ad. Verify complete protocol inventory, prior 408-entry READY
   against its original source, ledger READY, frozen interfaces/F0, copied ABIs,
   communication provenance, tools, selected evaluator inputs and helper hashes.
2. Test explicit valid/invalid raw replies through the public RpcBindingView API;
   probe integer canonicality and ABI trailing/offset handling separately from
   authorization or chain truth. Preserve unexpected results. Do not edit owner.
3. Run scoped RPC/binding tests, then isolated protocol selection if justified.
   Extend only coordinator selector to exclude new live_f/live_e fixtures and
   guard setup; local synthetic loopback HTTP fixtures are permitted. Owner live
   tests/mutation counts remain read-only unless explicitly rerun.
4. Recheck sources and peers; publish factual REVIEW A3-0091 and owned handoff.
   Full runtime READY/mapping and separate exact source/tools/config/run FREEZE
   ACKs still precede integrated services. Qualified E unchanged; F NOT_RUN/G locked.

Environment is inherited with explicit PYTHONPATH/PYTHONDONTWRITEBYTECODE and
selection output path. No full environment reproducibility claim. Evidence
scripts exercise existing behavior; no shared interface or runtime changes.
