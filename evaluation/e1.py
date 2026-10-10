"""Hash-frozen local two-chain E1 runner; both exact peer ACKs precede services.

Paper-derived HMBC2020 reconstruction, synthetic fixtures, symbolic decryptability.
This entry point executes E1 controls, not E2 fault schedules or an RQ gate. Peer
source snapshots remain owner-authored. No peer implementation is imported.
"""
import argparse
from contextlib import ExitStack
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import socket
import subprocess
import sys

from eth_utils import keccak

from evaluation.access_artifacts import require
from evaluation.access_execution import execute_access
from evaluation.bootstrap import FREEZE_SHA256, frozen_validate, strict_json
from evaluation.bootstrap_execution import execute_bootstrap
from evaluation.chain import PublicChain, _owned_signer
from evaluation.evm import AbiContract, _hex
from evaluation import host_toolchain
from evaluation.manifests import now, record_command, sha256
from evaluation.processes import JsonLinesProcess, ServiceProcess
from evaluation.rpc import RpcClient

ROOT = Path(__file__).resolve().parents[1]
PIN_REVIEW = ROOT/'evaluation/evidence/e1/collector-20261008/pin-review.json'
PROFILES = ['paper-strict', 'paper-minimal', 'repaired-e']
# Solo phase (A1-0059/A1-0061): agent 1 plus two same-model proxies. Strict
# mode below is unchanged; solo plans/results carry this disclosure.
SOLO = 'solo-correlated'
SOLO_DISCLOSURE = ('Solo phase under the human directive A1-0059: agent 1 and the agent-2/agent-3 proxies are the same '
                   'model, so every review and ACK is correlated self-review, not independent review.')
SOLO_PREFIXES = {'agent-1': 'communication/agent-1/outbox/',
                 'agent-2': 'communication/agent-1/solo/agent-2-proxy/outbox/',
                 'freeze': 'communication/agent-1/solo/agent-3-proxy/outbox/'}


def _runtime_sources():
    paths = list((ROOT/'evaluation').glob('*.py'))+list((ROOT/'evaluation/fixtures/e1').rglob('*.json'))
    paths += list((ROOT/'interfaces/v1').rglob('*.json'))
    paths += [ROOT/name for name in ('uv.lock', 'pyproject.toml', 'evaluation/toolchain.json', 'AGENTS.md', 'SPEC.md', 'PLAN.md')]
    paths += [p for p in [host_toolchain.OVERRIDE] if p.is_file()]
    paths += [PIN_REVIEW]
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(set(paths))}


def create_plan(*, run_id, freeze_message, review_mode='strict'):
    """Create a review artifact only. Publication and ACK receipt are separate."""
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', run_id) is not None, 'run ID')
    require(review_mode in ('strict', SOLO), 'review mode')
    pattern = r'A3-[0-9]{4}' if review_mode == 'strict' else r'S3-[0-9]{4}'
    require(re.fullmatch(pattern, freeze_message) is not None, 'freeze message ID')
    toolchain = json.loads((ROOT/'evaluation/toolchain.json').read_text())
    review = json.loads(PIN_REVIEW.read_text())
    # Frozen hashes always; a path differs only via the reviewed host override.
    resolved = host_toolchain.resolved()
    tools = {name: dict(path=resolved[name]['path'], sha256=resolved[name]['sha256']) for name in ('forge', 'anvil', 'cast', 'solc')}
    require(all(tools[n]['sha256'] == resolved[n]['frozenSha256'] for n in tools), 'frozen tool hashes')
    for name, path in [('python', ROOT/'.venv/bin/python'), ('python3', Path('/usr/bin/python3')), ('bash', Path('/usr/bin/bash'))]:
        tools[name] = dict(path=str(path), sha256=sha256(path))
    plan = dict(schemaVersion='hmbc-e1-integration-plan/v1', rq='E', runId=run_id, freezeMessage=freeze_message,
                interfaceVersion='v1', interfaceFreezeSha256=FREEZE_SHA256, adapterMode='symbolic', profiles=PROFILES,
                logDetailMode='complete-details', ports=dict(pbc=18545, dbc=28545 if review_mode == 'strict' else 18546),
                chainIds=dict(pbc='18545', dbc='28545'),
                deployerSignerRole='relay', deploymentSpeed='owner-default-slow', owners={k: review[k] for k in ('ledger', 'protocol')},
                agent3Sources=_runtime_sources(), tools=tools, pythonVersion=platform.python_version(),
                packagePins={n: importlib.metadata.version(n) for n in ('eth-account', 'eth-abi', 'eth-utils', 'jsonschema', 'pytest')},
                serviceEnvironment=dict(PATH=str(Path(tools['forge']['path']).parent)+':'+os.defpath,
                                        HOME=os.environ.get('HOME','/home/karma'),LC_ALL='C.UTF-8',PYTHONNOUSERSITE='1'),
                dependencyLockSha256=sha256(ROOT/'uv.lock'), budgets=dict(rpc=5, readiness=15, deploy=600, bootstrap=120, transport=10, stopGrace=2),
                controls=['wrong-admin-before-H2', 'registered-Alice-allow', 'registered-Bob-policy-deny'],
                limitations=['Exact owner ACKs of this plan are required before services.',
                             'E1 only; all E2/E3 schedules and RQ gates remain unexecuted.',
                             'RPC consistency and masked runtime templates are not provider integrity or consensus.',
                             'RELEASE_SENT is attempted send; delivery unknown, no ABE or power-loss claim.'])
    moved = {n: resolved[n]['resolution'] for n in ('forge', 'anvil', 'cast', 'solc') if resolved[n]['resolution'] != 'frozen-path'}
    if moved:
        plan['hostToolOverride'] = dict(path='evaluation/host-tools.json', sha256=sha256(host_toolchain.OVERRIDE), resolutions=moved)
    if review_mode == SOLO:
        plan.update(reviewMode=SOLO, reviewDirective='A1-0059', reviewDecision='A1-0061', reviewDisclosure=SOLO_DISCLOSURE,
                    castHashPolicy='checkpoint',
                    hostDifferences=dict(python=dict(frozen=toolchain['hostPython'], actual=platform.python_version())))
    return plan


