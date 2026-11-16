# Evidence: production process transport, TEST-ONLY hooks H4/H5/H6, H7 process tests, live Foundry locator fix

Committed code: `4af9a0f` (`hmbc_protocol/witness_process_transport.py`, `testtools/{faulty_witness,compromised_worker,delayed_witness}.py`, six test files, two mutation runners, `tests/test_rpc_binding_view_live.py` locator fix). Used by the start-contract RFC A2-0074.
PAPER-DERIVED RECONSTRUCTION; symbolic mode; synthetic TEST-ONLY keys; one host; CPython 3.13.12, pytest 9.0.2, eth-account 0.14.0, jsonschema 4.26.0 (frozen root `uv.lock` 1fb4777a..); Foundry 1.8.5 and solc 0.8.37 hash-verified against `interfaces/v1/toolchain.json` before use.
**Who produced what:** the transport, the hooks, their tests and runners were written by forked sub-agents (on the human's instruction, 2026-11-07). Files prefixed `FORK-` are what a fork recorded and are NOT relied on. Files prefixed `PARENT-` are runs I made myself on the tree or on a clone of the committed bytes, and they are the evidence. Review is correlated (same model family).

## Parent-verified results
| Check | Result | File |
|---|---|---|
| Offline tests of both forks (5 files, `-k "not live"`), tree = HEAD d7e0426 plus the uncommitted files that became 4af9a0f | **156 passed, 0 skipped**, exit 0, 39 s | `PARENT-offline-156-passed.txt` |
| Live tests of both forks (real Anvil pair, agent 1's F ledger 85c59f5, real `witness_main` processes), `-k live` | **23 passed, 0 skipped**, exit 0, 262 s; no `anvil` or `witness_main` process left behind (`pgrep` = 0) | `PARENT-live-23-passed.txt` |
| `run_witness_process_transport_mutants.py` on a clone of exactly `4af9a0f` | control passes; **92 / 92 detected**, exit 0, 17 min | `PARENT-runner-transport-92of92-on-clone-of-4af9a0f.txt` |
| `run_witness_hooks_mutants.py --live` on the same clone | control passes with no skips; **46 / 46 detected**, exit 0, 12 min | `PARENT-runner-hooks-46of46-on-clone-of-4af9a0f.txt` |
| Foundry locator: `test_rpc_binding_view_live.py` with `HOME` lacking `~/.local/share/hmbc-tools` but `HMBC_FOUNDRY_DIR` set | RED **19 skipped in 0.33 s**; after the fix (it uses `support.foundry()`) GREEN **19 passed in 127 s**, same `HOME` | `PARENT-locator-RED-19-skipped.txt`, `PARENT-locator-GREEN-19-passed.txt` |

## Fork-recorded history (kept, not relied on)
- **Transport runner:** run 1 left survivors (`L2` label count unchecked, `S2` a non-directory state path accepted, `T1` a reply at the deadline returned before the timer, and others); run 2 was 90 / 92 with exit 1 (`N3` timed out, `D1` survived); tests were added; run 3 was 92 / 92 (`FORK-A-runner-run1/2/3-*`). Fork A then died on a network error before writing its report; I verified the module and tests myself, as above.
- **Hooks runner:** run 1 was 39 / 40 (`D13`, the default hold position `before`, survived: a real test gap, closed by a test of `main()`'s arguments); run 2 was 46 / 46 with 2 argued equivalents (`F13`/`F14`: each of the two store wrappers dropped alone, because `init_store` delegates to `open_store`; dropping both is detected) (`FORK-B-runner-run1/2-*`).
- **RED runs:** H4 22 failed / 1 passed, H5 19 failed / 2 passed (`FORK-B-H4/H5-RED-*`). **H6 has no right-reason RED:** its module was written right after its tests, the RED was reproduced afterwards by moving the module aside (a missing-module RED only), so the H6 evidence is its mutants, and I say so plainly. The first live H7 run had 1 failure that was the fork's own test bug (`os.makedirs(mode=0o700)` leaves the intermediate state directory 0o755, which the witness correctly refused).

## What the tests establish, and what they do not
- H4 `faulty_witness`: exit 86 at `before_commit`/`after_commit`; after `after_commit` a restart replies with the RECORDED value and `CONFLICT_PINNED` for any other (live row F-13).
- H5 `compromised_worker` (a class, no runner-facing command yet): releases for explicit claims without a ledger-committed grant, honest for every other grant; the real ledger has no grant and the PBC never forwarded the request, while the honest worker answers `NOT_COMMITTED`. **Symbolic only: no secrecy or ABE conclusion.**
- H6 `delayed_witness`: replies byte-identical to production, only later; SIGKILL during an `after` hold leaves the record durable, during a `before` hold leaves nothing.
- H7: a real `witness_main` refuses corrupt (`STORE_CORRUPT`), missing-behind-a-marker (`STORE_MISSING`), rows-without-marker, marker-disagrees, another deployment's store (`BINDING_MISMATCH`) and another witness's store (`OWNER_MISMATCH`) with one closed JSON line, exit 2, nothing written. **A main-file-only copy is NOT refused**: it starts and signs a different value for a key already signed (the undetectable rollback of INVENTORY FM-14, measured live); the consistent three-file copy keeps the pin.
- Transport: pid files (decimal pid + LF, mode 0600, atomic, left after death), bounded stderr files (4096 bytes), no respawn, `command_for` seam, monotonic clock only, strict reply parsing.
- **Not established:** power-loss or OS-kill durability (process death only); anything through ONE adapter command (the CLI wiring is separate: `test_adapter_v2_main_wiring*.py`); real-process H1/H3; any F case or gate. H6's checks use real-time thresholds and could flake on a heavily loaded host.
