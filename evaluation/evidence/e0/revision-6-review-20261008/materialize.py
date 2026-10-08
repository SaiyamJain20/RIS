"""One-time exact E0 delta materialization, retained as a run record."""
import copy, csv, json
from pathlib import Path
root=Path('/home/karma/Documents/RIS')
path=root/'evaluation/scenarios/e0_cases.json'
catalog=json.loads(path.read_text())
catalog['status']='E0 candidate revision6 expectations for exact review; NOT E2 executor input or observed results'
catalog['registrationCondition']='Before adversarial schedules, trusted coordinator pre-registers synthetic worker payload/policy commitments and verifies ledger owner/policy; no registrant or payload authenticity claim (A41).'
for c in catalog['cases']:
    if c['variant']=='subject-substitution' and c['profile'].startswith('paper-'):
        c['expected']['qualification']='Compromised configured relay stress is outside paper secure isolation. Substitute only gid in the relay ForwardedRequest passed to policyEnf while keeping Alice\'s verified credential records. Paper profiles use no decision certificate. The DBC may authorize the substituted tuple; the grant gid is relay-asserted. With D35/A38 the symbolic response follows that gid\'s PBC-registered recipient key, not the original requester. An unregistered gid gets no release. This is a reconstruction/specification-gap comparison, not an HMBC exploit.'
        c['assumptions'].append('A38')
    if c['profile'].startswith('paper-') and any(s['action']=='RELEASE' for s in c['steps']):
        c['expected']['qualification']+=' D35/A38: paper response recipient is RSC.recipientKeyHash(grant.gid), while the native DBC grant recipient remains zero. Verify the registered key exists. Release and any pre-expiry retry must occur strictly before policyEnf DBC block timestamp + 30 seconds (A24); set injected DBC time explicitly and retain the block/expiry. A later receipt never extends release expiry. Current production owner still refuses paper grants; option-(c) spike evidence is not an integrated case result.'
        c['assumptions'].extend(['A24','A38'])
    c['assumptions'].append('A41')
    c['assumptions']=list(dict.fromkeys(c['assumptions']))
path.write_text(json.dumps(catalog,indent=2)+'\n')
nonce=copy.deepcopy(next(c for c in catalog['cases'] if c['id']=='E01-nonce-replay-repaired-e'))
nonce.update(id='E01-same-nonce-distinct-digests-repaired-e',variant='same-nonce-distinct-digests',
 assumptions=['A01','A02','A14','A19','A36','A39','A41'])
nonce['steps']=[dict(action=a,offsetSeconds='0') for a in ['REQUEST_ACCESS','REQUEST_SAME_NONCE_DISTINCT_DIGEST',
 'FORWARD_BOTH_REQUESTS','ACCEPT_CHECKPOINT','CERTIFY_BOTH_BEFORE_CONSUMPTION','CONSUME_FIRST','CONSUME_PRECOLLECTED_SECOND']]
nonce['expected']['qualification']='Fresh scenario: two valid user-signed Alice requests, same gid/nonce, distinct expiresAt within live 30-second bounds. Independently verify both signatures, distinct digests and derived grantIds. Forward both BEFORE ONE checkpoint covering both. Collect BOTH honest policy-aware ALLOW certificates BEFORE either consume; each sees nonceConsumed=false. Preserve that checkpoint, credentials and TTLs; consume first then the second PRE-COLLECTED certificate without re-collection. Native repaired-e: REPLAY, no second grant, first grant unchanged. MUT_NO_NONCE (8) counterpart: second distinct allowed grant; nonce never recorded. These are NOT_RUN expectations; A2 owner measurements are separate. No evaluator witness key.'
cases=[nonce]
base=copy.deepcopy(next(c for c in catalog['cases'] if c['id']=='E03-fabricated-outcome-repaired-e'))
for variant,action in [('receipt-binding-control','RESIGN_RECEIPT_FIELD'),('receipt-signature-control','ALTER_RECEIPT_KEEP_SIGNATURE')]:
    for field in ['requestDigest','gid','dataId']:
        c=copy.deepcopy(base)
        c.update(id=f'E03-{variant}-{field}-repaired-e',variant=variant,
            assumptions=['A01','A03','A12','A13','A36','A40','A41'])
        c['steps']=[dict(action=a,offsetSeconds='0') for a in ['REQUEST_ACCESS','FORWARD_OR_CONSUME','ATTEST_GRANT']]
        c['steps'] += [dict(action=action,offsetSeconds='0',receiptField=field),dict(action='REPORT_OUTCOME',offsetSeconds='0')]
        c['expected']=dict(property='audit-correspondence',outcome='NO_NEW_OUTCOME',
            classification='REPAIR_SUPPORTED' if variant=='receipt-binding-control' else 'SUPPORTED',error='WRONG_SUBJECT',
            qualification='Each trial/profile begins with its OWN fresh forwarded request, actual allowed grant and honest receipt; separate fresh requests for all three fields, the positive trial and every signature trial. Change ONLY receipt.'+field+'; keep outer requestDigest, grantId, destination, epochs/expiry/membership and all other fields. Native repaired-e rejects WRONG_SUBJECT, PBC remains FORWARDED, no outcome/log/status transition. '+
            ('Agent2 TEST-ONLY tool signs the inconsistent receipt at runtime using actual PSC/chain domain and real grant/expiry; returns artifact only. MUT_NO_RECEIPT_BINDING (32) counterpart ACCEPTS and becomes OUTCOME_RECORDED; retain inconsistent native fields. Deliberate witness-deviation/defense-in-depth control outside honest-witness assumption, not an HMBC attack.' if variant=='receipt-binding-control' else 'Retain original honest signature over the altered receipt; binding check precedes quorum in repaired-e. MUT_NO_RECEIPT_BINDING (32) reaches BAD_SIGNATURE and also rejects; this signature control cannot kill the binding mutant.')+' Receipts may reconcile after expiry without reauthorizing release. NOT_RUN; owner measurements are separate.')
        cases.append(c)
