# Return review by agent 2 (A2-0039), 2026-10-12

Scope: agent 2's own module `protocol/**` and the solo-phase work (2026-10-09..12) done in agent 2's name by a same-model proxy (A1-0059, A1-0086). Synthetic data, one host, Python 3.13.12.
**Independence limit:** the reviewer is the same model family as the proxy and as agents 1 and 3. Everything below is therefore a mechanical re-execution or a measurement, not an independent
judgement; where a claim needed judgement it is marked as such in A2-0039.

| # | Claim checked | Method | Result | File |
|---|---|---|---|---|
| 1 | Production bytes unchanged by the solo phase (A1-0086 s4) | `git rev-parse <commit>:<dir>` for `hmbc_protocol`, `testtools`, `exports`, `abi` at `origin/agent-2` and `origin/agent-1` | identical tree hashes (89b05b0c.., e546ce36.., 04f0a5d2.., ad3db606..) | (commands below) |
| 2 | Manifests verify | `sha256sum -c` | 108/108 at my tip (hash d16ddad8..), 127/127 at agent-1 tip (551e9f77..); no tracked non-evidence file is missing from the manifest | (commands below) |
| 3 | Ledger contracts never changed between the E1 pin 91add8c, 933d2a7 and agent-1's tip | `git rev-parse <c>:ledger/src` | one tree hash 47f30e7c.. at all three | `environment.txt` |
| 4 | My module at my own tip 96ebe16 | full suite | 1365 passed, 201 skipped in 300 s, no failure line (exit code not captured: the run was piped to `tail`); same counts as A2-0020 | (not archived) |
| 5 | Solo-phase suite at agent-1 tip 6911478 | full suite, scratch clone | **1375 passed, 201 skipped, exit 0, 321 s** (claimed 1375/201) | `suite-agent1-tip-6911478.txt` |
| 6 | The three solo-phase mutants (routing, recovery, restart) are real | `mutation_check.py --only routing,recovery,restart` on a scratch clone | 3/3 DETECTED, 0 survivors; baseline 1375/201; sources restored | `mutation-reexecution-p2-t1-t3.json` |
| 7 | Proxy gate-freeze review S2-0021 | script re-run unchanged (`python -I`) | exit 0, `problems: []`, 294/294 leaves equal | `review-script-reexecution.txt` |
| 8 | Proxy gate-run review S2-0022 over 2126 published files | script re-run unchanged | exit 0, `problems: []`, 56 rows, 48+18 decisions, 180 never-instantiated probes; only RQ1-E.md line numbers differ (report revised later) | `review-script-reexecution.txt` |
| 9 | Recorded mutation detections are failed assertions, not collection errors | classify `pytestTail` of every recorded mutant | 98/98 detections are "N failed" | (commands below) |
| 10 | The 8 "equivalent" survivors are really unreachable | read each reason against `KSSC.sol` and `RSC.sol` | the `allowed`/`exists`/grantId reason holds: `requestData` is the only write path and stores `Grant(true,true,...)` | (commands below) |
| 11 | **NEW defect:** `worker_log.export` mishandles state paths containing `#`, `?`, `%` | offline Worker + exporter | stray empty database created beside the directory; a different database read silently; or OperationalError | `worker-log-uri-defect-demo.txt`, `worker-log-uri-RED-before-fix.txt` |
| 12 | Fix for 11 (test first) | 7 new tests RED 6 failed/1 passed, then GREEN | 7 passed; `test_worker_log.py` + `test_adapter_process_paper.py` 13 passed; 2 new mutants 2/2 DETECTED | `worker-log-uri-GREEN-*.txt`, `mutation-check-worker-log-uri.json` |
| 12b | D49 (worker created lazily; relied on by 180 never-instantiated probes) was untested | new test `test_only_encrypt_record_release_and_finish_decryption_ever_create_the_worker_database`; mutant "a witness op instantiates the worker" | test GREEN on real code (23 passed in the file); mutant 1/1 DETECTED by the tool on the intended assertion | `mutation-check-d49-worker-not-eager.json` |
| 12c | Finished working tree | full suite, real tree, no HMBC_WRITE_EVIDENCE | **1383 passed, 201 skipped, exit 0, 324 s**; tracked files untouched by the run | `suite-final-working-tree.txt` |
| 13 | Worker deployment fingerprint can tell deployments apart | live fresh-chain deployments of six profiles | **no**: clean repaired-e, both mutant-* and both paper profiles share `9886222d..` | `fingerprint-measurement.txt` |
| 14 | Refuted: a retry could return a different response because a GID's recipient key changed | read `RSC.register` | refuted: `ALREADY_REGISTERED`, the key is write-once | (commands below) |

## Commands (repository root of the scratch clone unless stated)

```
# environment: see environment.txt (HOME redirected to a scratch dir; Foundry/solc hashes verified against the repo's pins before use)
git rev-parse origin/agent-2:protocol/hmbc_protocol origin/agent-1:protocol/hmbc_protocol          # likewise testtools, exports, abi
sha256sum -c --quiet protocol/evidence/source-manifest.sha256
python -m pytest protocol/tests -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider -rs -q
python protocol/tools/mutation_check.py --only routing,recovery,restart --out <scratch>/mut.json
python -I protocol/evidence/reviews/s2-0021-gate-freeze/review_gate_freeze.py.txt <repo root>
python -I protocol/evidence/reviews/s2-0022-gate-run/review_gate_run.py.txt evaluation/evidence/e3/gate-run-20261012 <repo root> <scratch>
python protocol/tools/mutation_check.py --only worker_log --grep quote_from_bytes --out <scratch>/mut-uri.json
```

## What this review did not do

Re-run the 4749 s integrated gate run; re-check ledger facts, native evidence or agent 3's oracles beyond reading the two proxy scripts' outputs; re-read the paper's figures behind D47; run the
full mutation check (73 + 21 + 9 + 3 older mutants were read, not re-run); test power-loss or OS-kill durability; validate anything against a second host or a consensus ledger.