def _git_blob(commit, path):
    require(re.fullmatch(r'[0-9a-f]{40}', commit) is not None, 'exact Git commit')
    try:
        return subprocess.check_output(['git', 'show', commit+':'+path], cwd=ROOT, stderr=subprocess.PIPE, timeout=10)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ValueError('Pinned Git blob is unavailable') from error


def _owner_paths(owner):
    module = 'ledger' if 'ledger/foundry.toml' in owner['entries'] else 'protocol'
    for path, digest in owner['entries'].items():
        p = PurePosixPath(path)
        require(not p.is_absolute() and '..' not in p.parts and p.parts[0] == module
                and str(p) == path and re.fullmatch(r'[0-9a-f]{64}', digest) is not None, 'owned snapshot path/digest')
    return module


def verify_plan(plan):
    reference = create_plan(run_id=plan['runId'], freeze_message=plan['freezeMessage'], review_mode=plan.get('reviewMode', 'strict'))
    require(plan == reference, 'current exact plan inputs/configuration')
    require(sha256(ROOT/'interfaces/v1/FREEZE.json') == FREEZE_SHA256, 'immutable interface freeze')
    require(platform.python_version() == plan['pythonVersion'], 'Python version')
    for tool in plan['tools'].values():
        require(Path(tool['path']).is_file() and sha256(tool['path']) == tool['sha256'], 'tool binary hash')
    require(sha256(ROOT/'uv.lock') == plan['dependencyLockSha256'], 'root dependency lock')
    for owner in plan['owners'].values():
        _owner_paths(owner)
        for path, digest in owner['entries'].items():
            require(hashlib.sha256(_git_blob(owner['commit'], path)).hexdigest() == digest, 'owner inventory blob')


def _headers(raw):
    fields = {}
    for line in raw.decode('utf-8').splitlines():
        if not line.strip(): break
        key, sep, value = line.partition(':')
        require(bool(sep) and key not in fields, 'unique message header')
        fields[key] = value.strip()
    return fields


def _verify_solo_ack_message(raw, *, agent, plan, plan_sha256):
    """Solo-mode ACK: agent 1 as itself, agent 2's work only as a declared proxy."""
    require(agent in ('agent-1', 'agent-2'), 'solo ACK owner')
    fields = _headers(raw)
    sender = fields.get('From', '')
    if agent == 'agent-1':
        identity = sender == 'agent-1' and re.fullmatch(r'A1-[0-9]{4}', fields.get('Message-ID', '')) is not None
    else:
        identity = (re.fullmatch(r'agent-2 \(proxy[^()\n]*\)', sender) is not None
                    and re.fullmatch(r'S2-[0-9]{4}', fields.get('Message-ID', '')) is not None)
    recipients = [x.strip() for x in fields.get('To', '').split(',')]
    require(identity and fields.get('Type') == 'ACK' and fields.get('RQ') == 'E'
            and fields.get('Interface-version') == 'v1' and fields.get('Responds-to') == plan['freezeMessage']
            and fields.get('Accepted-plan-sha256') == plan_sha256
            and any(x == 'all' or re.fullmatch(r'agent-3( \(proxy[^()]*\))?', x) for x in recipients), 'exact solo plan ACK')
    return fields['Message-ID']


