"""One-command gate E run from fresh state (A1-0082 P4-1; S3-0002 section 3.1 without stages 4 and 5).

Paper-derived HMBC2020 reconstruction, synthetic fixtures, symbolic adapter. Solo phase: every review and
ACK is correlated self-review by the same model (A1-0059).

Stages: verify-freeze and versions; source bracket (pre); all 56 catalog rows, one fresh chain pair per
row, each through `evaluation.e2.run_row` (the P2 slice runners and their frozen row checks, selected by
the existing `e2.create_plan` slice flags); ProVerif re-run compared byte for byte with A3-0033 and
p3-proverif-20261012; source bracket (post); manifest.json; gate-evidence.json. The mutant and
revocation-window stages are dropped by the human decisions A1-0080 and A1-0081.

Aggregation only: this module adds no oracle. The manifest status says whether the run stages passed. It
is not a gate E decision: that is the GATES.md checklist plus three same-source ACKs (A1-0082 P4-3/P4-4),
and `evaluation.gate` stays fail-closed.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import time

from evaluation import e1, e2, host_toolchain
from evaluation.access_artifacts import require
from evaluation.bootstrap import FREEZE_SHA256
from evaluation.gate import E_CRITERIA
from evaluation.manifests import canonical_hash, now, record_command, sha256

ROOT = e1.ROOT
FREEZE = ROOT/'interfaces/v1/FREEZE.json'
CATALOGS = ('evaluation/scenarios/e0_cases.json', 'evaluation/scenarios/e0_supplement_cases.json')
STAGES = ('verify-freeze-and-versions', 'source-bracket-pre', 'catalog-56', 'proverif', 'source-bracket-post', 'manifest', 'gate-evidence')
DROPPED_STAGES = {
    'mutants': ('S3-0002 stage 4 dropped by the human decision A1-0080 (after the A1-0079 safety-classifier stop): criterion 4 rests '
                'on owner, formal and baseline evidence; the integrated live mutant matrix is not run and is never resumed'),
    'window': ('S3-0002 stage 5 dropped by the human decision A1-0081: no revocation window is measured by this run; the report '
               'cites the owner measurement A1-0046 and the SL6 ordering result'),
}
E2 = 'evaluation/evidence/e2/'
SLICES = (
    dict(name='recovery-expiry', flag='expired_retry', proofs=('recovery/result.json', 'expired-retry/result.json'),
         history=dict(evidence=E2+'expiry-live-20261009/', message='A3-0038',
                      note='recovery only: '+E2+'recovery-live-20261009/ (A3-0036)')),
    dict(name='duplicate-outcome', flag='duplicate_outcome', proofs=('alice/duplicate-outcome/result.json',),
         history=dict(evidence=E2+'duplicate-live-20261009/', message='A3-0040', note='')),
    dict(name='nonce-replay', flag='nonce_replay', proofs=('alice/nonce-replay/result.json',),
         history=dict(evidence=E2+'grouped-replay-live-20261009/', message='A3-0045',
                      note='earlier trial '+E2+'nonce-replay-live-20261009/ failed (repaired release EXPIRED) and is kept')),
    dict(name='sl1-subject', flag='subject_substitution', proofs=('subject-stress/subject-substitution/result.json',),
         history=dict(evidence=E2+'sl1-subject-live-20261010/', message='S3-0006', note='')),
    dict(name='sl2-relay', flag='relay_stress', proofs=('relay-stress/result.json',),
         history=dict(evidence=E2+'sl2-relay-live-20261010/', message='S3-0010',
                      note='first run '+E2+'sl2-relay-failed-20261010/ (S3-0008) failed on a runner defect and is kept')),
    dict(name='sl3-audit', flag='audit_stress', proofs=('audit-stress/result.json',),
         history=dict(evidence=E2+'sl3-audit-live-20261010/', message='S3-0012', note='')),
    dict(name='sl4-receipt', flag='receipt_stress', proofs=('receipt-stress/result.json',),
         history=dict(evidence=E2+'sl4-receipt-live-20261010/', message='S3-0014', note='')),
    dict(name='sl5-trust', flag='trust_stress', proofs=('trust-stress/result.json',),
         history=dict(evidence=E2+'sl5-trust-live-20261010/', message='S3-0016', note='')),
    dict(name='sl6-barrier', flag='barrier_stress', proofs=('barrier-stress/result.json',),
         history=dict(evidence=E2+'sl6-barrier-live-20261011/', message='S3-0018', note='')),
    dict(name='sl7-destination', flag='destination_stress', proofs=('destination-stress/result.json',),
         history=dict(evidence=E2+'sl7-destination-live-20261011/', message='S3-0020', note='')),
)
SUBJECT_COMPLETION = 'subject-stress/subject-completion/result.json'
D47_ROWS = ('E03-crash-after-intent-paper-strict', 'E03-crash-after-intent-paper-minimal',
            'E03-crash-after-send-paper-strict', 'E03-crash-after-send-paper-minimal')
D47_LABEL = 'frozen BLOCKED / decided SPEC_GAP, UNPROVED (D47)'
_RECEIPT_GUARD = dict(slice='sl4-receipt', error='WRONG_SUBJECT', mutant='no-receipt-binding (32)',
                      guard='receipt field binding, checked before the quorum (PSC.sol:240-283 at 933d2a7)')
GUARD_ROWS = {
    'E01-same-nonce-distinct-digests-repaired-e': dict(slice='sl2-relay', error='REPLAY', mutant='no-nonce (8)',
                                                       guard='nonce guard KSSC.sol:182 (lines 181-183)'),
    'E03-receipt-binding-control-requestDigest-repaired-e': dict(_RECEIPT_GUARD),
    'E03-receipt-binding-control-gid-repaired-e': dict(_RECEIPT_GUARD),
    'E03-receipt-binding-control-dataId-repaired-e': dict(_RECEIPT_GUARD),
    'E02-signed-list-rollback-repaired-e': dict(slice='sl5-trust', error='STALE_ANCHOR', mutant='no-version-monotone (16)',
                                                guard='TMSC.sol:190'),
    'E02-post-barrier-revocation-repaired-e': dict(slice='sl6-barrier', error='STALE_STATE', mutant='no-state-barrier (2)',
                                                   guard='DecisionVerifier step 10, line 87, sequence cause'),
    'E02-expired-duty-repaired-e': dict(slice='sl6-barrier', error='EXPIRED', mutant='no-record-freshness (4)',
                                        guard='DecisionVerifier step 13 (record validity)'),
    'E01-wrong-destination-repaired-e': dict(slice='sl7-destination', error='WRONG_DESTINATION',
                                             mutant=('no-destination-binding (1): this row cannot kill it, step 1 fires first (A1-0039 '
                                                     'G-3); that mutant is detected only by the forge tests and the ProVerif mutant'),
                                             guard='DecisionVerifier step 1, line 60'),
}
PROVERIF_MODELS = (
    ('evaluation/models/e/access.pv', ('true', 'true', 'true', 'false', 'true'),
     E2+'formal-and-hook-review-20261009/positive-final.stdout', E2+'p3-proverif-20261012/access.stdout'),
    ('evaluation/models/e/access_mutant.pv', ('false', 'false', 'true', 'false', 'true'),
     E2+'formal-and-hook-review-20261009/mutant-final.stdout', E2+'p3-proverif-20261012/access_mutant.stdout'),
)
MUTANT_RERUN = ('ledger/evidence/p3-mutant-suite-rerun/command.txt', 'ledger/evidence/p3-mutant-suite-rerun/mutants.json',
                'ledger/evidence/p3-mutant-suite-rerun/mutants.txt')
P3_PROVERIF = tuple(E2+'p3-proverif-20261012/'+name for name in (
    'README.md', 'summary.json', 'access.stdout', 'access.stderr', 'access.run.json',
    'access_mutant.stdout', 'access_mutant.stderr', 'access_mutant.run.json'))
A1_0080 = 'communication/agent-1/outbox/0080-decision-human-mutant-evidence-scope.md'
CRITERION4_INPUTS = MUTANT_RERUN+P3_PROVERIF+(A1_0080,)
GATE_INPUTS = (('evaluation/models/e/access.pv', 'evaluation/models/e/access_mutant.pv', 'evaluation/models/e/README.md',
                E2+'formal-and-hook-review-20261009/positive-final.stdout', E2+'formal-and-hook-review-20261009/mutant-final.stdout')
               + P3_PROVERIF + MUTANT_RERUN
               + ('ledger/evidence/ae2-mutants.json', 'ledger/evidence/ae2-mutants.txt', A1_0080,
                  'communication/agent-1/outbox/0081-decision-human-window-evidence-p3-closed.md',
                  'communication/agent-1/outbox/0082-decision-p4-gate-run-report-acks.md',
                  'communication/E0_MAPPING_ACKS.json', 'communication/E0_ACCEPTANCE.md',
                  'evaluation/evidence/e1/integrated-controls-20261008/README.md'))
CRITERION4_NOTE = ('met on owner, formal and baseline evidence (human decision A1-0080); integrated live mutant matrix not run '
                   '(safety-classifier stop, A1-0079). The forge mutant suite covers the ledger contracts only, not the adapter, '
                   'relay or two-chain runner; the guard rows show that the integrated runner reaches each guard, not a mutant '
                   'accepting; no live accept-versus-reject kill of no-destination-binding is claimed.')
CRITERIA_RULES = {
    'interface-and-source-review': dict(
        rule=('VERIFIED iff verify-freeze is UNCHANGED: FREEZE.json equals the frozen hash and all 15 frozen copies hash as recorded; '
              'moved owner inventories are checked against their frozen Git blobs. The source map and paper-gap review is the '
              'closed E0 record (E0_MAPPING_ACKS.json, E0_ACCEPTANCE.md); this run re-checks the frozen bytes only.'),
        evidence=['run:verify-freeze.json', 'repo:interfaces/v1/FREEZE.json', 'repo:communication/E0_MAPPING_ACKS.json',
                  'repo:communication/E0_ACCEPTANCE.md'], pendingAfterRun=False),
    'legitimate-and-denied-controls': dict(
        rule=('VERIFIED iff all 56 rows PASS: every row first runs the three controls on D1 (wrong-admin UNAUTHORIZED_CALLER(16) '
              'before H2, registered Alice allow with release and one outcome, registered Bob POLICY_DENIED(9)) and e1._profile '
              'refuses the row otherwise.'),
        evidence=['run:catalog-coverage-56.json', 'run:catalog/', 'repo:evaluation/evidence/e1/integrated-controls-20261008/'],
        pendingAfterRun=False),
    'E01-E02-E03-classification': dict(
        rule=('VERIFIED iff all 56 rows PASS their frozen e2 row check and catalog-coverage-56.json lists every catalog case with its '
              'frozen expectation, observed proof fields and reported classification. The 4 paper crash rows carry the D47 label '
              'and are never findings.'),
        evidence=['run:catalog-coverage-56.json'], pendingAfterRun=False),
    'repairs-and-mutants': dict(
        rule=('VERIFIED (human-scoped, A1-0080) iff every guard row PASS with its expected error, all 56 rows PASS (positive '
              'controls in every row, so the repaired profile is not deny-all), the ProVerif stage matched (destination-mutant '
              'counterexamples, other fields agree) and the owner mutant evidence still hashes as in the plan.'),
        evidence=['repo:ledger/evidence/p3-mutant-suite-rerun/', 'repo:evaluation/evidence/e2/p3-proverif-20261012/',
                  'run:<the guard rows of this run>', 'repo:'+A1_0080],
        note=CRITERION4_NOTE, pendingAfterRun=False),
    'real-two-chain-and-recovery': dict(
        rule=('VERIFIED iff all 56 rows PASS, each on a fresh two-Anvil chain pair with owner deployments and the production '
              'adapter (adapterMode symbolic recorded), including the 6 crash/recovery rows with their expired cached retry.'),
        evidence=['run:catalog/recovery-expiry/', 'run:manifest.json'], pendingAfterRun=False),
    'proverif-and-negative-control': dict(
        rule=('VERIFIED iff both models exit 0 with empty stderr, their RESULT verdicts equal the expectation, and stdout is '
              'byte-identical to A3-0033 and to p3-proverif-20261012 (declared local ProVerif 2.05 build).'),
        evidence=['run:proverif/summary.json', 'repo:'+E2+'formal-and-hook-review-20261009/', 'repo:'+E2+'p3-proverif-20261012/'],
        pendingAfterRun=False),
    'RQ1-report': dict(
        rule=('PENDING after the run: evaluation/reports/RQ1-E.md is published after the run (A1-0082 P4-2) and adjudicated with '
              'the three same-source ACKs (P4-3).'),
        evidence=['repo:evaluation/reports/RQ1-E.md'], pendingAfterRun=True),
    'stable-hashed-input-output-tools': dict(
        rule=('VERIFIED iff the source bracket is equal before and after and equal to the plan (agent3Sources, gateInputs and the '
              'broad evaluation/interfaces bracket), HEAD and git status are unchanged, every tool hash matches, the gate plan '
              're-verifies at the end, and resultFiles hash every result.'),
        evidence=['run:bracket-pre.json', 'run:bracket-post.json', 'run:versions.json', 'run:verify-freeze.json', 'run:manifest.json'],
        pendingAfterRun=False),
    'three-matching-acks': dict(
        rule=('PENDING after the run: three same-source ACKs (agent 1, agent 2 (proxy), agent 3 (proxy)) naming one manifest, '
              'gate-evidence and RQ1-E.md hash and HEAD, each with the correlated-review disclosure (A1-0082 P4-3).'),
        evidence=['repo:communication/GATES.md'], pendingAfterRun=True),
}
GATE_DECISION = ('run stages only; not gate E PASS. Gate E is adjudicated by the GATES.md checklist and three same-source ACKs '
                 '(A1-0082 P4-3/P4-4); evaluation.gate stays fail-closed.')
VERSION_ARGS = (('forge', ('--version',)), ('anvil', ('--version',)), ('cast', ('--version',)), ('solc', ('--version',)),
                ('python', ('--version',)), ('python3', ('--version',)), ('bash', ('--version',)), ('proverif', ('-help',)))


def _catalog():
    return {c['id']: c for path in CATALOGS for c in json.loads((ROOT/path).read_text())['cases']}


def _case_ids(sub):
    if 'caseIds' in sub:
        return list(sub['caseIds'])
    return ['E03-crash-'+item['point'].replace('_', '-')+'-'+item['profile'] for item in sub['matrix']]


def create_plan(*, run_id, freeze_message, review_mode=e1.SOLO):
    """The gate plan: ten embedded slice plans (one per existing e2 flag), the ProVerif stage and the gate inputs."""
    require(review_mode == e1.SOLO, 'the gate run is a solo-phase plan (A1-0082)')
    require(isinstance(freeze_message, str) and re.fullmatch(r'S3-[0-9]{4}', freeze_message) is not None, 'gate freeze message ID')
    require(isinstance(run_id, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,40}', run_id) is not None, 'gate run ID')
    slices = []
    for spec in SLICES:
        sub = e2.create_plan(run_id=run_id+'-'+spec['name'], freeze_message=freeze_message, review_mode=review_mode, **{spec['flag']: True})
        slices.append(dict(name=spec['name'], flag=spec['flag'], runId=sub['runId'], caseIds=_case_ids(sub),
                           proofFiles=list(spec['proofs']), history=dict(spec['history']), plan=sub))
    first = slices[0]['plan']
    require(all(s['plan'][k] == first[k] for s in slices for k in ('tools', 'owners', 'agent3Sources', 'pythonVersion', 'serviceEnvironment',
                                                                  'ports', 'chainIds', 'packagePins')),
            'one toolchain, owner pin set, source set and port pair for every slice')
    ids = [i for s in slices for i in s['caseIds']]
    require(len(ids) == 56 == len(set(ids)) and set(ids) == set(_catalog()), 'the 56 frozen catalog cases, each exactly once')
    pv = host_toolchain.resolve('proverif')
    models = [dict(model=model, sha256=sha256(ROOT/model), expectedVerdicts=list(verdicts),
                   references={'A3-0033': dict(path=a3, sha256=sha256(ROOT/a3)), 'p3-proverif-20261012': dict(path=p3, sha256=sha256(ROOT/p3))})
              for model, verdicts, a3, p3 in PROVERIF_MODELS]
    return dict(
        schemaVersion='hmbc-e-gate-plan/v1', rq='E', runId=run_id, freezeMessage=freeze_message, interfaceVersion='v1',
        interfaceFreezeSha256=FREEZE_SHA256, executionMode='real-integrated', adapterMode='symbolic',
        reviewMode=e1.SOLO, reviewDirective='A1-0059', reviewDecision='A1-0082', reviewDisclosure=e1.SOLO_DISCLOSURE,
        design='S3-0002 section 3.1 with stages 4 (mutants) and 5 (window) dropped (A1-0080, A1-0081, A1-0082)',
        stages=list(STAGES), droppedStages=dict(DROPPED_STAGES),
        aggregation=('every row runs through evaluation.e2.run_row with its embedded slice plan (the same P2 slice runner, '
                     'e1._profile, and the same frozen row check); no new oracle; slice output layouts unchanged '
                     '(catalog/<slice>/<case>/<profile>/...)'),
        order=('slices in the historical order recovery-expiry, duplicate-outcome, nonce-replay, SL1..SL7; rows in slice-plan matrix '
               'order; every row on a fresh Anvil pair (PBC 18545, DBC 18546; chain ids 18545/28545): the three controls first on D1, '
               'then the stress on a fresh D2 (and B for wrong destination); only the DBC clock moves, and only in the rows that '
               'pin or advance it'),
        failurePolicy=('each row runs exactly once; an exception or a failed frozen row check marks the row FAILED with its type and '
                       'message, keeps its output and the run continues with the next row on a fresh chain pair; rows never reached '
                       'stay NOT_RUN; no retry; any FAILED or NOT_RUN row, a ProVerif mismatch, a changed input or worktree makes the '
                       'run FAILED; re-running a failed row needs a new FREEZE (A1-0082)'),
        outputPolicy=('raw output only under --output, which must lie outside the repository working tree; nothing is written in the '
                      'repository during the run; publication is a separate selection with a never-publish key scan after the run, '
                      'as in the slices; TEST-ONLY keys and raw release tokens are never published'),
        hostMemory=('MemTotal, MemFree, MemAvailable, SwapTotal and SwapFree from /proc/meminfo before and after the run, and '
                    'MemAvailable at each row start; never two live runs or full suites at once'),
        catalog=dict(files={path: sha256(ROOT/path) for path in CATALOGS}, rows=56, paperCrashRows=list(D47_ROWS), paperCrashLabel=D47_LABEL),
        slices=slices, guardRows=copy.deepcopy(GUARD_ROWS),
        proverif=dict(tool=dict(path=pv['path'], sha256=pv['sha256'], frozenSha256=pv['frozenSha256'], resolution=pv['resolution'],
                                declaredLocalBuild=copy.deepcopy(pv.get('declaredLocalBuild'))),
                      environment=dict(first['serviceEnvironment']), timeoutSeconds=60, cwd='repository root', models=models),
        gateInputs={path: sha256(ROOT/path) for path in GATE_INPUTS},
        criteriaRules=copy.deepcopy(CRITERIA_RULES),
        wallTimeEstimate=dict(
            expected='about 1.5 h; allow up to 2.5 h under host load (S3-0002 estimated 2-2.5 h without mutants and window)',
            basis=('sum of the actual slice wall times, 5252 s: SL1 255.73, SL2 544.93, SL3 459.88, SL4 601.60, SL5 531.40, '
                   'SL6 736.64, SL7 602.24 s on this host; pre-solo recovery+expiry 780, duplicate 365, grouped replay 375 s on '
                   'agent 3 host; plus plan verification, ProVerif and brackets (about 1-2 min)')),
        limitations=[
            'Solo-phase plan: the committed S3 FREEZE and both exact solo ACKs (A1 and S2) precede services; all are correlated self-review (A1-0059).',
            'Mutant stage dropped (A1-0080): criterion 4 rests on owner, formal and baseline evidence; integrated live mutant matrix not run.',
            'Window stage dropped (A1-0081): no window is measured by this run; the report cites A1-0046 and SL6.',
            'The manifest status reports the run stages only; gate E is adjudicated by GATES.md and three same-source ACKs; evaluation.gate stays fail-closed.',
            'Paper crash rows: frozen BLOCKED / decided SPEC_GAP, UNPROVED (D47); never a finding.',
            'Repaired TTL margins are about 2 s (SL7 expiry boundary) and about 7 s (SL6 expired duty) under host load; a failed row is kept.',
            'One trial per row on one host; Anvil without consensus or finality; symbolic adapter; safe-ledger, trusted-worker and one trusted witness; no statistics.',
            'Tested reconstruction results, never an HMBC exploit or an authors-implementation claim; relay-stress rows are outside A01.'])


def verify_plan(plan):
    require(plan == create_plan(run_id=plan['runId'], freeze_message=plan['freezeMessage'], review_mode=plan.get('reviewMode', 'strict')),
            'exact current gate plan/source/config')
    for item in plan['slices']:
        e2.verify_plan(item['plan'])


def verify_freeze(freeze=None):
    """Stage 1: FREEZE.json and its 15 frozen copies; a moved owner inventory is checked against its frozen Git blob."""
    freeze_ok = sha256(FREEZE) == FREEZE_SHA256
    freeze = json.loads(FREEZE.read_text()) if freeze is None else freeze
    copies = []
    for path, row in sorted(freeze['frozenCopies'].items()):
        copy_ok = (ROOT/path).is_file() and sha256(ROOT/path) == row['sha256']
        if 'commit' in row:
            blob = hashlib.sha256(e1._git_blob(row['commit'], row['sourcePath'])).hexdigest()
            current = (ROOT/row['sourcePath']).is_file() and sha256(ROOT/row['sourcePath']) == row['sha256']
            source = dict(path=row['sourcePath'], commit=row['commit'], frozenGitBlob=True, ok=blob == row['sha256'], movedSinceFreeze=not current)
        else:
            source = dict(path=row['sourcePath'], frozenGitBlob=False,
                          ok=(ROOT/row['sourcePath']).is_file() and sha256(ROOT/row['sourcePath']) == row['sha256'])
        copies.append(dict(path=path, sha256=row['sha256'], mapping=row.get('mapping'), copyOk=copy_ok, source=source,
                           ok=copy_ok and source['ok']))
    unchanged = freeze_ok and len(copies) == 15 and all(c['ok'] for c in copies)
    return dict(status='UNCHANGED' if unchanged else 'CHANGED', freeze='interfaces/v1/FREEZE.json', freezeSha256=FREEZE_SHA256,
                freezeSha256Ok=freeze_ok, copies=copies, checkedAt=now())


def _memory():
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, _, rest = line.partition(':')
        if key in ('MemTotal', 'MemFree', 'MemAvailable', 'SwapTotal', 'SwapFree'):
            values[key] = int(rest.split()[0])
    return dict(values, unit='kB', at=now())


def _git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, timeout=60, check=True).stdout


def _worktree():
    return dict(head=_git('rev-parse', 'HEAD').strip(), status=_git('status', '--porcelain=v1', '--untracked-files=all').splitlines(),
                at=now())


def _bracket():
    broad = {}
    for base in ('evaluation', 'interfaces/v1'):
        for path in sorted((ROOT/base).rglob('*')):
            rel = path.relative_to(ROOT)
            if path.is_file() and '__pycache__' not in rel.parts and rel.parts[:2] != ('evaluation', 'runs'):
                broad[str(rel)] = sha256(path)
    for name in ('pyproject.toml', 'uv.lock', 'AGENTS.md', 'SPEC.md', 'PLAN.md'):
        broad[name] = sha256(ROOT/name)
    return dict(agent3Sources=e2._sources(), gateInputs={path: sha256(ROOT/path) for path in GATE_INPUTS}, broad=broad)


def _bracket_record(value, label):
    return dict(label=label, takenAt=now(), counts={k: len(v) for k, v in value.items()},
                aggregates={k: canonical_hash(v) for k, v in value.items()}, **value)


def _versions(plan, output):
    tools = dict(plan['slices'][0]['plan']['tools']); tools['proverif'] = plan['proverif']['tool']
    rows = {}
    for name, args in VERSION_ARGS:
        tool = tools[name]; log = Path(output)/'versions'/(name+'.txt')
        require(Path(tool['path']).is_file() and sha256(tool['path']) == tool['sha256'],
                'version command binary hash: '+name)
        row = record_command([tool['path'], *args], ROOT, log, timeout=30, env=plan['proverif']['environment'])
        lines = log.read_text(errors='replace').strip().splitlines()
        rows[name] = dict(path=tool['path'], sha256=tool['sha256'], hashOk=Path(tool['path']).is_file() and sha256(tool['path']) == tool['sha256'],
                          argv=row['argv'], exitCode=row['exitCode'], firstLine=lines[0] if lines else '', outputSha256=row['outputSha256'])
    sub = plan['slices'][0]['plan']
    return dict(recordedAt=now(), tools=rows, pythonVersion=platform.python_version(), plannedPythonVersion=sub['pythonVersion'],
                hostDifferences=sub.get('hostDifferences'), packagePins=sub['packagePins'], hostToolOverride=sub.get('hostToolOverride'),
                ok=all(r['hashOk'] and r['exitCode'] == 0 for r in rows.values())
                   and platform.python_version() == sub['pythonVersion'])


def run_proverif(plan, output):
    """Stage 6: both models with the pinned build; verdicts and stdout bytes compared with A3-0033 and p3-proverif-20261012."""
    pv = plan['proverif']; folder = Path(output)/'proverif'; folder.mkdir(parents=True, exist_ok=True)
    tool = pv['tool']; tool_ok = Path(tool['path']).is_file() and sha256(tool['path']) == tool['sha256']
    require(tool_ok, 'ProVerif binary hash before execution')
    runs = {}
    for model in pv['models']:
        require(Path(tool['path']).is_file() and sha256(tool['path']) == tool['sha256'],
                'ProVerif binary hash before execution')
        require((ROOT/model['model']).is_file() and sha256(ROOT/model['model']) == model['sha256'],
                'ProVerif model hash before execution')
        name = Path(model['model']).stem; argv = [tool['path'], model['model']]
        started = now(); began = time.monotonic(); timed_out = False
        try:
            done = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=pv['timeoutSeconds'], env=pv['environment'])
            code, out, err = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired as error:
            timed_out, code, out, err = True, None, error.stdout or b'', error.stderr or b''
        wall = time.monotonic()-began
        (folder/(name+'.stdout')).write_bytes(out); (folder/(name+'.stderr')).write_bytes(err)
        text = out.decode('utf-8', 'replace'); digest = hashlib.sha256(out).hexdigest()
        verdicts = re.findall(r'^RESULT .+ is (true|false)\.$', text, re.MULTILINE)
        references = {}
        for label, ref in model['references'].items():
            unchanged = (ROOT/ref['path']).is_file() and sha256(ROOT/ref['path']) == ref['sha256']
            references[label] = dict(path=ref['path'], sha256=ref['sha256'], referenceUnchanged=unchanged,
                                     fullOutputIdentical=unchanged and digest == ref['sha256'])
        model_ok = sha256(ROOT/model['model']) == model['sha256']
        tool_ok = tool_ok and Path(tool['path']).is_file() and sha256(tool['path']) == tool['sha256']
        matched = (tool_ok and model_ok and not timed_out and code == 0 and not err and 'cannot be proved' not in text
                   and verdicts == model['expectedVerdicts'] and all(r['fullOutputIdentical'] for r in references.values()))
        runs[name] = dict(model=model['model'], modelSha256=model['sha256'], modelUnchanged=model_ok, argv=argv, cwd=str(ROOT),
                          startedAt=started, exitCode=code, timedOut=timed_out, wallSeconds=round(wall, 6), stdoutSha256=digest,
                          stderrBytes=len(err), results=re.findall(r'^RESULT .+$', text, re.MULTILINE), verdicts=verdicts,
                          expectedVerdicts=list(model['expectedVerdicts']), references=references, matched=matched)
    summary = dict(tool=dict(tool, hashOk=tool_ok), environment=pv['environment'], runs=runs,
                   matched=len(runs) == len(pv['models']) and all(r['matched'] for r in runs.values()),
                   scope='symbolic abstraction of the access flow; not the deployed ledger and not a computational proof')
    (folder/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


def _run_catalog(plan, output, manifest, write):
    """Stage 3: every row once through e2.run_row; failures kept, the run continues on the next fresh chain pair."""
    rows = {(r['slice'], r['case']): r for r in manifest['rows']}
    catalog = output/'catalog'; catalog.mkdir()
    for spec in plan['slices']:
        sub = spec['plan']; folder = catalog/spec['name']; folder.mkdir()
        mode, limitation = e2.slice_mode(sub)
        record = dict(rq='E', executionMode=mode, adapterMode='symbolic', status='RUNNING', startedAt=now(), endedAt=None, cases={},
                      servicesStarted=[], acks=manifest['acks'], failure=None, sourceStable=None, limitation=limitation,
                      gateRun=dict(runId=plan['runId'], freezeMessage=plan['freezeMessage'], planSha256=manifest['planSha256'],
                                   slice=spec['name'], caseIds=spec['caseIds']),
                      slicePlanCanonicalSha256=canonical_hash(sub), reviewMode=sub['reviewMode'], reviewDisclosure=sub['reviewDisclosure'])
        manifest['slices'][spec['name']] = dict(status='RUNNING', manifest='catalog/'+spec['name']+'/manifest.json')
        case_records = {}; failed = []
        for item in sub['matrix']:
            row = rows[(spec['name'], e2.case_name(sub, item))]
            row.update(status='RUNNING', startedAt=now(), memAvailableKiBAtStart=_memory()['MemAvailable']); write()
            began = time.monotonic()
            try:
                e2.run_row(sub, item, folder, record, case_records)
                case = record['cases'][row['case']]
                row.update(status='PASS', caseStatus=case['status'])
                if 'expiredRetry' in case:
                    row['expiredRetry'] = case['expiredRetry']
            except BaseException as error:
                failure = dict(type=type(error).__name__, message=str(error))
                row.update(status='FAILED', failure=failure); failed.append(row['case'])
                if row['case'] in record['cases']:
                    record['cases'][row['case']].update(status='FAILED', failure=failure)
                if not isinstance(error, Exception):
                    raise
            finally:
                row.update(endedAt=now(), elapsedSeconds=round(time.monotonic()-began, 3))
                profile = case_records.get(row['case'], {}).get('profiles', {}).get(row['profile'], {})
                row.update(servicesStopped=profile.get('servicesStopped'), sourcesStable=profile.get('sourcesStable'),
                           castStable=profile.get('castStable'))
                record['servicesStarted'] = [dict(case=c, **e) for c, child in case_records.items() for e in child['servicesStarted']]
                (folder/'manifest.json').write_text(json.dumps(record, indent=2)+'\n'); write()
        if failed:
            record.update(status='FAILED', failure=dict(failedCases=failed), sourceStable=e2._sources() == sub['agent3Sources'])
        else:
            try:
                e2.verify_plan(sub); record.update(status=e2.slice_status(sub), sourceStable=True)
            except Exception as error:
                record.update(status='FAILED', failure=dict(type=type(error).__name__, message=str(error)), sourceStable=False)
        record['endedAt'] = now()
        (folder/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
        manifest['slices'][spec['name']]['status'] = record['status']
        manifest['servicesStarted'] += [dict(slice=spec['name'], **e) for e in record['servicesStarted']]
        manifest['adapterProcesses'] += [dict(slice=spec['name'], case=c, **e) for c, child in case_records.items()
                                         for e in child.get('adapterProcesses', [])]
        write()


def _coverage(plan, output, manifest):
    """Aggregate the 56 rows: frozen expectation, row status and the proof fields the row check already accepted."""
    catalog = _catalog(); specs = {s['name']: s for s in plan['slices']}; rows = []
    for row in manifest['rows']:
        case, spec = catalog[row['caseId']], specs[row['slice']]
        base = output/row['path']/row['profile']
        names = list(spec['proofFiles'])+([SUBJECT_COMPLETION] if row['slice'] == 'sl1-subject' and row['profile'] != 'repaired-e' else [])
        proofs = {name: json.loads((base/name).read_text()) for name in names if (base/name).is_file()}
        primary = proofs.get(spec['proofFiles'][0], {})
        observed = {k: primary[k] for k in ('ok', 'classification', 'error', 'outcome', 'firingStep', 'delivery') if k in primary}
        if 'expired-retry/result.json' in proofs:
            observed['expiredRetryError'] = proofs['expired-retry/result.json'].get('error')
        entry = dict(caseId=row['caseId'], caseFamily=case.get('caseFamily'), profile=case['profile'], variant=case.get('variant'),
                     slice=row['slice'], path='run:'+row['path'], status=row['status'], sourceRefs=case.get('sourceRefs'),
                     assumptions=case.get('assumptions'), expected=case['expected'], frozenExecutionStatus=case.get('executionStatus'),
                     observed=observed, proofFiles=['run:'+row['path']+'/'+row['profile']+'/'+name for name in proofs],
                     historicalRun=spec['history'])
        if row['caseId'] in D47_ROWS:
            entry['label'] = D47_LABEL
        reported = None
        if row['status'] == 'PASS':
            reported = observed.get('classification') or (D47_LABEL if row['caseId'] in D47_ROWS else case['expected']['classification'])
        entry['reportedClassification'] = reported
        if 'failure' in row:
            entry['failure'] = row['failure']
        rows.append(entry)
    counts = {s: sum(r['status'] == s for r in rows) for s in ('PASS', 'FAILED', 'NOT_RUN', 'RUNNING')}
    return dict(catalogFiles=plan['catalog']['files'], runId=plan['runId'], counts=counts, rows=rows,
                note=('aggregated from the frozen catalog and the proof files that the e2 row checks accepted; no new oracle; the 4 '
                      'paper crash rows carry the D47 label and are never findings'))


def _criteria(plan, manifest, coverage, freeze_ok, versions_ok, proverif, stable):
    rows = manifest['rows']; by_id = {r['caseId']: r for r in coverage['rows']}
    all_pass = len(rows) == 56 and all(r['status'] == 'PASS' for r in rows)
    recovery = [r for r in rows if r['slice'] == 'recovery-expiry']
    guard_paths, guards_ok = [], True
    for case_id, guard in plan['guardRows'].items():
        row = by_id[case_id]; guard_paths.append(row['proofFiles'][0] if row['proofFiles'] else row['path'])
        guards_ok = guards_ok and row['status'] == 'PASS' and row['observed'].get('error') == guard['error']
    c4_inputs = all((ROOT/p).is_file() and sha256(ROOT/p) == plan['gateInputs'][p] for p in CRITERION4_INPUTS)
    proverif_ok = bool(proverif and proverif.get('matched') is True)
    verdicts = {
        'interface-and-source-review': freeze_ok,
        'legitimate-and-denied-controls': all_pass,
        'E01-E02-E03-classification': all_pass and len(coverage['rows']) == 56 and all(r['reportedClassification'] for r in coverage['rows']),
        'repairs-and-mutants': all_pass and guards_ok and proverif_ok and c4_inputs,
        'real-two-chain-and-recovery': all_pass and len(recovery) == 6,
        'proverif-and-negative-control': proverif_ok,
        'stable-hashed-input-output-tools': stable and versions_ok,
    }
    criteria = {}
    for name in E_CRITERIA:
        rule = plan['criteriaRules'][name]
        evidence = [p for p in rule['evidence'] if not p.startswith('run:<')]
        if name == 'repairs-and-mutants':
            evidence = evidence[:2]+guard_paths+evidence[2:]
        status = 'PENDING' if rule['pendingAfterRun'] else ('VERIFIED' if verdicts[name] else 'FAILED')
        criteria[name] = dict(status=status, evidencePaths=evidence, rule=rule['rule'], note=rule.get('note', ''))
    return criteria


def _result_files(output):
    files = {}
    for path in sorted(Path(output).rglob('*')):
        rel = path.relative_to(output)
        if not path.is_file() or str(rel) == 'manifest.json':
            continue
        if len(rel.parts) == 1 or rel.parts[0] in ('proverif', 'versions') or path.name in ('result.json', 'manifest.json'):
            files[str(rel)] = sha256(path)
    return files


def execute(plan_path, ack_path, output):
    output = Path(output)
    require(not output.resolve().is_relative_to(ROOT.resolve()), 'gate output outside the repository working tree (A1-0082)')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    manifest = dict(rq='E', executionMode='real-integrated', interfaceVersion='v1', adapterMode='symbolic', status='BLOCKED',
                    gateDecision=GATE_DECISION, startedAt=now(), endedAt=None, planPath=str(plan_path), planSha256=None, runId=None,
                    freezeMessage=None, acks=None, failure=None, sourceStable=None, worktreeUnchanged=None, planReverified=None,
                    stages={}, rows=[], slices={}, proverif=None, servicesStarted=[], adapterProcesses=[], resultFiles={},
                    hostMemory=dict(before=_memory(), after=None), worktree=dict(pre=None, post=None),
                    droppedStages=dict(DROPPED_STAGES), limitation=GATE_DECISION)

    def write():
        (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    write(); authorized = False; plan = None
    try:
        raw = Path(plan_path).read_bytes(); plan = json.loads(raw)
        manifest.update(planSha256=hashlib.sha256(raw).hexdigest(), runId=plan.get('runId'), freezeMessage=plan.get('freezeMessage'))
        verify_plan(plan)
        manifest.update(reviewMode=plan['reviewMode'], reviewDisclosure=plan['reviewDisclosure'])
        manifest['rows'] = [dict(caseId=case_id, slice=s['name'], case=e2.case_name(s['plan'], item), profile=item['profile'],
                                 path='catalog/'+s['name']+'/'+e2.case_name(s['plan'], item), status='NOT_RUN')
                            for s in plan['slices'] for item, case_id in zip(s['plan']['matrix'], s['caseIds'])]
        write()
        manifest['acks'] = e1._acks(ack_path, plan, manifest['planSha256'])
        authorized = True; manifest['status'] = 'RUNNING'
        manifest['worktree']['pre'] = _worktree(); write()
        # 1. verify-freeze and versions
        started = now(); freeze = verify_freeze(); versions = _versions(plan, output)
        (output/'verify-freeze.json').write_text(json.dumps(freeze, indent=2)+'\n')
        (output/'versions.json').write_text(json.dumps(versions, indent=2)+'\n')
        freeze_ok = freeze['status'] == 'UNCHANGED'
        manifest['stages']['verify-freeze-and-versions'] = dict(status='PASS' if freeze_ok and versions['ok'] else 'FAILED', startedAt=started,
                                                                endedAt=now(), freeze=freeze['status'], versionsOk=versions['ok'])
        # 2. source bracket (pre)
        started = now(); pre = _bracket()
        (output/'bracket-pre.json').write_text(json.dumps(_bracket_record(pre, 'pre'), indent=2)+'\n')
        pre_ok = (pre['gateInputs'] == plan['gateInputs'] and all(pre['agent3Sources'] == s['plan']['agent3Sources'] for s in plan['slices']))
        manifest['stages']['source-bracket-pre'] = dict(status='PASS' if pre_ok else 'FAILED', startedAt=started, endedAt=now())
        write()
        # 3. all 56 catalog rows (only from verified inputs; otherwise every row stays NOT_RUN and no service starts)
        started = now()
        if manifest['stages']['verify-freeze-and-versions']['status'] == 'PASS' and pre_ok:
            _run_catalog(plan, output, manifest, write)
            counts = {s: sum(r['status'] == s for r in manifest['rows']) for s in ('PASS', 'FAILED', 'NOT_RUN')}
            manifest['stages']['catalog-56'] = dict(status='PASS' if counts['PASS'] == 56 else 'FAILED', startedAt=started, endedAt=now(),
                                                    counts=counts)
        else:
            manifest['stages']['catalog-56'] = dict(status='NOT_RUN', startedAt=started, endedAt=now(),
                                                    reason='stage 1 or 2 failed; no service was started')
        write()
        # 6. ProVerif
        started = now(); manifest['proverif'] = run_proverif(plan, output)
        manifest['stages']['proverif'] = dict(status='PASS' if manifest['proverif']['matched'] else 'FAILED', startedAt=started, endedAt=now())
        # 7. source bracket (post), worktree and final plan verification
        started = now(); post = _bracket()
        (output/'bracket-post.json').write_text(json.dumps(_bracket_record(post, 'post'), indent=2)+'\n')
        manifest['worktree']['post'] = _worktree()
        try:
            verify_plan(plan); manifest['planReverified'] = True
        except Exception as error:
            manifest['planReverified'] = False; manifest['planReverifyFailure'] = dict(type=type(error).__name__, message=str(error))
        manifest['worktreeUnchanged'] = ({k: v for k, v in manifest['worktree']['pre'].items() if k != 'at'}
                                         == {k: v for k, v in manifest['worktree']['post'].items() if k != 'at'})
        manifest['sourceStable'] = pre_ok and post == pre and manifest['planReverified'] is True
        stable = manifest['sourceStable'] and manifest['worktreeUnchanged']
        manifest['stages']['source-bracket-post'] = dict(status='PASS' if stable else 'FAILED', startedAt=started, endedAt=now())
        # 8./9. coverage, gate evidence, result hashes and status
        coverage = _coverage(plan, output, manifest)
        (output/'catalog-coverage-56.json').write_text(json.dumps(coverage, indent=2)+'\n')
        criteria = _criteria(plan, manifest, coverage, freeze_ok, versions['ok'], manifest['proverif'], stable)
        evidence = dict(rq='E', runId=plan['runId'], planSha256=manifest['planSha256'], freezeMessage=plan['freezeMessage'],
                        criteria=criteria, droppedStages=dict(DROPPED_STAGES), gateDecision=GATE_DECISION,
                        reviewDisclosure=plan['reviewDisclosure'], writtenAt=now())
        (output/'gate-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
        manifest['stages']['gate-evidence'] = dict(status='WRITTEN', at=now(),
                                                   criteria={k: v['status'] for k, v in criteria.items()})
        passed = all(manifest['stages'][s]['status'] == 'PASS' for s in ('verify-freeze-and-versions', 'source-bracket-pre', 'catalog-56',
                                                                         'proverif', 'source-bracket-post'))
        manifest['status'] = 'PASS' if passed else 'FAILED'
        manifest['resultFiles'] = _result_files(output)
        manifest['stages']['manifest'] = dict(status='WRITTEN', at=now())
    except BaseException as error:
        manifest['failure'] = dict(type=type(error).__name__, message=str(error))
        manifest['status'] = 'FAILED' if authorized else 'BLOCKED'
        if authorized and plan is not None:
            try: manifest['sourceStable'] = all(e2._sources() == s['plan']['agent3Sources'] for s in plan['slices'])
            except Exception: manifest['sourceStable'] = False
        if not isinstance(error, Exception):
            raise
    finally:
        manifest['hostMemory']['after'] = _memory(); manifest['endedAt'] = now()
        write()
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True); p.add_argument('--acks', type=Path); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); result = execute(args.plan, args.acks, args.output)
    counts = {s: sum(r['status'] == s for r in result['rows']) for s in ('PASS', 'FAILED', 'NOT_RUN', 'RUNNING')}
    print(json.dumps(dict(status=result['status'], failure=result['failure'], sourceStable=result['sourceStable'],
                          worktreeUnchanged=result['worktreeUnchanged'], rows=counts,
                          proverifMatched=(result['proverif'] or {}).get('matched'), servicesStarted=len(result['servicesStarted']),
                          gateDecision=result['gateDecision'], reviewDisclosure=result.get('reviewDisclosure', e1.SOLO_DISCLOSURE)), indent=2))
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__': raise SystemExit(main())
