"""Read-only timing attribution from retained commands; never starts services.

Only command method names, timestamps, exit codes and source hashes are emitted.
Unmeasured Python/serialization/hash overhead is explicitly unattributed.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp(value):
    return datetime.fromisoformat(value).timestamp()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prior-output', required=True, type=Path)
    parser.add_argument('--cast', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    inputs = {}
    rows = []
    for profile in ('paper-strict', 'paper-minimal', 'repaired-e'):
        base = args.prior_output / (profile+'-nonce-replay') / profile
        result_path = base/'alice/nonce-replay/result.json'
        inputs[str(result_path)] = digest(result_path)
        result = json.loads(result_path.read_text())
        start, end = stamp(result['startedAt']), stamp(result['endedAt'])
        groups = {}
        for label, path in [('pbc', base/'pbc-rpc/commands.json'),
                            ('dbc', base/'dbc-rpc/commands.json'),
                            ('exporter', base/'commands.json')]:
            inputs[str(path)] = digest(path)
            selected = [r for r in json.loads(path.read_text())
                        if start <= stamp(r['startedAt']) and stamp(r['endedAt']) <= end]
            assert all(r['exitCode'] == 0 and not r['timedOut'] for r in selected)
            if label == 'exporter':
                assert all('hmbc_protocol.worker_log' in r['argv'] and '--state-dir' in r['argv'] for r in selected)
            groups[label] = dict(count=len(selected),
                                 seconds=sum(r['elapsedSeconds'] for r in selected),
                                 methods=dict(Counter(r['argv'][2] for r in selected)) if label != 'exporter' else {},
                                 commands=[dict(method=r['argv'][2] if label != 'exporter' else 'redacted-worker-export',
                                                startedAt=r['startedAt'], endedAt=r['endedAt'],
                                                elapsedSeconds=r['elapsedSeconds'], exitCode=r['exitCode']) for r in selected])
        duration = end-start
        measured = sum(g['seconds'] for g in groups.values())
        assert 0 < measured < duration
        rpc_count = groups['pbc']['count']+groups['dbc']['count']
        rows.append(dict(profile=profile, startedAt=result['startedAt'], endedAt=result['endedAt'],
                         probeSeconds=duration, groups=groups, measuredSubprocessSeconds=measured,
                         unattributedOutsideSubprocessSeconds=duration-measured,
                         rpcCount=rpc_count, castFullHashCallsFromSource=2*rpc_count))
    before = digest(args.cast)
    # Same read_bytes + sha256 primitive as evaluation.manifests.sha256.
    for _ in range(10):
        assert digest(args.cast) == before
    timings = []
    for _ in range(30):
        start = time.perf_counter()
        assert digest(args.cast) == before
        timings.append(time.perf_counter()-start)
    assert digest(args.cast) == before
    assert all(digest(path) == value for path, value in inputs.items())
    report = dict(scope='read-only diagnosis; no new integrated trial or fix claim',
                  priorInputs=inputs, priorInputsStable=True, rows=rows,
                  hashMicrobenchmark=dict(path=str(args.cast), sha256=before, sizeBytes=args.cast.stat().st_size,
                                          warmup=10, repetitions=30, seconds=timings,
                                          medianSeconds=statistics.median(timings)),
                  limitations=['Historical command intervals omit hash/JSON/ABI/Python work and are not full RPC duration.',
                               'Outside-subprocess time is measured by subtraction, not attributed exclusively to hashing.',
                               'Current-host hash microbenchmark cannot recover historical hash durations.',
                               'Historical single trial per profile; no latency distribution or production performance claim.'])
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps([dict(profile=r['profile'], probeSeconds=r['probeSeconds'],
                           rpcCount=r['rpcCount'], measuredSubprocessSeconds=r['measuredSubprocessSeconds'],
                           unattributedSeconds=r['unattributedOutsideSubprocessSeconds']) for r in rows]))


if __name__ == '__main__':
    main()
