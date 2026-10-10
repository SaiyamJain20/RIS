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
AUDIT_EXPECTED = {('paper-strict', 'dropped-outcome'): ('SUPPORTED', None), ('paper-minimal', 'dropped-outcome'): ('SUPPORTED', None),
                  ('repaired-e', 'dropped-outcome'): ('REPAIR_SUPPORTED', None),
                  ('paper-strict', 'fabricated-outcome'): ('SPEC_GAP', None), ('paper-minimal', 'fabricated-outcome'): ('SPEC_GAP', None),
                  ('repaired-e', 'fabricated-outcome'): ('REPAIR_SUPPORTED', 'WRONG_PROFILE')}
RECEIPT_EXPECTED = {'receipt-binding-control': ('REPAIR_SUPPORTED', 'WRONG_SUBJECT'),
                    'receipt-signature-control': ('SUPPORTED', 'WRONG_SUBJECT'), 'receipt-binding-positive': ('SUPPORTED', None)}
# S2-0007/A1-0064: protocol pin 0716a8e, testtools/deviating_witness.py.
DEVIATION_PATH = 'protocol/testtools/deviating_witness.py'
DEVIATION_SHA256 = '0511ba571b71d960d8ffbe4b8c811da99ed7de53a4b7515ac425c5291cc3c2d7'
TRUST_EXPECTED = {**{(p, 'wrong-issuer'): ('SUPPORTED', 'UNAUTHORIZED_CALLER') for p in e1.PROFILES},
                  ('paper-strict', 'signed-list-rollback'): ('SPEC_GAP', None), ('paper-minimal', 'signed-list-rollback'): ('SPEC_GAP', None),
                  ('repaired-e', 'signed-list-rollback'): ('REPAIR_SUPPORTED', 'STALE_ANCHOR')}
BARRIER_EXPECTED = {**{(p, v): ('SPEC_GAP', None) for p in ('paper-strict', 'paper-minimal') for v in e1.BARRIER_VARIANTS},
                    ('repaired-e', 'pre-barrier-revocation'): ('REPAIR_SUPPORTED', None),
                    ('repaired-e', 'post-barrier-revocation'): ('REPAIR_SUPPORTED', 'STALE_STATE'),
                    ('repaired-e', 'expired-duty'): ('REPAIR_SUPPORTED', 'EXPIRED')}