c=copy.deepcopy(base)
c.update(id='E03-receipt-binding-positive-repaired-e',variant='receipt-binding-positive',assumptions=['A01','A03','A12','A13','A36','A40','A41'])
c['steps']=[dict(action=a,offsetSeconds='0') for a in ['REQUEST_ACCESS','FORWARD_OR_CONSUME','ATTEST_GRANT','REPORT_OUTCOME']]
c['expected']=dict(property='audit-correspondence',outcome='ACCEPT',classification='SUPPORTED',error=None,
 qualification='Separate fresh forwarded-and-granted request in repaired-e AND receipt-binding mutant. Honest attest_grant receipt records one matching successful outcome; preserve native fields/status/log. This positive control prevents deny-all from passing. It attests authorization only, not release/delivery. Receipts may reconcile after expiry. NOT_RUN.')
cases.append(c)
(root/'evaluation/scenarios/e0_supplement_cases.json').write_text(json.dumps(dict(
 status='E0 revision6 supplement definitions for exact review; NOT_RUN, not an executor or result',
 scheduleSemantics='Ordered zero-delay directives with fresh scenario state per case/profile. FORWARD_OR_CONSUME includes legitimate public witness/consume path. ATTEST_GRANT calls public adapter. RESIGN_RECEIPT_FIELD invokes Agent2 testtools.deviating_witness outside adapter; ALTER_RECEIPT_KEEP_SIGNATURE uses the retained honest receipt. No witness keys in runner. Mutant counterparts are specified in qualification; execute only after E1 and exact service/freeze ACKs.',
 cases=cases),indent=2)+'\n')
rows=[
 ['A38','reconstruction choice','Paper-mode symbolic response recipient is PBC RSC.recipientKeyHash(grant.gid); zero registered key refuses release; native DBC grant recipient remains zero','HMBC III-D3 PDF p10; A1-0021; A2-0011; D35','Relay-asserted gid may differ from requester. Paper grant expiry is policyEnf DBC timestamp plus30s. No cryptographic encryption claim; production successor and exact delta ACK pending.'],
 ['A39','control choice','Same nonce guard tested using two distinct user-signed requests and both honest certificates collected before consumption under one checkpoint','A3-0016 supplement r2; A1-0020; A2-0010','Native REPLAY versus MUT_NO_NONCE second grant and absent nonce write. NOT_RUN evaluator schedule; owner measurements separate.'],
 ['A40','deliberate mutation','Receipt-binding control uses Agent2 test-only runtime signer over one inconsistent bound field; each trial uses a fresh forwarded granted request','A3-0016 supplement r2; A1-0020; A2-0010','Outside honest-witness assumption. Guarded WRONG_SUBJECT versus binding mutant ACCEPT; original-signature control reaches mutant BAD_SIGNATURE. No HMBC exploit claim.'],
 ['A41','experiment condition','Trusted coordinator pre-registers synthetic worker payload/policy commitments before adversarial schedules and checks ledger owner/policy','A3-0016 supplement r2; A1-0020; A2-0010','Worker first writer only; payloadDigest/ciphertextDigest not ledger authenticated. No registrant or payload authenticity conclusion.']]
with (root/'evaluation/evidence/assumptions.csv').open('a',newline='') as f:
    writer=csv.writer(f,lineterminator='\n');writer.writerows(rows)