def _verify_solo_freeze(raw, *, plan, plan_sha256):
    fields = _headers(raw)
    require(fields.get('Message-ID') == plan['freezeMessage'] and fields.get('Type') == 'FREEZE'
            and re.fullmatch(r'agent-3 \(proxy[^()\n]*\)', fields.get('From', '')) is not None
            and fields.get('RQ') == 'E' and fields.get('Interface-version') == 'v1'
            and fields.get('Plan-sha256') == plan_sha256, 'exact solo FREEZE for this plan')
    return fields['Message-ID']


def _solo_is_ancestor(commit):
    require(re.fullmatch(r'[0-9a-f]{40}', commit) is not None, 'exact Git commit')
    return subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, timeout=10).returncode == 0


def _solo_acks(path, plan, plan_sha256):
    require(path is not None, 'solo FREEZE and both exact ACK records are absent')
    acks = strict_json(Path(path).read_bytes())
    require(set(acks) == set(SOLO_PREFIXES), 'solo FREEZE plus both ACK records')
    checked = {}
    for key, pin in acks.items():
        require(set(pin) == {'commit', 'path', 'sha256'} and pin['path'].startswith(SOLO_PREFIXES[key])
                and '..' not in PurePosixPath(pin['path']).parts, 'solo record provenance')
        raw = _git_blob(pin['commit'], pin['path'])
        require(hashlib.sha256(raw).hexdigest() == pin['sha256'], 'solo record file hash')
        require(_solo_is_ancestor(pin['commit']), 'solo record committed in the integrated history')
        message = (_verify_solo_freeze(raw, plan=plan, plan_sha256=plan_sha256) if key == 'freeze'
                   else _verify_solo_ack_message(raw, agent=key, plan=plan, plan_sha256=plan_sha256))
        checked[key] = dict(pin, messageId=message)
    return checked


def verify_ack_message(raw, *, agent, plan, plan_sha256):
    """Parse exact project ACK metadata; a READY or willingness is insufficient."""
    if plan.get('reviewMode') == SOLO:
        return _verify_solo_ack_message(raw, agent=agent, plan=plan, plan_sha256=plan_sha256)
    require(agent in ('agent-1', 'agent-2'), 'ACK owner')
    fields = {}
    for line in raw.decode('utf-8').splitlines():
        if not line.strip(): break
        key, sep, value = line.partition(':')
        require(bool(sep) and key not in fields, 'unique ACK header')
        fields[key] = value.strip()
    require(fields.get('From') == agent and fields.get('Type') == 'ACK' and fields.get('RQ') == 'E'
            and fields.get('Interface-version') == 'v1' and fields.get('Responds-to') == plan['freezeMessage']
            and fields.get('Accepted-plan-sha256') == plan_sha256
            and any(x.strip() in ('agent-3', 'all') for x in fields.get('To', '').split(',')), 'exact plan ACK')
    require(re.fullmatch('A'+agent[-1]+r'-[0-9]{4}', fields.get('Message-ID', '')) is not None, 'ACK message identity')
    return fields['Message-ID']


def _acks(path, plan, plan_sha256):
    if plan.get('reviewMode') == SOLO:
        return _solo_acks(path, plan, plan_sha256)
    require(path is not None, 'both exact integration FREEZE ACKs are absent')
    acks = strict_json(Path(path).read_bytes())
    require(set(acks) == {'agent-1', 'agent-2'}, 'both integration ACK records')
    checked = {}
    for agent, pin in acks.items():
        require(set(pin) == {'commit', 'path', 'sha256'} and pin['path'].startswith('communication/'+agent+'/outbox/')
                and '..' not in PurePosixPath(pin['path']).parts, 'ACK provenance record')
        raw = _git_blob(pin['commit'], pin['path'])
        require(hashlib.sha256(raw).hexdigest() == pin['sha256'], 'ACK file hash')
        ancestry = subprocess.run(['git', 'merge-base', '--is-ancestor', pin['commit'], 'origin/'+agent], cwd=ROOT, timeout=10)
        require(ancestry.returncode == 0, 'ACK belongs to fetched owner history')
        checked[agent] = dict(pin, messageId=verify_ack_message(raw, agent=agent, plan=plan, plan_sha256=plan_sha256))
    return checked