# A1-0034 owner producer at ledger pin 933d2a7 (A1-0061 D-6).
SIGN_LIST_PATH, SIGN_LIST_SHA256 = 'ledger/tools/sign_list.sh', '806e9a98a52899ca5fc4fe33e1e90e39d7607a51a4f5c6c5942c0edd21c37ded'
SIGN_SCRIPT_PATH, SIGN_SCRIPT_SHA256 = 'ledger/script/SignList.s.sol', '7aa3b1dd085f5aaaa6aa7b28191d3b6d0cfd3ff02bb0b61291daead13e3ba177'
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
                subject_substitution=False, relay_stress=False, audit_stress=False, receipt_stress=False, trust_stress=False,
                barrier_stress=False, review_mode='strict'):
    # Retain the previously reviewed environment, mining/ports, tool and custody
    # recipe; any new exact runtime bytes require new full execution-plan ACKs.
    flags = (expired_retry, duplicate_outcome, nonce_replay, subject_substitution, relay_stress, audit_stress, receipt_stress, trust_stress,
             barrier_stress)
    require(all(type(flag) is bool for flag in flags) and sum(flags) <= 1, 'explicit nonoverlapping probe selection')
    require(not subject_substitution or review_mode == e1.SOLO, 'SL1 subject plans are solo-phase plans (A1-0061)')
    require(not relay_stress or review_mode == e1.SOLO, 'SL2 relay plans are solo-phase plans (A1-0061)')
    require(not audit_stress or review_mode == e1.SOLO, 'SL3 audit plans are solo-phase plans (A1-0061)')
    require(not receipt_stress or review_mode == e1.SOLO, 'SL4 receipt plans are solo-phase plans (A1-0061)')
    require(not trust_stress or review_mode == e1.SOLO, 'SL5 trust plans are solo-phase plans (A1-0061)')
    require(not barrier_stress or review_mode == e1.SOLO, 'SL6 barrier plans are solo-phase plans (A1-0061)')
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
    if audit_stress:
        rows = [(p, v) for v in ('dropped-outcome', 'fabricated-outcome') for p in e1.PROFILES]
        plan.update(schemaVersion='hmbc-e2-audit-stress-plan/v1', auditStress=True,
                    executionScope='six fresh E03 audit-stress comparisons (SL3); not full RQ matrix',
                    matrix=[dict(profile=profile, point=None, variant=variant) for profile, variant in rows],
                    caseIds=['E03-'+variant+'-'+profile for profile, variant in rows],
                    controls=['wrong-admin-before-H2', 'registered-Alice-allow-release-one-outcome', 'registered-Bob-policy-deny',
                              'fresh-second-deployment-audit-stress'],
                    restart='none; production adapter only, no crash hook',
                    freshness=('fresh chain pair per matrix row; controls on deployment D1; stress on a fresh second deployment D2 '
                               'on the same chain pair with its own bootstrap, adapter process and 0700 state; relay/CA-admin balances '
                               'reset to 1000 ETH before D2'),
                    observation='relay-submitted public calls and production adapter operations; whole decoded two-chain histories; worker log',
                    auditProbe=dict(
                        droppedOutcome=('REQUEST_ACCESS > FORWARD_OR_CONSUME > RELEASE > DROP_OUTCOME (A1-0064/S2-0007 R2): '
                                        'encrypt_record registers the record commitments and instantiates the worker as RELEASE requires; '
                                        'Alice request, grant (paper policyEnf, repaired checkpoint+decision+consumeDecision); ONE production '
                                        'release strictly before grant expiry, bound to the RSC registered key (paper, native recipient 0, '
                                        'D35/A38) or the signed recipient (repaired); no outcome reported; PBC request stays FORWARDED with '
                                        'outcomeLogId 0 (PENDING); worker gains exactly intent+one attempted send, delivery unknown; native '
                                        'state unchanged by the release'),
                        fabricatedOutcome=('REQUEST_ACCESS > FABRICATE_OUTCOME: relay PSC.reportOutcome(digest, derived grantId, fixed '
                                           'synthetic outcome digest) for the logged request with no DBC grant or consumption; paper: '
                                           'OUTCOME(4) LSC log with complete details + OutcomeRecorded, status 2, DBC unchanged (CONDITIONAL/'
                                           'SPEC_GAP); repaired-e: mined Rejected WRONG_PROFILE(21), nothing changed, and attest_grant of the '
                                           'absent grant refused NOT_COMMITTED by the honest witness; no worker operation (verified '
                                           'never-instantiated worker, D49)'),
                        snapshots=('native views/logs per chain at one explicit block per read group; Cast hash checkpoint per read '
                                   'group/submit (A1-0061 D-5b); worker export or verified never-instantiated record (D49)')),
                    classification=('dropped outcome: paper SUPPORTED, repaired-e REPAIR_SUPPORTED (PENDING); fabricated outcome: paper '
                                    'SPEC_GAP (configured-relay stress outside A01), repaired-e REPAIR_SUPPORTED with WRONG_PROFILE(21); '
                                    'tested reconstruction results, never an HMBC exploit or authors-implementation claim'),
                    timing='paper release strictly before policyEnf + 30 s (A24); repaired steps strictly before request expiry; '
                           'unexpected expiry fails visibly; no TTL change',
                    limitations=['Solo-phase plan: both exact solo ACKs (A1 and S2) and the committed S3 FREEZE precede services.',
                                 'Six of the 34 remaining catalog comparisons; no complete matrix, live mutants/window/report/gate.',
                                 'Delivery unknown: worker RELEASE_SENT is an attempted send; reconciliation needs eventual delivery.',
                                 'Symbolic adapter; safe-ledger/trusted-worker/one trusted witness.'])
        plan.pop('workerExpected')
    if receipt_stress:
        rows = [(variant, field) for variant, fields in e1.RECEIPT_VARIANTS.items() for field in fields]
        owners = plan['owners']['protocol']['entries']
        require(owners.get(DEVIATION_PATH) == DEVIATION_SHA256, 'deviating witness is the S2-0007 owner inventory entry')
        plan.update(schemaVersion='hmbc-e2-receipt-stress-plan/v1', receiptStress=True,
                    executionScope='seven fresh repaired-e E03 receipt controls (SL4); not full RQ matrix',
                    matrix=[dict(profile='repaired-e', point=None, variant=variant, field=field) for variant, field in rows],
                    caseIds=['E03-'+variant+('-'+field if field else '')+'-repaired-e' for variant, field in rows],
                    controls=['wrong-admin-before-H2', 'registered-Alice-allow-release-one-outcome', 'registered-Bob-policy-deny',
                              'fresh-second-deployment-receipt-control'],
                    restart='none; production adapter only, no crash hook',
                    freshness=('fresh chain pair per matrix row; controls on deployment D1; the receipt row on a fresh second '
                               'deployment D2 on the same chain pair with its own bootstrap, adapter process and 0700 state, its own '
                               'fresh forwarded request, actual allowed grant and honest receipt; relay/CA-admin balances reset to '
                               '1000 ETH before D2'),
                    observation=('relay-submitted public calls, production adapter operations and the pinned TEST-ONLY deviating '
                                 'witness command; whole decoded two-chain histories; worker never-instantiated record'),
                    receiptProbe=dict(
                        steps=('REQUEST_ACCESS > FORWARD_OR_CONSUME (checkpoint, honest ALLOW certificate, consumeDecision) > '
                               'ATTEST_GRANT (production witness, before any report on the request) > [binding: RESIGN_RECEIPT_FIELD '
                               'via the deviating witness at the honest receipt dbcBlockNumber | signature: ALTER_RECEIPT_KEEP_SIGNATURE, '
                               'same deterministic value, honest signature kept, no tool | positive: none] > REPORT_OUTCOME (relay '
                               'PSC.reportAttestedOutcome(digest, fixed synthetic outcome digest, receipt, signatures))'),
                        expected=('binding x3: mined Rejected WRONG_SUBJECT(2), no events, whole native state unchanged, PBC stays '
                                  'FORWARDED (REPAIR_SUPPORTED; A40 deliberate deviation); signature x3: same rejection, the binding '
                                  'check precedes quorum (SUPPORTED; cannot kill MUT_NO_RECEIPT_BINDING); positive: LSC OUTCOME(4) log '
                                  'with details abi.encode(digest, outcomeDigest, receipt, relay) then AttestedOutcomeRecorded(digest, '
                                  'grantId, outcomeDigest, dbcBlockNumber, logId), status 2, DBC unchanged (ACCEPT/SUPPORTED); ledger '
                                  '933d2a7 PSC.sol:240-283'),
                        deviatingWitness=dict(
                            module='testtools.deviating_witness', path=DEVIATION_PATH, sha256=DEVIATION_SHA256,
                            invocation=list(e1.DEVIATION_TEMPLATE), cwd='materialized protocol snapshot (protocol/)',
                            conditions=[
                                'S2-0007 conditions accepted in A1-0064; binding rows only; owner command, never an adapter operation.',
                                'Exact pinned bytes re-hashed before every call; argv built only from this template; no --value.',
                                '--deployment is the same deployment file (byte-identical) the stress adapter was pinned with (R11).',
                                '--at-block is the honest receipt dbcBlockNumber of that row (honest attest_grant first).',
                                'Any non-zero exit is a failed trial: no retry, no report; published only as output sha256 and first line.',
                                'Before use, three-way check: only the named field differs from the honest receipt; the signature '
                                'recovers to the configured witness under the evaluator own EIP-712 encoder (HMBCReceipt v1, PBC PSC '
                                'domain); testOnly is true and deviation.field equals the row field; plus the default deterministic '
                                'alteration value.',
                                'Published artifact keeps testOnly and deviation and is labelled A40 deliberate witness deviation, not '
                                'an honest-witness receipt and not an HMBC result.',
                                'never publish private keys, seeds or anything derived from a key label, raw release tokens (D1 Alice '
                                'control: tokenSha256 only), or the raw tool command log (it stays in the private run output).']),
                        workerPrecondition=('re-checked for SL4 at protocol pin 0716a8e: the worker database is created only by '
                                            'adapter.py:133-136 _worker, reached only from release, encrypt_record and finish_decryption '
                                            '(adapter.py:179-190); prepare_request is pure; collect_checkpoint, collect_decision and '
                                            'attest_grant use Witness only (adapter.py:153-176); the deviating witness takes no state '
                                            'directory. SL4 performs none of the three worker operations, so the D2 worker must be a '
                                            'verified never-instantiated record (D49), re-observed at baseline and after every catalog step; '
                                            'any instantiation fails the row'),
                        snapshots=('native views/logs per chain at one explicit block per read group; Cast hash checkpoint per read '
                                   'group/submit (A1-0061 D-5b); verified never-instantiated worker record (D49)')),
                    classification=('receipt-binding-control: REPAIR_SUPPORTED with WRONG_SUBJECT(2) (A40 deliberate witness deviation, '
                                    'defence in depth outside the honest-witness assumption); receipt-signature-control: SUPPORTED with '
                                    'WRONG_SUBJECT(2); receipt-binding-positive: SUPPORTED (ACCEPT); tested reconstruction results, never '
                                    'an HMBC exploit or authors-implementation claim'),
                    timing=('request, checkpoint, decision and consume strictly before request/decision expiry; attest and report '
                            'may follow grant expiry (late reconciliation allowed, recorded); no TTL change'),
                    limitations=['Solo-phase plan: both exact solo ACKs (A1 and S2) and the committed S3 FREEZE precede services.',
                                 'Seven of the 28 remaining catalog comparisons; no complete matrix, live mutants/window/report/gate.',
                                 'MUT_NO_RECEIPT_BINDING counterparts are P3 mutant work, not run here.',
                                 'A receipt attests DBC authorization only, not release or delivery; delivery unknown.',
                                 'Symbolic adapter; safe-ledger/trusted-worker/one trusted witness.'])
        plan.pop('workerExpected')
    if trust_stress:
        rows = [(p, v) for v in e1.TRUST_VARIANTS for p in e1.PROFILES]
        entries = plan['owners']['ledger']['entries']
        require(entries.get(SIGN_LIST_PATH) == SIGN_LIST_SHA256 and entries.get(SIGN_SCRIPT_PATH) == SIGN_SCRIPT_SHA256,
                'signed-list producer is the A1-0034 owner inventory entry')
        plan.update(schemaVersion='hmbc-e2-trust-stress-plan/v1', trustStress=True,
                    executionScope='six fresh E02 trust-freshness comparisons (SL5); not full RQ matrix',
                    matrix=[dict(profile=profile, point=None, variant=variant) for profile, variant in rows],
                    caseIds=['E02-'+variant+'-'+profile for profile, variant in rows],
                    controls=['wrong-admin-before-H2', 'registered-Alice-allow-release-one-outcome', 'registered-Bob-policy-deny',
                              'fresh-second-deployment-trust-stress'],
                    restart='none; production adapter only, no crash hook',
                    freshness=('fresh chain pair per matrix row; controls on deployment D1; the trust row on a fresh second deployment D2 '
                               'on the same chain pair with its own bootstrap, adapter process and 0700 state; relay/CA-admin balances '
                               'reset to 1000 ETH before D2'),
                    observation=('owner signed-list producer output, CA-admin and relay public calls, eth_call simulation, production '
                                 'prepare_request; TMSC anchors/authEpoch/revocation/credentials and whole decoded two-chain histories; '
                                 'worker never-instantiated record'),
                    trustProbe=dict(
                        wrongIssuer=('WRONG_ISSUER_UPDATE: the producer signs a fresh next-version H2 CRL (no revocations) with the H2 '
                                     'root; eth_call of updateRevocationList from the H2 CA-admin (never mined) must return the next '
                                     'generation; the H1 CA-admin then submits the same list -> mined Rejected UNAUTHORIZED_CALLER(16) at '
                                     'TMSC.sol:181 in every profile, nothing changed; baseline caller restriction (D-record N-1), not a '
                                     'repair; credited only through this row (A1-0061), not through the bootstrap wrong-admin control'),
                        signedListRollback=('INSTALL_NEW_LIST > REPLAY_OLD_LIST > REQUEST_ACCESS: the producer signs H1 CRL v2 revoking '
                                            'Alice certificate serial 101; the H1 CA-admin installs it (Alice REVOKED(19)); the H1 CA-admin '
                                            'resubmits the bootstrap H1 CRL v1 byte-for-byte, still valid; Alice then requests access '
                                            'with the current authEpoch read just before the request (A1-0064; repaired PSC refuses a '
                                            'mismatch). Paper: replay accepted (latest appended list current), Alice forwarded with '
                                            'anchorVersion 1 (ACCEPT/SPEC_GAP). Repaired-e: replay mined Rejected STALE_ANCHOR(5) at '
                                            'TMSC.sol:190, v2 retained, Alice AccessDenied REVOKED(19) (REJECT/REPAIR_SUPPORTED)'),
                        signList=dict(
                            script=SIGN_LIST_PATH, scriptSha256=SIGN_LIST_SHA256, forgeScript=SIGN_SCRIPT_PATH,
                            forgeScriptSha256=SIGN_SCRIPT_SHA256, invocations=copy.deepcopy(e1.SIGN_LIST_TEMPLATES),
                            cwd='materialized ledger snapshot root',
                            conditions=[
                                'Owner TEST-ONLY producer (A1-0034), confirmed for SL5 in A1-0061 D-6; read-only, it sends no transaction '
                                'and never writes keys to outputs.',
                                'Exact pinned bytes (sign_list.sh and SignList.s.sol) re-hashed before every call; argv built only from '
                                'the per-variant template; default next version, never --version.',
                                '--deployment is the same deployment file (byte-identical) the stress adapter was pinned with.',
                                'Any non-zero exit is a failed trial: no retry, no submission; published only as output sha256 and '
                                'first line.',
                                'Before use: schema hmbc-ledger-signed-list/v0, testOnly true, binding to this chain/TMSC/RSC/deployment '
                                'sha256/profile, the planned authority and revocations, the next on-chain version, and the root '
                                'signature recovered under the evaluator own EIP-712 encoder (HMBCTrust, PBC TMSC).']),
                        workerPrecondition=('re-checked for SL5: the only adapter operation is prepare_request (pure, adapter.py:79-104 '
                                            'at 0716a8e); trust updates are CA-admin chain transactions and the producer is a ledger '
                                            'owner command with no adapter state. SL5 performs no worker operation, so the D2 worker '
                                            'must be a verified never-instantiated record (D49), re-observed at baseline and after every '
                                            'catalog step; any instantiation fails the row'),
                        snapshots=('TMSC revocationListState (H1, H2), authEpoch, isRevoked(H1, 101), checkCredentials(Alice) and '
                                   'decoded PBC/DBC histories at one explicit block per read group; Cast hash checkpoint per read '
                                   'group/submit (A1-0061 D-5b); verified never-instantiated worker record (D49)')),
                    classification=('wrong-issuer: SUPPORTED with UNAUTHORIZED_CALLER(16) in every profile (baseline caller restriction); '
                                    'signed-list rollback: paper SPEC_GAP (ACCEPT), repaired-e REPAIR_SUPPORTED with STALE_ANCHOR(5); '
                                    'authorized issuer-scoped administrator actions; tested reconstruction results, never an HMBC '
                                    'exploit or authors-implementation claim'),
                    timing=('no request lifetime binds the trust steps; the request is prepared and submitted with the authEpoch read '
                            'immediately before it; list validity one day from the producer timestamp; unexpected expiry fails visibly'),
                    limitations=['Solo-phase plan: both exact solo ACKs (A1 and S2) and the committed S3 FREEZE precede services.',
                                 'Six of the 21 remaining catalog comparisons; no complete matrix, live mutants/window/report/gate.',
                                 'CRL only: the catalog allows CRL/TempACL; TempACL rollback is not exercised (explicit choice).',
                                 'MUT_NO_VERSION_MONOTONE counterpart is P3 mutant work, not run here.',
                                 'Symbolic adapter; safe-ledger/trusted-worker/one trusted witness.'])
        plan.pop('workerExpected')
    if barrier_stress:
        rows = [(p, v) for v in e1.BARRIER_VARIANTS for p in e1.PROFILES]
        entries = plan['owners']['ledger']['entries']
        require(entries.get(SIGN_LIST_PATH) == SIGN_LIST_SHA256 and entries.get(SIGN_SCRIPT_PATH) == SIGN_SCRIPT_SHA256,
                'signed-list producer is the A1-0034 owner inventory entry')
        plan.update(schemaVersion='hmbc-e2-barrier-stress-plan/v1', barrierStress=True,
                    executionScope='nine fresh E02 revocation-barrier and expired-duty comparisons (SL6); not full RQ matrix',
                    matrix=[dict(profile=profile, point=None, variant=variant) for profile, variant in rows],
                    caseIds=['E02-'+variant+'-'+profile for profile, variant in rows],
                    controls=['wrong-admin-before-H2', 'registered-Alice-allow-release-one-outcome', 'registered-Bob-policy-deny',
                              'fresh-second-deployment-barrier-stress'],
                    restart='none; production adapter only, no crash hook',
                    freshness=('fresh chain pair per matrix row; controls on deployment D1; the row on a fresh second deployment D2 on the '
                               'same chain pair with its own bootstrap, adapter process and 0700 state; relay/CA-admin balances reset to '
                               '1000 ETH before D2'),
                    observation=('owner signed-list producer output, CA-admin and relay public calls, production prepare_request, '
                                 'collect_checkpoint and collect_decision; DBC KSSC current checkpoint at consumption; PBC TMSC revocation, '
                                 'credentials and authEpoch; whole decoded two-chain histories; worker never-instantiated record'),
                    barrierProbe=dict(
                        certificateDiscipline=('repaired-e: the checkpoint and the ONE decision are collected after REQUEST_ACCESS and '
                                               'collected before the PBC update (catalog qualification; A1-0064); exactly one collect_decision '
                                               'per request in exchanges.json (A31 is runner discipline, S2-0007); never re-collected'),
                        preBarrier=('REQUEST_ACCESS > REVOKE_ON_PBC > FORWARD_OR_CONSUME, with REVOKE_ON_PBC before consume: the producer '
                                    'CRL v2 revoking Alice serial 101 is signed before the row (read-only) and installed by the H1 CA-admin '
                                    'at REVOKE_ON_PBC (Alice REVOKED(19) on the PBC, authEpoch + 1); no new checkpoint is accepted before '
                                    'consume, so the DBC checkpoint is unchanged (request authEpoch == checkpoint authEpoch) and the older '
                                    'certificate is accepted: the measured window is intentional, not instantaneous revocation '
                                    '(REPAIR_SUPPORTED); windowSeconds = consume - revocation block time'),
                        postBarrier=('repaired-e adds ACCEPT_CHECKPOINT after REVOKE_ON_PBC (collect_checkpoint + acceptState: sequence '
                                     '+ 1, new authEpoch) and then consumes the older certificate -> STALE_STATE(6) at DecisionVerifier '
                                     'step 10, line 87, required to be the sequence cause: the new checkpoint is current at consumption, '
                                     'decision stateSequence == old sequence != new sequence, decision expiresAt <= new checkpoint expiresAt, '
                                     'consume time < decision, request and new checkpoint expiresAt (steps 9 and 10a pass); no grant, nonce '
                                     'unchanged. Paper profiles have no checkpoint barrier: ACCEPT_CHECKPOINT is omitted'),
                        expiredDuty=('setup INSTALL_SHORT_DUTY: the producer signs an H1 TempACL v2 whose only entry is Alice OnDuty '
                                     '[t-60, t+untilIn] and the H1 CA-admin installs it before REQUEST_ACCESS; the PBC request is forwarded '
                                     'while the duty is valid; repaired-e collects the checkpoint and decision while the duty is valid '
                                     '(the witness attests DENY with empty records once a record validUntil <= DBC now, witness.py:133; '
                                     'decision expiresAt = min(request, checkpoint, DBC now + 30), not capped by records, witness.py:140); '
                                     'ADVANCE_CLOCK moves only the DBC (evm_setNextBlockTimestamp(max(latest+1, duty end)) + evm_mine); the '
                                     'PBC clock is not moved; then consume. Repaired-e: EXPIRED(7) required to be step 13: duty end <= '
                                     'consume time < min(decision, request, checkpoint expiresAt), so step 9 (line 74) and step 10a (line 85) '
                                     'pass; all four values and the consume block time are recorded'),
                        paperRows=('paper ACSC.policyEnf/evaluate (ACSC.sol:140-167) takes the relay records from the PBC forward event '
                                   'and has no record validUntil check and no checkpoint, so every paper row grants (TTL block + 30, '
                                   'recipient 0). Frozen classes are all SPEC_GAP; frozen outcomes are ACCEPT (pre-barrier) and '
                                   'CONDITIONAL (post-barrier, expired duty: acceptance depends on the configured relay forwarding '
                                   'request-time records); the observed outcome is a grant in all six'),
                        signList=dict(
                            script=SIGN_LIST_PATH, scriptSha256=SIGN_LIST_SHA256, forgeScript=SIGN_SCRIPT_PATH,
                            forgeScriptSha256=SIGN_SCRIPT_SHA256, invocations=copy.deepcopy(e1.BARRIER_SIGN_TEMPLATES),
                            untilInBounds=list(e1.UNTIL_IN_BOUNDS), cwd='materialized ledger snapshot root',
                            untilInRule=('untilIn = (PBC pending time - PBC latest block time) + 25, bounded 25..600 s: the producer '
                                         'signs at the latest block time t, so the duty ends about 25 s after now; that lies after the '
                                         'decision collection and before the request expiry (30 s after the request) and the witness '
                                         'decision TTL (DBC now + 30 s); the record validUntil on both chains is the TempACL entry end '
                                         '(repaired: min with the list validity of one day)'),
                            conditions=[
                                'Owner TEST-ONLY producer (A1-0034), confirmed in A1-0061 D-6; read-only; never writes keys to outputs.',
                                'Exact pinned bytes (sign_list.sh and SignList.s.sol) re-hashed before every call; argv only from the '
                                'per-purpose template; untilIn is the only computed argument and is bounded; never --version.',
                                '--deployment is the same deployment file (byte-identical) the stress adapter was pinned with.',
                                'Any non-zero exit is a failed trial: no retry; published only as output sha256 and first line.',
                                'Before use: schema, testOnly, binding to this chain/TMSC/RSC/deployment sha256/profile, the planned '
                                'authority and content, the next on-chain version, and the root signature under the evaluator own '
                                'EIP-712 encoder.']),
                        workerPrecondition=('re-checked for SL6: the adapter operations are prepare_request (pure) and collect_checkpoint '
                                            'and collect_decision (Witness only, adapter.py:153-170 at 0716a8e); trust updates are CA-admin '
                                            'transactions and the producer has no adapter state; release, encrypt_record and '
                                            'finish_decryption are never reached, so the D2 worker must be a verified never-instantiated '
                                            'record (D49), re-observed at baseline and after every catalog step; any instantiation fails the row'),
                        snapshots=('DBC grants/nonces/count/history and the current checkpoint, PBC request state and history at one explicit '
                                   'block per read group; PBC revocation/credentials/authEpoch around REVOKE_ON_PBC; Cast hash checkpoint '
                                   'per read group/submit (A1-0061 D-5b); verified never-instantiated worker record (D49)')),
                    classification=('pre-barrier: paper SPEC_GAP (ACCEPT), repaired-e REPAIR_SUPPORTED (intentional window); post-barrier: '
                                    'paper SPEC_GAP, repaired-e REPAIR_SUPPORTED with STALE_STATE(6); expired duty: paper SPEC_GAP, '
                                    'repaired-e REPAIR_SUPPORTED with EXPIRED(7); tested reconstruction results, never an HMBC exploit or '
                                    'authors-implementation claim'),
                    timing=('request, checkpoint, decision, revocation and consume inside the 30 s request lifetime; only the DBC clock '
                            'moves and only in the expired-duty rows; unexpected expiry fails visibly; no TTL change'),
                    limitations=['Solo-phase plan: both exact solo ACKs (A1 and S2) and the committed S3 FREEZE precede services.',
                                 'Nine of the 15 remaining catalog comparisons; no complete matrix, live mutants/window/report/gate.',
                                 'MUT_NO_STATE_BARRIER and MUT_NO_RECORD_FRESHNESS counterparts are P3 mutant work, not run here.',
                                 'The revocation window is measured per row, not characterized statistically (P3 revocation window).',
                                 'Symbolic adapter; safe-ledger/trusted-worker/one trusted witness.'])
        plan.pop('workerExpected')
    return plan


