# Owned witness RPC capture implementation plan

Agent 3 / C-F1 continues A3-0160, inline, under the existing F0 implementation
authorization. This closes part of the runner acquisition gap; it does not
authorize services or integrated cases. The human's 2026-11-16 continuation
request specifically rejects replacing unfinished implementation with repeated
branch/status checks. No extra agents or worktrees.

## Design and scope

Extend the existing bounded `JsonLinesProcess` in a new F-only module; leave
the E transport and frozen interfaces unchanged. Record request/response bytes
at the actual pipe exchange boundary, rather than accepting caller-made events.
Only the four public witness RPC kinds are admitted. Count attempted exchanges
inside the transport, retain a lossless hex wire journal, and build the existing
capture/receipt format from successfully parsed and correlated replies.

At shutdown, close stdin and drain stdout to EOF within a bounded budget before
the existing owned-process cleanup. Missing replies, malformed replies, wrong
IDs, extra stdout, stderr, nonzero exits and forced termination must prevent a
usable completed capture. Record process identity, counts and artifact hashes.
Completion means this owned pipe session was observed cleanly; it does not
authenticate ledger observations, honest witness behavior, off-channel signing,
signed-history completeness or persistence. Cryptographic capture authenticity
and global transcript completeness remain false. A caller-provided process may
be malicious. Only synthetic child probes run in this checkpoint.

Alternatives: caller-sealed dictionaries already exist but cannot establish
acquisition; copying the full E transport would duplicate lifecycle logic.
Reuse the transport and keep the new collector separate from E.

## Tasks and acceptance

- [x] Add `evaluation/tests/test_owned_witness_capture.py`: successful sequential
  replies with reused IDs; all four signed kinds join to existing synthetic
  signed history; exact response bytes survive; pre-send rejection preserves the
  session; missing/malformed/wrong-ID replies fail; shutdown detects trailing
  stdout, stderr, nonzero exits and forced termination; final capture is not
  available while running or after a failed session; existing output preserved.
- [x] Run tests RED with absent collector and retain command/exit/output.
- [x] Implement `CapturedWitnessProcess` in
  `evaluation/owned_witness_capture.py`, reusing bounded pipe/process handling.
- [x] Run focused GREEN plus existing transport/capture/join regressions. Review
  failure cleanup and claims; add any missing regression before repair.
- [x] Retain commands, logs, tool/source/output hashes and scientific limits.
  Update BOARD and this role's STATUS/HANDOFF/outbox with exact remaining work.
  Preserve report/plan hashes so existing exact-hash reviews remain valid.
- [ ] Review exact changed paths, commit and push normally on agent-3; verify
  remote SHA, preserve unrelated untracked files and release both locks.

Next runner tasks remain baseline orchestration, family drivers, native signing
observations, capture/history integration, post-bracket and E regression.
All 32 cases/Gate F remain NOT_RUN, G LOCKED and execution plan DRAFT/false.
