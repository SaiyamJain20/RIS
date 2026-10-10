"""Exact-plan gated, fresh two-chain C-E2 recovery or audit comparisons.

Recovery or duplicate outcome cases across three profiles, with wrong-issuer, Alice and Bob
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
# Frozen catalog expectations for the SL2 rows (classification, error).
RELAY_EXPECTED = {('paper-strict', 'forged-tuple'): ('SPEC_GAP', None), ('paper-minimal', 'forged-tuple'): ('SPEC_GAP', None),
                  ('repaired-e', 'forged-tuple'): ('REPAIR_SUPPORTED', 'BAD_SIGNATURE'),
                  ('paper-strict', 'new-reference-replay'): ('SPEC_GAP', None),
                  ('paper-minimal', 'new-reference-replay'): ('SPEC_GAP', None),
                  ('repaired-e', 'new-reference-replay'): ('REPAIR_SUPPORTED', 'REPLAY'),
                  ('repaired-e', 'same-nonce-distinct-digests'): ('REPAIR_SUPPORTED', 'REPLAY')}
ACCEPTANCE = ROOT/'evaluation/evidence/e2/crash-transport-20261009/start-contract-acceptance.json'


def _sources():
    paths = [p for p in (ROOT/'evaluation').rglob('*.py') if 'tests' not in p.relative_to(ROOT/'evaluation').parts]
    paths += list((ROOT/'evaluation/fixtures').rglob('*.json'))+list((ROOT/'evaluation/scenarios').rglob('*.json'))
    paths += list((ROOT/'interfaces/v1').rglob('*'))+list((ROOT/'interfaces/proposals/v1').rglob('*.json'))
    paths += [ROOT/p for p in ('AGENTS.md', 'SPEC.md', 'PLAN.md', 'uv.lock', 'pyproject.toml', 'evaluation/toolchain.json')]
    paths += [CONTRACT, ACCEPTANCE, e1.PIN_REVIEW]
    paths += [p for p in [ROOT/'evaluation/host-tools.json'] if p.is_file()]
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


def create_plan(*, run_id, freeze_message, expired_retry=False, duplicate_outcome=False, nonce_replay=False,
                subject_substitution=False, relay_stress=False, review_mode='strict'):
    # Retain the previously reviewed environment, mining/ports, tool and custody
    # recipe; any new exact runtime bytes require new full execution-plan ACKs.
    flags = (expired_retry, duplicate_outcome, nonce_replay, subject_substitution, relay_stress)
    require(all(type(flag) is bool for flag in flags) and sum(flags) <= 1, 'explicit nonoverlapping probe selection')
    require(not subject_substitution or review_mode == e1.SOLO, 'SL1 subject plans are solo-phase plans (A1-0061)')
    require(not relay_stress or review_mode == e1.SOLO, 'SL2 relay plans are solo-phase plans (A1-0061)')
    plan = e1.create_plan(run_id=run_id, freeze_message=freeze_message, review_mode=review_mode)
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
    if expired_retry:
        plan.update(schemaVersion='hmbc-e2-recovery-expiry-plan/v1', expiredRetry=True,
                    executionScope='six fresh logical recovery comparisons plus six expired cached retries; not full RQ matrix',
                    expiryProbe=dict(order='after Alice recovery/completion/outcome, before Bob control',
                                     clock='DBC evm_setNextBlockTimestamp(max(latest+1, original grant expiry)); evm_mine; verify latest and pending >= expiry',
                                     input='identical release envelope with the recovered grantId and deployment',
                                     expected='EXPIRED; entire redacted worker cache/events/attempts and native grant/request/all contract logs unchanged',
                                     scope='refusal after successful recovery; not first restart at expiry, exact wall-clock equality or power-loss durability'))
        plan['controls'].append('expired-original-grant-cached-retry-no-new-event')
        plan['limitations'].append('Six expired retry probes supplement historical recovery evidence; remaining50 catalog/mutants/windows/report/gate still required.')
    if duplicate_outcome:
        plan.update(schemaVersion='hmbc-e2-duplicate-outcome-plan/v1', duplicateOutcome=True,
                    executionScope='three fresh duplicate outcome comparisons; not full RQ matrix',
                    matrix=[dict(profile=profile, point=None) for profile in e1.PROFILES],
                    caseIds=['E03-duplicate-outcome-'+profile for profile in e1.PROFILES],
                    classification='SUPPORTED for both paper reconstruction profiles; REPAIR_SUPPORTED for repaired-e; no paper implementation claim',
                    controls=['wrong-admin-before-H2', 'registered-Alice-allow-release-one-outcome',
                              'identical-outcome-call-mined-REPLAY-no-change', 'registered-Bob-policy-deny'],
                    restart='none; production adapter only, no crash hook selected',
                    observation='successful Alice outcome then identical application calldata in a fresh transaction; mined Rejected(8)',
                    timing='normal live grant release before original expiry; late duplicate reconciliation allowed; no expiry extension',
                    duplicateProbe=dict(order='after successful Alice outcome, before Bob denial',
                                        call='relay resubmits identical reportOutcome/reportAttestedOutcome arguments with fresh transaction nonce',
                                        expected='status0, decoded Rejected(8)/REPLAY, no receipt logs; all request/grant/worker/cache and PBC/DBC contract logs unchanged',
                                        positive='exactly one prior successful outcome and GrantIssued plus Alice release and Bob denial'),
                    limitations=['Both new exact full plan ACKs required before services.',
                                 'Three duplicate outcome cases only; all50 remaining schedules (including these3 until measured), live mutants/windows/report/gate remain required.',
                                 'Paper-derived reconstruction behavior, not authors implementation or discovered vulnerability.',
                                 'Production adapter only; symbolic crypto/safe-ledger/trusted-worker; no delivery/ABE/consensus/power-loss proof.'])
        plan.pop('workerExpected')
    if nonce_replay:
        plan.update(schemaVersion='hmbc-e2-nonce-replay-plan/v1', nonceReplay=True,
                    executionScope='three fresh identical accepted request replays; not full RQ matrix',
                    matrix=[dict(profile=profile, point=None) for profile in e1.PROFILES],
                    caseIds=['E01-nonce-replay-'+profile for profile in e1.PROFILES],
                    controls=['wrong-admin-before-H2', 'registered-Alice-allow-grant',
                              'identical-ACSC-call-mined-REPLAY-no-change-before-release',
                              'original-Alice-release-completion-one-outcome', 'registered-Bob-policy-deny'],
                    restart='none; production adapter only, no crash hook',
                    observation='identical accepted policyEnf/consumeDecision application calldata; fresh relay transaction nonce; status0/Rejected8/no logs',
                    timing='replay before original request/grant expiry; Alice release remains strictly before original expiry; unexpected expiry fails',
                    replayProbe=dict(order='after checked native Alice grant, before first release/completion/outcome',
                                     positive='one logged FORWARDED request and one allowed matching native grant/access log',
                                     expected='REPLAY8; complete grant/request/nonce/access count/worker/PBC and DBC histories unchanged',
                                     nonce='paper profiles false; repaired-e true from original acceptance',
                                     references='identical accepted request/forward reference; never fabricate a new reference',
                                     operations='no adapter operation/clock advance/crash/restart during replay; worker exporter read-only'),
                    classification='paper SUPPORTED as tested reconstruction; repaired-e REPAIR_SUPPORTED; no original implementation claim',
                    limitations=['Both NEW exact full execution-plan ACKs precede services.',
                                 'Three of remaining47 prospective schedules only; no complete matrix, live mutants/windows/report/gate result.',
                                 'Equal idle-worker snapshots are not worker retry/idempotence evidence.',
                                 'Symbolic crypto/safe-ledger/trusted-worker; no delivery/ABE/consensus/power-loss proof.'])
        plan['replayProbe']['nativeSnapshots'] = dict(
            block='one explicit latest-selected historical block per chain per snapshot',
            identity='chain and block before/after each group; all selected ABI hashes before/after',
            history='all deployment contract addresses; from0 to the selected block number',
            budget='at most16 view/log queries per group; shared PublicChain timeout10s',
            evidence='individual ABI/calldata/return rows; separate before/after block anchors',
            worker='both full idle-worker exports before first release; no worker operation')
        plan['limitations'][1] = ('Three fresh replay comparisons; historical paper2 complete/repaired1 incomplete, '
                                  '44 untouched schedules;45 catalog comparisons still need completion, plus mutants/windows/report/gate.')
        plan['limitations'].append('Grouped RPC consistency cannot detect a transient reorg restored between boundary checks; safe-ledger assumption unchanged.')
        plan.pop('workerExpected')
    if subject_substitution:
        plan.update(schemaVersion='hmbc-e2-subject-substitution-plan/v1', subjectSubstitution=True,
                    executionScope='three fresh E01 subject-substitution comparisons (SL1); not full RQ matrix',
                    matrix=[dict(profile=profile, point=None) for profile in e1.PROFILES],
                    caseIds=['E01-subject-substitution-'+profile for profile in e1.PROFILES],
                    controls=['wrong-admin-before-H2', 'registered-Alice-allow-release-one-outcome', 'registered-Bob-policy-deny',
                              'fresh-second-deployment-subject-stress'],
                    restart='none; production adapter only, no crash hook',
                    freshness=('fresh chain pair per matrix row; controls on deployment D1; stress on a fresh second deployment D2 '
                               'on the same chain pair with its own bootstrap, adapter process and 0700 state; relay/CA-admin balances '
                               'reset to 1000 ETH before D2'),
                    observation=('Alice signs and logs a real PBC request on D2; the relay changes ONLY gid to registered Bob in the '
                                 'paper ForwardedRequest (policyEnf) or the repaired request (consumeDecision) and keeps Alice\'s '
                                 'verified credential records and, in repaired-e, her original ALLOW certificate'),
                    subjectProbe=dict(
                        target='registered Bob gid from the D2 bootstrap (no doctor role; policy-denied in his own right)',
                        preRelease=('whole block-anchored grant/request/two-nonce/access-count/decoded two-chain histories and idle '
                                    'worker before/after one mined ACSC call; paper: one GrantIssued+AccessLog for Bob, zero native '
                                    'recipient, TTL policyEnf+30s, original Alice request still FORWARDED; repaired-e: mined status0 '
                                    'Rejected(2) WRONG_SUBJECT, no logs, whole state unchanged'),
                        completion=('paper only: registered PBC recipient keys read for both subjects; one production release on '
                                    'the substituted grant strictly before its expiry; response bound to Bob registered key; same '
                                    'response completed with keyref:user:bob (decryptable) and keyref:user:alice (WRONG_SUBJECT); '
                                    'exactly one worker intent/send/cache delta; completions change nothing; no outcome reported'),
                        snapshots=('native views/logs per chain at one explicit block inside each read group; worker exports at '
                                   'each stage; Cast hash checkpoint per read group/submit (A1-0061 D-5b)')),
                    classification=('paper-strict/paper-minimal: SPEC_GAP (CONDITIONAL) under compromised-relay stress outside the '
                                    'paper secure-isolation assumption (A01); repaired-e: REPAIR_SUPPORTED, WRONG_SUBJECT(2); '
                                    'tested reconstruction results, never an HMBC exploit or authors-implementation claim'),
                    timing='each stage strictly before the original request/grant expiry; unexpected expiry fails visibly; no TTL change',
                    limitations=['Solo-phase plan: both exact solo ACKs (A1 and S2) and the committed S3 FREEZE precede services.',
                                 'Three of the 44 remaining catalog comparisons; no complete matrix, live mutants/window/report/gate.',
                                 'Delivery unknown; symbolic adapter; safe-ledger/trusted-worker/one trusted witness.',
                                 'Grouped RPC consistency cannot detect a transient reorg restored between boundary checks.'])
        plan.pop('workerExpected')
    if relay_stress:
        rows = [(p, 'forged-tuple') for p in e1.PROFILES]+[(p, 'new-reference-replay') for p in e1.PROFILES]
        rows.append(('repaired-e', 'same-nonce-distinct-digests'))
        plan.update(schemaVersion='hmbc-e2-relay-stress-plan/v1', relayStress=True,
                    executionScope='seven fresh E01 relay-stress comparisons (SL2); not full RQ matrix',
                    matrix=[dict(profile=profile, point=None, variant=variant) for profile, variant in rows],
                    caseIds=['E01-'+variant+'-'+profile for profile, variant in rows],
                    controls=['wrong-admin-before-H2', 'registered-Alice-allow-release-one-outcome', 'registered-Bob-policy-deny',
                              'fresh-second-deployment-relay-stress'],
                    restart='none; production adapter only, no crash hook, no release in the stress',
                    freshness=('fresh chain pair per matrix row; controls on deployment D1; stress on a fresh second deployment D2 '
                               'on the same chain pair with its own bootstrap, adapter process and 0700 state; relay/CA-admin balances '
                               'reset to 1000 ETH before D2'),
                    observation='relay-submitted public ACSC calls only; whole decoded two-chain histories and selected views; idle worker',
                    relayProbe=dict(
                        forgedTuple=('paper: relay policyEnf({fixed synthetic pbcRequestId never sent to the PBC, Alice gid, record, READ}, '
                                     'Alice credential records from the public TMSC.checkCredentials view) -> GrantIssued(recipient 0, TTL +30 s)'
                                     '+AccessLog with no PBC request or log (ACCEPT/SPEC_GAP); repaired-e: real Alice request, checkpoint and '
                                     'honest certificate; eth_call (simulation, never mined) of the honest certificate must return the derived '
                                     'grant id; the honest witness signature and the relay signature must recover under the same '
                                     'runner digest and DBC/KSSC EIP-712 domain (A1-0064); then the identical decision signed by the '
                                     'TEST-ONLY relay key (non-witness) is mined -> Rejected BAD_SIGNATURE(1) (SigLib: signer not in '
                                     'witness set), nothing changed'),
                        newReferenceReplay=('paper: original forwarded tuple granted, then the same verified tuple under a fixed fresh '
                                            'relay reference -> second grant, no second PBC request (A25; ACCEPT/SPEC_GAP); repaired-e: the '
                                            'original signed request and certificate re-consumed with identical calldata -> REPLAY(8) from '
                                            'grant uniqueness at KSSC.sol:180, before the nonce check'),
                        sameNonce=('repaired-e only: two Alice requests with nonce 1 and expiry e and e-1 (distinct digests and grant ids), '
                                   'both forwarded, one checkpoint after both, both ALLOW certificates collected before any consume; '
                                   'consume first (grant, nonce consumed), then the second pre-collected certificate -> REPLAY(8) at the '
                                   'nonce guard KSSC.sol:182 (lines 181-183); pre/post states read afterwards at explicit blocks second-1 '
                                   'and second (D-5c); every chain timestamp recorded against both 30 s lifetimes (A1-0064)'),
                        snapshots=('native views/logs per chain at one explicit block per read group; Cast hash checkpoint per read '
                                   'group/submit (A1-0061 D-5b); idle D2 worker = verified never-instantiated record (pinned exporter '
                                   'exit 1 with its exact no-worker.sqlite message and both database paths absent; SL2 performs no '
                                   'worker operation) or an unchanged idle export; no state-changing call instantiates it (S3-0008)')),
                    classification=('paper-strict/paper-minimal forged tuple and new reference: SPEC_GAP (configured-relay stress outside '
                                    'A01); repaired-e: REPAIR_SUPPORTED with BAD_SIGNATURE(1), REPLAY(8) and REPLAY(8); tested '
                                    'reconstruction results, never an HMBC exploit or authors-implementation claim'),
                    timing='repaired-e steps strictly before the original request expiry (30 s); unexpected expiry fails visibly; no TTL change',
                    limitations=['Solo-phase plan: both exact solo ACKs (A1 and S2) and the committed S3 FREEZE precede services.',
                                 'Seven of the 41 remaining catalog comparisons; no complete matrix, live mutants/window/report/gate.',
                                 'Repaired new-reference replay cannot reach the nonce guard; only the same-nonce row does.',
                                 'Delivery unknown; symbolic adapter; safe-ledger/trusted-worker/one trusted witness.'])
        plan.pop('workerExpected')
    return plan


def verify_plan(plan):
    require(plan == create_plan(run_id=plan['runId'], freeze_message=plan['freezeMessage'],
                                expired_retry=plan.get('expiredRetry', False), duplicate_outcome=plan.get('duplicateOutcome', False),
                                nonce_replay=plan.get('nonceReplay', False), subject_substitution=plan.get('subjectSubstitution', False),
                                relay_stress=plan.get('relayStress', False), review_mode=plan.get('reviewMode', 'strict')),
            'exact current E2 plan/source/config')
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
        if plan.get('reviewMode') == e1.SOLO:
            record.update(reviewMode=e1.SOLO, reviewDisclosure=e1.SOLO_DISCLOSURE)
        record['acks'] = e1._acks(ack_path, plan, record['planSha256'])
        if plan.get('duplicateOutcome', False):
            record.update(executionMode='two-chain-e2-duplicate-outcome-slice',
                          limitation='Three duplicate outcome comparisons only; no complete catalog or RQ gate.')
        if plan.get('nonceReplay', False):
            record.update(executionMode='two-chain-e2-nonce-replay-slice',
                          limitation='Three identical accepted request replays only; no complete catalog or RQ gate.')
        if plan.get('subjectSubstitution', False):
            record.update(executionMode='two-chain-e2-subject-substitution-slice',
                          limitation='Three subject-substitution comparisons only; no complete catalog or RQ gate.')
        if plan.get('relayStress', False):
            record.update(executionMode='two-chain-e2-relay-stress-slice',
                          limitation='Seven E01 relay-stress comparisons only; no complete catalog or RQ gate.')
        authorized = True; record['status'] = 'RUNNING'
        for item in plan['matrix']:
            verify_plan(plan)
            probe_name = 'nonce-replay' if plan.get('nonceReplay', False) else 'duplicate-outcome'
            if plan.get('subjectSubstitution', False): probe_name = 'subject-substitution'
            if plan.get('relayStress', False): probe_name = item['variant']
            case = item['profile']+'-'+(item['point'] or probe_name); destination = output/case; destination.mkdir()
            child = dict(profiles={}, servicesStarted=[], adapterProcesses=[])
            case_records[case] = child
            record['cases'][case] = dict(status='RUNNING', manifest=case+'/manifest.json')
            (output/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
            selected = copy.deepcopy(plan); selected['runId'] = plan['runId']+'-'+(item['point'] or probe_name)
            probe_options = {'duplicate_outcome': True} if plan.get('duplicateOutcome', False) else {}
            if plan.get('nonceReplay', False): probe_options = {'nonce_replay': True}
            if plan.get('subjectSubstitution', False): probe_options = {'subject_substitution': True}
            if plan.get('relayStress', False): probe_options = {'relay_stress': item['variant']}
            e1._profile(selected, item['profile'], destination/item['profile'], child, recovery_point=item['point'],
                        expired_retry=plan.get('expiredRetry', False), **probe_options)
            if plan.get('relayStress', False):
                proof = json.loads((destination/item['profile']/'relay-stress/result.json').read_text())
                expected = RELAY_EXPECTED[(item['profile'], item['variant'])]
                require(proof['ok'] is True and proof['delivery'] == 'unknown' and proof['variant'] == item['variant']
                        and (proof['classification'], proof['error']) == expected, 'complete checked relay stress result')
            elif plan.get('subjectSubstitution', False):
                stress = destination/item['profile']/'subject-stress'
                pre = json.loads((stress/'subject-substitution/result.json').read_text())
                repaired = item['profile'] == 'repaired-e'
                require(pre['ok'] is True and pre['delivery'] == 'unknown' and pre['workerUnchanged'] is True
                        and pre['classification'] == ('REPAIR_SUPPORTED' if repaired else 'SPEC_GAP')
                        and pre['error'] == ('WRONG_SUBJECT' if repaired else None), 'complete checked subject pre-release result')
                completion = stress/'subject-completion/result.json'
                if repaired:
                    require(not completion.exists(), 'repaired subject stress has no release')
                else:
                    done = json.loads(completion.read_text())
                    require(done['ok'] is True and done['classification'] == 'SPEC_GAP' and done['delivery'] == 'unknown'
                            and done['bobDecryptable'] is True and done['aliceError'] == 'WRONG_SUBJECT'
                            and done['outcomeTested'] is False, 'complete checked paper subject completion')
            elif plan.get('duplicateOutcome', False) or plan.get('nonceReplay', False):
                proof = json.loads((destination/item['profile']/('alice/'+probe_name+'/result.json')).read_text())
                require(proof['ok'] is True and proof['error'] == 'REPLAY' and proof['delivery'] == 'unknown'
                        and proof['workerUnchanged'] is True and proof['nativeUnchanged'] is True
                        and proof['identicalCalldata'] is True, 'complete checked native replay result')
            else:
                proof = json.loads((destination/item['profile']/'recovery/result.json').read_text())
                require(proof['ok'] is True and proof['delivery'] == 'unknown', 'complete checked recovery result')
            if plan.get('expiredRetry', False):
                expiry = json.loads((destination/item['profile']/'expired-retry/result.json').read_text())
                require(expiry['ok'] is True and expiry['error'] == 'EXPIRED' and expiry['delivery'] == 'unknown'
                        and expiry['workerUnchanged'] is True and expiry['nativeUnchanged'] is True, 'complete expired retry refusal')
                record['cases'][case]['expiredRetry'] = 'EXPIRED_NO_CHANGE_PASS'
            if plan.get('subjectSubstitution', False):
                record['cases'][case]['status'] = 'SUBJECT_SUBSTITUTION_CONTROL_PASS'
                continue
            if plan.get('relayStress', False):
                record['cases'][case]['status'] = 'RELAY_STRESS_CONTROL_PASS'
                continue
            record['cases'][case]['status'] = ('NONCE_REPLAY_CONTROL_PASS' if plan.get('nonceReplay', False)
                                             else ('DUPLICATE_OUTCOME_CONTROL_PASS' if plan.get('duplicateOutcome', False) else 'RECOVERY_CONTROL_PASS'))
        verify_plan(plan); record.update(status='E2_DUPLICATE_OUTCOME_SLICE_PASS' if plan.get('duplicateOutcome', False) else ('E2_RECOVERY_EXPIRY_SLICE_PASS' if plan.get('expiredRetry', False) else 'E2_RECOVERY_SLICE_PASS'), sourceStable=True)
        if plan.get('nonceReplay', False): record['status'] = 'E2_NONCE_REPLAY_SLICE_PASS'
        if plan.get('subjectSubstitution', False): record['status'] = 'E2_SUBJECT_SUBSTITUTION_SLICE_PASS'
        if plan.get('relayStress', False): record['status'] = 'E2_RELAY_STRESS_SLICE_PASS'
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
    return 0 if result['status'] in ('E2_RECOVERY_SLICE_PASS', 'E2_RECOVERY_EXPIRY_SLICE_PASS', 'E2_DUPLICATE_OUTCOME_SLICE_PASS',
                                     'E2_NONCE_REPLAY_SLICE_PASS', 'E2_SUBJECT_SUBSTITUTION_SLICE_PASS', 'E2_RELAY_STRESS_SLICE_PASS') else 2


if __name__ == '__main__': raise SystemExit(main())
