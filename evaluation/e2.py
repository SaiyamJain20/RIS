"""Exact-plan gated, fresh two-chain C-E2 logical recovery comparison slice.

Six cases across three profiles, each with wrong-issuer, Alice recovery and Bob
policy-denial controls. This slice does not execute the complete 56-case catalog,
revocation-window/mutant matrix, power-loss tests or an RQ gate.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform

from evaluation import e1
from evaluation.access_artifacts import require
from evaluation.bootstrap import FREEZE_SHA256
from evaluation.manifests import now, sha256

ROOT = e1.ROOT
CONTRACT = ROOT/'evaluation/evidence/e2/formal-and-hook-review-20261009/start-contract-r1.json'
ACCEPTANCE = ROOT/'evaluation/evidence/e2/crash-transport-20261009/start-contract-acceptance.json'


def _sources():
    paths = [p for p in (ROOT/'evaluation').rglob('*.py') if 'tests' not in p.relative_to(ROOT/'evaluation').parts]
    paths += list((ROOT/'evaluation/fixtures').rglob('*.json'))
    paths += list((ROOT/'interfaces/v1').rglob('*'))+list((ROOT/'interfaces/proposals/v1').rglob('*.json'))
    paths += [ROOT/p for p in ('AGENTS.md', 'SPEC.md', 'PLAN.md', 'uv.lock', 'pyproject.toml', 'evaluation/toolchain.json')]
    paths += [CONTRACT, ACCEPTANCE, e1.PIN_REVIEW]
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(set(paths)) if p.is_file()}


def _owners(contract):
    result = {}
    for name in ('ledger', 'protocol'):
        pin = contract[name]
        raw = e1._git_blob(pin['commit'], name+'/evidence/source-manifest.sha256')
        require(hashlib.sha256(raw).hexdigest() == pin['manifestSha256'], 'accepted owner inventory')
        entries = {}
        for line in raw.decode().splitlines():
            digest, path = line.split(maxsplit=1); path = path.lstrip('*')
            require(path not in entries, 'unique owner inventory path')
            entries[path] = digest
        require(len(entries) == pin['entries'], 'accepted inventory length')
        result[name] = dict(commit=pin['commit'], inventorySha256=pin['manifestSha256'], entries=entries)
    return result


def create_plan(*, run_id, freeze_message):
    # Retain the previously reviewed environment, mining/ports, tool and custody
    # recipe; any new exact runtime bytes require new full execution-plan ACKs.
    plan = e1.create_plan(run_id=run_id, freeze_message=freeze_message)
    contract = json.loads(CONTRACT.read_text())
    plan.update(schemaVersion='hmbc-e2-recovery-plan/v1', executionScope='six fresh logical crash/recovery cases; not full RQ matrix',
                owners=_owners(contract), agent3Sources=_sources(), startContractSha256=sha256(CONTRACT),
                startupAcceptanceSha256=sha256(ACCEPTANCE), fullCatalogComplete=False, mining='Anvil automatic mining; explicit pending clock probes',
                matrix=[dict(profile=profile, point=point) for profile in e1.PROFILES for point in ('after_intent', 'after_send')],
                controls=['wrong-admin-before-H2', 'registered-Alice-crash-cached-retry-outcome', 'registered-Bob-policy-deny'],
                freshness='fresh chain pair, deployment, protocol state and snapshots per matrix row',
                restart='production adapter on identical private state/deployment; one restart; no expiry extension',
                observation='empty EOF after_intent or one validated frame then EOF after_send; natural86, empty stderr; same cached response',
                workerExpected={'after_intent': dict(crashEvents=['RELEASE_INTENT'], crashAttempts=[0, 0], retryEvents=['RELEASE_INTENT', 'RELEASE_SENT'], retryAttempts=[1, 1]),
                                'after_send': dict(crashEvents=['RELEASE_INTENT', 'RELEASE_SENT'], crashAttempts=[1, 0], retryEvents=['RELEASE_INTENT', 'RELEASE_SENT', 'RELEASE_SENT'], retryAttempts=[2, 1])},
                timing='retry strictly before original native grant expiry; unexpected expiry fails run, never extends permission',
                limitations=['Both exact full plan ACKs required; supplement ACKs are insufficient.',
                             'Six logical recovery comparisons only; complete56 catalog/mutants/revocation windows/report/gate remain required.',
                             'Paper crash classification remains BLOCKED/unproved until explicit report qualification.',
                             'Symbolic crypto, safe-ledger/trusted-worker assumptions; no recipient delivery, ABE, consensus, power-loss or OS-kill proof.'])
    return plan


def verify_plan(plan):
    require(plan == create_plan(run_id=plan['runId'], freeze_message=plan['freezeMessage']), 'exact current E2 plan/source/config')
    require(sha256(ROOT/'interfaces/v1/FREEZE.json') == FREEZE_SHA256, 'immutable v1 freeze')
    require(platform.python_version() == plan['pythonVersion'], 'pinned Python version')
    for tool in plan['tools'].values():
        require(Path(tool['path']).is_file() and sha256(tool['path']) == tool['sha256'], 'tool binary hash')
    acceptance = json.loads(ACCEPTANCE.read_text())
    require(acceptance['status'] == 'ACCEPTED_SCOPED_STARTUP_SUPPLEMENT_ONLY'
            and acceptance['contract']['sha256'] == plan['startContractSha256'], 'accepted scoped startup contract')
    contract = json.loads(CONTRACT.read_text())
    require(hashlib.sha256(e1._git_blob(contract['protocol']['commit'], 'protocol/testtools/faulty_adapter.py')).hexdigest()
            == contract['protocol']['hookSha256'], 'accepted exact hook')
    for owner in plan['owners'].values():
        e1._owner_paths(owner)
        for path, digest in owner['entries'].items():
            require(hashlib.sha256(e1._git_blob(owner['commit'], path)).hexdigest() == digest, 'exact owner input blob')


def execute(plan_path, ack_path, output):
    output = Path(output); output.mkdir(parents=True, exist_ok=False, mode=0o700)
    record = dict(rq='E', executionMode='two-chain-e2-recovery-slice', adapterMode='symbolic', status='BLOCKED',
                  startedAt=now(), endedAt=None, cases={}, servicesStarted=[], acks=None, failure=None, sourceStable=None,
                  limitation='Six logical process recovery comparisons only; no complete catalog or RQ gate.')
    authorized = False; case_records = {}
    try:
        raw = Path(plan_path).read_bytes(); plan = json.loads(raw)
        record['planSha256'] = hashlib.sha256(raw).hexdigest(); verify_plan(plan)
        record['acks'] = e1._acks(ack_path, plan, record['planSha256'])
        authorized = True; record['status'] = 'RUNNING'
        for item in plan['matrix']:
            verify_plan(plan)
            case = item['profile']+'-'+item['point']; destination = output/case; destination.mkdir()
            child = dict(profiles={}, servicesStarted=[], adapterProcesses=[])
            case_records[case] = child
            record['cases'][case] = dict(status='RUNNING', manifest=case+'/manifest.json')
            (output/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
            selected = copy.deepcopy(plan); selected['runId'] = plan['runId']+'-'+item['point']
            e1._profile(selected, item['profile'], destination/item['profile'], child, recovery_point=item['point'])
            proof = json.loads((destination/item['profile']/'recovery/result.json').read_text())
            require(proof['ok'] is True and proof['delivery'] == 'unknown', 'complete checked recovery result')
            record['cases'][case]['status'] = 'RECOVERY_CONTROL_PASS'
        verify_plan(plan); record.update(status='E2_RECOVERY_SLICE_PASS', sourceStable=True)
    except BaseException as error:
        record['failure'] = dict(type=type(error).__name__, message=str(error))
        record['status'] = 'FAILED' if authorized else 'BLOCKED'
        if authorized: record['sourceStable'] = _sources() == plan['agent3Sources']
        if not isinstance(error, Exception): raise
    finally:
        record['servicesStarted'] = [dict(case=case, **entry) for case, child in case_records.items() for entry in child['servicesStarted']]
        record['endedAt'] = now()
        (output/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True); p.add_argument('--acks', type=Path); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); result = execute(args.plan, args.acks, args.output)
    print(json.dumps({k: result[k] for k in ('status', 'failure', 'sourceStable', 'servicesStarted')}, indent=2))
    return 0 if result['status'] == 'E2_RECOVERY_SLICE_PASS' else 2


if __name__ == '__main__': raise SystemExit(main())