def materialize_owner(owner, destination):
    _owner_paths(owner)  # validate the complete inventory before the first write
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=False)
    for path, digest in owner['entries'].items():
        raw = _git_blob(owner['commit'], path)
        require(hashlib.sha256(raw).hexdigest() == digest, 'snapshot source hash')
        target = destination/path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    return destination


def _snapshot_stable(owner, destination):
    return all(sha256(destination/path) == digest for path, digest in owner['entries'].items())


def check_runtime_bytecode(raw, artifact):
    """Compare compiler template outside explicitly declared immutable slots."""
    actual = bytearray(_hex(raw)); template = bytearray(_hex(artifact['object']))
    require(actual and len(actual) == len(template), 'runtime code length')
    intervals = []
    for refs in artifact.get('immutableReferences', {}).values():
        for ref in refs:
            start, length = ref['start'], ref['length']
            require(type(start) is int and type(length) is int and start >= 0 and length > 0 and start+length <= len(actual), 'compiler immutable bounds')
            require(all(start+length <= lo or start >= hi for lo, hi in intervals), 'compiler immutable disjoint slots')
            intervals.append((start, start+length))
            actual[start:start+length] = bytes(length); template[start:start+length] = bytes(length)
    require(actual == template, 'runtime compiler template')


def _available(ports):
    with ExitStack() as stack:
        for port in ports.values():
            s = stack.enter_context(socket.socket())
            # A stopped profile can leave TCP TIME_WAIT connections. Match the
            # next server's bind semantics while still refusing live listeners.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))


RELAY_VARIANTS = ('forged-tuple', 'new-reference-replay', 'same-nonce-distinct-digests')


def observe_worker_export(exit_code, raw, state_dir):
    """Classify one pinned `hmbc_protocol.worker_log --state-dir` result (S3-0008).

    Exit 0 with a JSON object is an instantiated export. A verified never-instantiated
    worker needs exit 1 with exactly the exporter's own message for this state dir AND
    both database paths absent on the filesystem; it is recorded explicitly, never as
    an empty export. Anything else is a failure.
    """
    state_dir = Path(state_dir)
    if exit_code == 0:
        require(bool(raw) and isinstance(strict_json(raw), dict), 'non-empty worker export object')
        return dict(instantiated=True, export=raw)
    nested, direct = state_dir/'worker'/'worker.sqlite', state_dir/'worker.sqlite'
    expected = f'no worker.sqlite in {state_dir} (looked in <dir>/worker/ and in <dir>)\n'.encode()
    require(exit_code == 1 and raw == expected and not nested.exists() and not direct.exists(),
            'verified never-instantiated worker export refusal')
    return dict(instantiated=False, exitCode=1, message=expected.decode(), checkedAbsent=[str(nested), str(direct)])