def verify_plan(plan):
    require(plan == create_plan(run_id=plan['runId'], freeze_message=plan['freezeMessage'],
                                expired_retry=plan.get('expiredRetry', False), duplicate_outcome=plan.get('duplicateOutcome', False),
                                nonce_replay=plan.get('nonceReplay', False), subject_substitution=plan.get('subjectSubstitution', False),
                                relay_stress=plan.get('relayStress', False), audit_stress=plan.get('auditStress', False),
                                receipt_stress=plan.get('receiptStress', False), trust_stress=plan.get('trustStress', False),
                                barrier_stress=plan.get('barrierStress', False), review_mode=plan.get('reviewMode', 'strict')),
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
        if plan.get('auditStress', False):
            record.update(executionMode='two-chain-e2-audit-stress-slice',
                          limitation='Six E03 audit-stress comparisons only; no complete catalog or RQ gate.')
        if plan.get('barrierStress', False):
            record.update(executionMode='two-chain-e2-barrier-stress-slice',
                          limitation='Nine E02 revocation-barrier and expired-duty comparisons only; no complete catalog or RQ gate.')
        if plan.get('trustStress', False):
            record.update(executionMode='two-chain-e2-trust-stress-slice',
                          limitation='Six E02 trust-freshness comparisons only; no complete catalog or RQ gate.')
        if plan.get('receiptStress', False):
            record.update(executionMode='two-chain-e2-receipt-stress-slice',
                          limitation='Seven repaired-e E03 receipt controls only; no complete catalog or RQ gate.')
        authorized = True; record['status'] = 'RUNNING'
        for item in plan['matrix']:
            verify_plan(plan)
            probe_name = 'nonce-replay' if plan.get('nonceReplay', False) else 'duplicate-outcome'
            if plan.get('subjectSubstitution', False): probe_name = 'subject-substitution'
            if any(plan.get(k, False) for k in ('relayStress', 'auditStress', 'trustStress', 'barrierStress')): probe_name = item['variant']
            if plan.get('receiptStress', False): probe_name = item['variant']+('-'+item['field'] if item['field'] else '')
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
            if plan.get('auditStress', False): probe_options = {'audit_stress': item['variant']}
            if plan.get('receiptStress', False): probe_options = {'receipt_stress': item['variant'], 'receipt_field': item['field']}
            if plan.get('trustStress', False): probe_options = {'trust_stress': item['variant']}
            if plan.get('barrierStress', False): probe_options = {'barrier_stress': item['variant']}
            e1._profile(selected, item['profile'], destination/item['profile'], child, recovery_point=item['point'],
                        expired_retry=plan.get('expiredRetry', False), **probe_options)
            if plan.get('barrierStress', False):
                proof = json.loads((destination/item['profile']/'barrier-stress/result.json').read_text())
                require(proof['ok'] is True and proof['delivery'] == 'unknown' and proof['variant'] == item['variant']
                        and (proof['classification'], proof['error']) == BARRIER_EXPECTED[(item['profile'], item['variant'])],
                        'complete checked barrier stress result')
            elif plan.get('trustStress', False):
                proof = json.loads((destination/item['profile']/'trust-stress/result.json').read_text())
                require(proof['ok'] is True and proof['delivery'] == 'unknown' and proof['variant'] == item['variant']
                        and (proof['classification'], proof['error']) == TRUST_EXPECTED[(item['profile'], item['variant'])],
                        'complete checked trust stress result')
            elif plan.get('receiptStress', False):
                proof = json.loads((destination/item['profile']/'receipt-stress/result.json').read_text())
                require(proof['ok'] is True and proof['delivery'] == 'unknown' and proof['variant'] == item['variant']
                        and proof['field'] == item['field'] and (proof['classification'], proof['error']) == RECEIPT_EXPECTED[item['variant']],
                        'complete checked receipt control result')
            elif plan.get('auditStress', False):
                proof = json.loads((destination/item['profile']/'audit-stress/result.json').read_text())
                require(proof['ok'] is True and proof['delivery'] == 'unknown' and proof['variant'] == item['variant']
                        and (proof['classification'], proof['error']) == AUDIT_EXPECTED[(item['profile'], item['variant'])],
                        'complete checked audit stress result')
            elif plan.get('relayStress', False):
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
            if plan.get('auditStress', False):
                record['cases'][case]['status'] = 'AUDIT_STRESS_CONTROL_PASS'
                continue
            if plan.get('receiptStress', False):
                record['cases'][case]['status'] = 'RECEIPT_STRESS_CONTROL_PASS'
                continue
            if plan.get('trustStress', False):
                record['cases'][case]['status'] = 'TRUST_STRESS_CONTROL_PASS'
                continue
            if plan.get('barrierStress', False):
                record['cases'][case]['status'] = 'BARRIER_STRESS_CONTROL_PASS'
                continue
            record['cases'][case]['status'] = ('NONCE_REPLAY_CONTROL_PASS' if plan.get('nonceReplay', False)
                                             else ('DUPLICATE_OUTCOME_CONTROL_PASS' if plan.get('duplicateOutcome', False) else 'RECOVERY_CONTROL_PASS'))
        verify_plan(plan); record.update(status='E2_DUPLICATE_OUTCOME_SLICE_PASS' if plan.get('duplicateOutcome', False) else ('E2_RECOVERY_EXPIRY_SLICE_PASS' if plan.get('expiredRetry', False) else 'E2_RECOVERY_SLICE_PASS'), sourceStable=True)
        if plan.get('nonceReplay', False): record['status'] = 'E2_NONCE_REPLAY_SLICE_PASS'
        if plan.get('subjectSubstitution', False): record['status'] = 'E2_SUBJECT_SUBSTITUTION_SLICE_PASS'
        if plan.get('relayStress', False): record['status'] = 'E2_RELAY_STRESS_SLICE_PASS'
        if plan.get('auditStress', False): record['status'] = 'E2_AUDIT_STRESS_SLICE_PASS'
        if plan.get('receiptStress', False): record['status'] = 'E2_RECEIPT_STRESS_SLICE_PASS'
        if plan.get('trustStress', False): record['status'] = 'E2_TRUST_STRESS_SLICE_PASS'
        if plan.get('barrierStress', False): record['status'] = 'E2_BARRIER_STRESS_SLICE_PASS'
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
                                     'E2_NONCE_REPLAY_SLICE_PASS', 'E2_SUBJECT_SUBSTITUTION_SLICE_PASS', 'E2_RELAY_STRESS_SLICE_PASS',
                                     'E2_AUDIT_STRESS_SLICE_PASS', 'E2_RECEIPT_STRESS_SLICE_PASS',
                                     'E2_TRUST_STRESS_SLICE_PASS', 'E2_BARRIER_STRESS_SLICE_PASS') else 2


if __name__ == '__main__': raise SystemExit(main())
