# Initial corrected-matrix preflight — 2026-11-14

This historical run corrected the earlier wrong matrix path and matched all 32 IDs, but it was captured before A1-0129 was folded into the plan and checker. It is superseded by `../preflight-20261114-r3/README.md`.

The old manifest records prefix-only interface, matrix and TLC pins, unpinned coverage/toolchain files, and the root toolchain/TLC scope discrepancy. The amended r3 plan now carries exact hashes and a separately pinned F-only TLC jar. This run remains useful as the first corrected-matrix result, not as the final preflight checkpoint.

No service started and no case ran in this historical run. Its 2,974-pass full suite predates the A1-0129 test/checker changes; use the r3 run for current verification.