def _profile(plan, profile, output, record, *, recovery_point=None, expired_retry=False, duplicate_outcome=False, nonce_replay=False,
             subject_substitution=False, relay_stress=None):
    require(type(expired_retry) is bool and (not expired_retry or recovery_point is not None), 'expiry probe follows explicit recovery')
    require(type(duplicate_outcome) is bool and (not duplicate_outcome or (recovery_point is None and not expired_retry)),
            'duplicate comparison uses production adapter without other fault probes')
    require(type(nonce_replay) is bool and (not nonce_replay or
            (recovery_point is None and not expired_retry and not duplicate_outcome)), 'isolated production nonce replay')
    require(type(subject_substitution) is bool and (not subject_substitution or
            (recovery_point is None and not expired_retry and not duplicate_outcome and not nonce_replay)), 'isolated subject stress')
    require(relay_stress is None or (relay_stress in RELAY_VARIANTS and recovery_point is None and not expired_retry
            and not duplicate_outcome and not nonce_replay and not subject_substitution), 'isolated relay stress')
    output.mkdir(parents=True, exist_ok=False)
    snapshots = output/'snapshots'
    ledger_root = materialize_owner(plan['owners']['ledger'], snapshots/'ledger')
    protocol_root = materialize_owner(plan['owners']['protocol'], snapshots/'protocol')
    tools = plan['tools']; budget = plan['budgets']; commands = []
    record['profiles'][profile] = dict(status='RUNNING', sourcesStable=None, commands=commands)
    ledger = ledger_root/'ledger'; protocol = protocol_root/'protocol'
    service_env = plan['serviceEnvironment']
    env = dict(service_env)
    env.update(FOUNDRY_SOLC=tools['solc']['path'], DEPLOYER_PK='0x'+_owned_signer('relay').key.hex(),
               PBC_CHAIN_ID='18545', DBC_CHAIN_ID='28545', LEDGER_DEPLOY_FAST='0')

    def command(label, argv, cwd, timeout, environment=None):
        row = record_command(argv, cwd, output/(label+'.txt'), timeout=timeout, env=environment, owned_process_group=True, stop_grace=budget['stopGrace'])
        commands.append(row)
        (output/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(row['exitCode'] == 0, 'owner command '+label)
        return (output/(label+'.txt')).read_bytes()

    services = []
    rpcs = {}
    hash_policy = 'checkpoint' if plan.get('castHashPolicy') == 'checkpoint' else 'per-call'
    try:
        _available(plan['ports'])
        with ExitStack() as stack:
            for name in ('pbc', 'dbc'):
                port = plan['ports'][name]; url = f'http://127.0.0.1:{port}'
                service = stack.enter_context(ServiceProcess([tools['anvil']['path'], '--host', '127.0.0.1', '--port', str(port),
                                                             '--chain-id', plan['chainIds'][name], '--hardfork', 'cancun', '--silent'],
                                                            cwd=ROOT, output=output/(name+'-service'), stop_grace=budget['stopGrace'],env=service_env))
                services.append(service); record['servicesStarted'].append(dict(profile=profile, chain=name, port=port, pid=service.pid))
                (output.parent/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
                rpc = RpcClient(url, cast=tools['cast']['path'], cast_sha256=tools['cast']['sha256'], cwd=ROOT,
                                output=output/(name+'-rpc'), timeout=budget['rpc'],env=service_env, hash_policy=hash_policy)
                rpc.checkpoint('run-start')
                # Port availability was checked before this direct child. Only
                # this owned child may be stopped; occupied ports are never cleaned.
                def ready(rpc=rpc, name=name):
                    try: return str(int(rpc.call('eth_chainId'), 16)) == plan['chainIds'][name]
                    except RuntimeError: return False  # retained CLI refusal while starting
                service.wait_ready(ready, timeout=budget['readiness']); rpcs[name] = rpc
                for role in ('relay', 'H1-ca-admin', 'H2-ca-admin', 'H3-ca-admin', 'H4-ca-admin'):
                    rpc.call('anvil_setBalance', [_owned_signer(role).address.lower(), hex(1000*10**18)])
            run_id = plan['runId']+'-'+profile
            command('owner-deploy', [tools['bash']['path'], str(ledger/'tools/deploy_local.sh'), rpcs['pbc'].url, rpcs['dbc'].url,
                                     profile, plan['logDetailMode'], run_id], ledger_root, budget['deploy'], env)
            deployment_path = ledger/'exports/deployments'/run_id/'deployment.json'
            deployment_bytes = deployment_path.read_bytes(); deployment = strict_json(deployment_bytes)
            frozen_validate('LedgerDeployment', deployment)
            require(deployment['interfaceVersion'] == 'v1' and deployment['profile'] == profile and deployment['mutations'] == '0', 'owner deployment profile')
            (output/'deployment.json').write_bytes(deployment_bytes)
            chains = {}
            for name in ('pbc', 'dbc'):
                manifest = deployment['chains'][name]
                require(manifest['rpcUrl'] == rpcs[name].url and manifest['chainId'] == plan['chainIds'][name], 'owner deployment endpoint')
                contracts = {}
                for role, address in manifest['contracts'].items():
                    item = deployment['abi'][role]; path = ledger/item['abi']
                    require(sha256(path) == plan['owners']['ledger']['entries']['ledger/'+item['abi']], 'reviewed ABI regeneration')
                    contracts[role] = AbiContract(path, address, item['abiSha256'])
                    code = rpcs[name].call('eth_getCode', [address, 'latest'])
                    compiled = json.loads((ledger/'out'/(role+'.sol')/(role+'.json')).read_text())
                    check_runtime_bytecode(code, compiled['deployedBytecode'])
                chains[name] = PublicChain(rpcs[name], chain_id=manifest['chainId'], contracts=contracts, output=output/(name+'-native'))
            bootstrap_path = ledger/'exports'/('bootstrap-'+run_id+'.json')
            command('owner-bootstrap-producer', [tools['bash']['path'], str(ledger/'tools/bootstrap_fixture.sh'), rpcs['pbc'].url,
                                                 str(deployment_path), str(bootstrap_path)], ledger_root, budget['bootstrap'], env)
            raw = bootstrap_path.read_bytes(); (output/'bootstrap.json').write_bytes(raw)
            bootstrap = execute_bootstrap(chains['pbc'], raw, deployment_bytes=deployment_bytes)
            (output/'bootstrap-checked.json').write_text(json.dumps(bootstrap, indent=2)+'\n')
            state = output/'private-adapter-state'; state.mkdir(mode=0o700)
            def adapter_process(label, point=None):
                argv = [tools['python']['path'], '-m', 'hmbc_protocol.adapter'] if point is None else [tools['python']['path'], '-m', 'testtools.faulty_adapter', '--crash-at', point]
                argv += ['--state-dir', str(state), '--deployment', str(deployment_path)]
                child = stack.enter_context(JsonLinesProcess(argv, cwd=protocol, output=output/label,
                                                            timeout=budget['transport'], stop_grace=budget['stopGrace'], env=service_env))
                record.setdefault('adapterProcesses', []).append(dict(profile=profile, label=label, pid=child.pid))
                (output.parent/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
                return child
            process = adapter_process('adapter', recovery_point)
            sequence = 0
            def worker_snapshot():
                nonlocal sequence
                label = f'worker-export-{sequence:02}'; sequence += 1
                return command(label, [tools['python']['path'], '-m', 'hmbc_protocol.worker_log', '--state-dir', str(state)], protocol, budget['transport'],service_env)
            if recovery_point is not None:
                from evaluation.recovery_execution import RecoveryAdapter
                process = RecoveryAdapter(process, restart=lambda: adapter_process('adapter-restarted'),
                                          point=recovery_point, pbc=chains['pbc'], dbc=chains['dbc'], deployment=deployment,
                                          worker_snapshot=worker_snapshot, output=output/'recovery')
            record_fixture = dict(dataId='0x'+keccak(text='HMBC.data.P1.MHR').hex(), owner=next(a['root'] for a in deployment['fixture']['authorities'] if a['id']=='H2'),
                                  payloadDigest='0x'+keccak(text='HMBC.synthetic.P1.MHR.E1').hex())
            policy = dict(clauses=[[dict(role='0x'+keccak(text='HMBC.role.Doctor').hex(), kind='1', issuerMode='0'),
                                   dict(role='0x'+keccak(text='HMBC.role.OnDuty').hex(), kind='2', issuerMode='2')]])
            results = {}
            for label in ('alice', 'bob'):
                probe_options = {'duplicate_outcome': True} if duplicate_outcome and label == 'alice' else {}
                if nonce_replay and label == 'alice': probe_options = {'nonce_replay': True}
                results[label] = execute_access(chains['pbc'], chains['dbc'], process, deployment_bytes=deployment_bytes,
                                               user_label=label, user=bootstrap['users'][label], record=record_fixture, policy=policy,
                                               expected_allow=label=='alice', worker_snapshot=worker_snapshot, output=output/label,
                                               recovery_point=recovery_point, **probe_options)
                if label == 'alice' and expired_retry:
                    from evaluation.expired_retry import execute_expired_retry
                    grants = [e['grantId'] for e in results[label]['observed']['events'] if e['type'] == 'DBC_AUTHORIZED']
                    require(len(grants) == 1, 'one recovered grant for expiry probe')
                    execute_expired_retry(chains['pbc'], chains['dbc'], process, deployment=deployment,
                                          grant_id=grants[0], worker_snapshot=worker_snapshot, output=output/'expired-retry')
            require(bootstrap['wrongAdminCode'] == '16' and all(r['ok'] for r in results.values()), 'three E1 controls')
            if subject_substitution or relay_stress is not None:
                # SL1/SL2: controls above ran on deployment D1. The stress uses a fresh
                # second deployment D2 on the same chain pair, its own bootstrap,
                # adapter process and private state, so the stress oracle sees an
                # unused grant/count/nonce state. No clock move or crash hook.
                kind = 'subject' if subject_substitution else 'relay'
                stress = output/(kind+'-instance'); stress.mkdir()
                for name in ('pbc', 'dbc'):
                    for role in ('relay', 'H1-ca-admin', 'H2-ca-admin', 'H3-ca-admin', 'H4-ca-admin'):
                        rpcs[name].call('anvil_setBalance', [_owned_signer(role).address.lower(), hex(1000*10**18)])
                stress_run = run_id+'-'+kind
                command('owner-deploy-'+kind, [tools['bash']['path'], str(ledger/'tools/deploy_local.sh'), rpcs['pbc'].url, rpcs['dbc'].url,
                                                 profile, plan['logDetailMode'], stress_run], ledger_root, budget['deploy'], env)
                stress_path = ledger/'exports/deployments'/stress_run/'deployment.json'
                stress_bytes = stress_path.read_bytes(); stress_dep = strict_json(stress_bytes)
                frozen_validate('LedgerDeployment', stress_dep)
                require(stress_dep['interfaceVersion'] == 'v1' and stress_dep['profile'] == profile and stress_dep['mutations'] == '0',
                        'owner stress deployment profile')
                require(all(not set(stress_dep['chains'][n]['contracts'].values()) & set(deployment['chains'][n]['contracts'].values())
                            for n in ('pbc', 'dbc')), 'fresh distinct stress deployment')
                (stress/'deployment.json').write_bytes(stress_bytes)
                stress_chains = {}
                for name in ('pbc', 'dbc'):
                    manifest = stress_dep['chains'][name]
                    require(manifest['rpcUrl'] == rpcs[name].url and manifest['chainId'] == plan['chainIds'][name], 'owner stress deployment endpoint')
                    contracts = {}
                    for role, address in manifest['contracts'].items():
                        item = stress_dep['abi'][role]; path = ledger/item['abi']
                        require(sha256(path) == plan['owners']['ledger']['entries']['ledger/'+item['abi']], 'reviewed ABI regeneration')
                        contracts[role] = AbiContract(path, address, item['abiSha256'])
                        code = rpcs[name].call('eth_getCode', [address, 'latest'])
                        compiled = json.loads((ledger/'out'/(role+'.sol')/(role+'.json')).read_text())
                        check_runtime_bytecode(code, compiled['deployedBytecode'])
                    stress_chains[name] = PublicChain(rpcs[name], chain_id=manifest['chainId'], contracts=contracts, output=stress/(name+'-native'))
                stress_bootstrap_path = ledger/'exports'/('bootstrap-'+stress_run+'.json')
                command('owner-bootstrap-'+kind, [tools['bash']['path'], str(ledger/'tools/bootstrap_fixture.sh'), rpcs['pbc'].url,
                                                    str(stress_path), str(stress_bootstrap_path)], ledger_root, budget['bootstrap'], env)
                raw = stress_bootstrap_path.read_bytes(); (stress/'bootstrap.json').write_bytes(raw)
                stress_boot = execute_bootstrap(stress_chains['pbc'], raw, deployment_bytes=stress_bytes)
                (stress/'bootstrap-checked.json').write_text(json.dumps(stress_boot, indent=2)+'\n')
                require(stress_boot['wrongAdminCode'] == '16', 'stress bootstrap issuer restriction')
                stress_state = stress/'private-adapter-state'; stress_state.mkdir(mode=0o700)
                stress_process = stack.enter_context(JsonLinesProcess(
                    [tools['python']['path'], '-m', 'hmbc_protocol.adapter', '--state-dir', str(stress_state), '--deployment', str(stress_path)],
                    cwd=protocol, output=stress/'adapter', timeout=budget['transport'], stop_grace=budget['stopGrace'], env=service_env))
                record.setdefault('adapterProcesses', []).append(dict(profile=profile, label='adapter-'+kind, pid=stress_process.pid))
                (output.parent/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
                stress_sequence = 0
                def stress_worker_snapshot():
                    nonlocal stress_sequence
                    label = f'{kind}-worker-export-{stress_sequence:02}'; stress_sequence += 1
                    return command(label, [tools['python']['path'], '-m', 'hmbc_protocol.worker_log', '--state-dir', str(stress_state)],
                                   protocol, budget['transport'], service_env)
                def stress_worker_probe():
                    # SL2 performs no worker operation; a never-created worker database is
                    # an explicit, verified observation (observe_worker_export), not a failure.
                    nonlocal stress_sequence
                    label = f'{kind}-worker-export-{stress_sequence:02}'; stress_sequence += 1
                    row = record_command([tools['python']['path'], '-m', 'hmbc_protocol.worker_log', '--state-dir', str(stress_state)],
                                         protocol, output/(label+'.txt'), timeout=budget['transport'], env=service_env,
                                         owned_process_group=True, stop_grace=budget['stopGrace'])
                    observation = observe_worker_export(row['exitCode'], (output/(label+'.txt')).read_bytes(), stress_state)
                    row['workerObservation'] = 'instantiated' if observation['instantiated'] else 'never-instantiated (verified)'
                    commands.append(row); (output/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
                    return observation
                stress_record = dict(record_fixture, owner=next(a['root'] for a in stress_dep['fixture']['authorities'] if a['id'] == 'H2'))
                if subject_substitution:
                    stress_result = execute_access(stress_chains['pbc'], stress_chains['dbc'], stress_process, deployment_bytes=stress_bytes,
                                                   user_label='alice', user=stress_boot['users']['alice'], record=stress_record, policy=policy,
                                                   expected_allow=True, worker_snapshot=stress_worker_snapshot, output=output/'subject-stress',
                                                   subject_substitution=stress_boot['users']['bob']['gid'],
                                                   subject_completion=profile != 'repaired-e')
                    require(stress_result['ok'] is True, 'subject stress result')
                    record['profiles'][profile]['subjectStress'] = dict(runId=stress_run, deployment=str(Path(profile)/'subject-instance/deployment.json'),
                                                                        result=str(Path(profile)/'subject-stress/result.json'))
                else:
                    from evaluation.relay_stress import execute_relay_stress
                    stress_result = execute_relay_stress(stress_chains['pbc'], stress_chains['dbc'], stress_process, deployment_bytes=stress_bytes,
                                                         user_label='alice', user=stress_boot['users']['alice'], record=stress_record,
                                                         policy=policy, variant=relay_stress, worker_snapshot=stress_worker_probe,
                                                         output=output/'relay-stress')
                    require(stress_result['ok'] is True and stress_result['variant'] == relay_stress, 'relay stress result')
                    record['profiles'][profile]['relayStress'] = dict(runId=stress_run, variant=relay_stress,
                                                                      deployment=str(Path(profile)/'relay-instance/deployment.json'),
                                                                      result=str(Path(profile)/'relay-stress/result.json'))
            record['profiles'][profile].update(status='CONTROL_PASS', results={k: str(Path(profile)/k/'result.json') for k in results},
                                              wrongAdmin='UNAUTHORIZED_CALLER; baseline issuer restriction, not a repair')
    finally:
        stable = _snapshot_stable(plan['owners']['ledger'], ledger_root) and _snapshot_stable(plan['owners']['protocol'], protocol_root)
        record['profiles'][profile]['sourcesStable'] = stable
        cast_stable = True
        for rpc in rpcs.values():
            try: rpc.checkpoint('run-end')
            except ValueError: cast_stable = False
        record['profiles'][profile]['castHashPolicy'] = hash_policy
        record['profiles'][profile]['castStable'] = cast_stable
        record['profiles'][profile]['servicesStopped'] = all(s.returncode is not None for s in services)
        (output.parent/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
        require(stable, 'peer snapshot source stability')
        require(cast_stable, 'Cast checkpoint stability')


def execute(plan_path, ack_path, output, *, profiles=None):
    output = Path(output); output.mkdir(parents=True, exist_ok=False, mode=0o700)
    record = dict(rq='E', executionMode='two-chain-e1', adapterMode='symbolic', status='BLOCKED', startedAt=now(), endedAt=None,
                  servicesStarted=[], profiles={}, acks=None, failure=None, sourceStable=None,
                  limitation='E1 controls only; E2/E3 and every RQ gate remain unproved.')
    authorized = False
    try:
        raw = Path(plan_path).read_bytes(); plan = json.loads(raw)
        record['planSha256'] = hashlib.sha256(raw).hexdigest(); verify_plan(plan)
        if plan.get('reviewMode') == SOLO:
            record.update(reviewMode=SOLO, reviewDisclosure=SOLO_DISCLOSURE)
        record['acks'] = _acks(ack_path, plan, record['planSha256'])
        selected = plan['profiles'] if profiles is None else profiles
        require(selected and all(p in plan['profiles'] for p in selected) and len(selected) == len(set(selected)), 'E1 selected profiles')
        authorized = True
        record['status'] = 'RUNNING'
        (output/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
        for profile in selected:
            verify_plan(plan)
            _profile(plan, profile, output/profile, record)
        verify_plan(plan); record['sourceStable'] = True
        record['status'] = 'E1_CONTROL_PASS'
    except BaseException as error:
        record['failure'] = dict(type=type(error).__name__, message=str(error))
        record['status'] = 'FAILED' if authorized else 'BLOCKED'
        if authorized:
            record['sourceStable'] = _runtime_sources() == plan['agent3Sources']
        if not isinstance(error, Exception): raise
    finally:
        record['endedAt'] = now()
        (output/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True); p.add_argument('--acks', type=Path); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); result = execute(args.plan, args.acks, args.output)
    print(json.dumps({k: result[k] for k in ('status', 'failure', 'sourceStable', 'servicesStarted')}, indent=2))
    return 0 if result['status'] == 'E1_CONTROL_PASS' else 2


if __name__ == '__main__': raise SystemExit(main())
