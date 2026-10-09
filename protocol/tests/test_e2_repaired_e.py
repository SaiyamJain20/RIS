"""E2 (agent 2): the 16 repaired-e cases of agent 3's pinned prospective catalog (candidate revision 5), executed live against agent 1's repaired-e ledger.

Provenance: paper-derived reconstruction; synthetic TEST-ONLY keys; no external services. Every expectation (`error`, `outcome`,
`classification`, and the closed `worker` record of the two crash cases) is read from protocol/tests/fixtures/e0-cases-a3-3e0300a.json
(SHA-256 pinned in e2_support) at run time, so a test cannot tune its expectation to what the ledger does. Each test performs the catalog's
ordered directives (checked against the catalog; a different schedule, step field, delay or unreviewed expected field raises StepScheduleError)
with agent 2's honest components; where a directive is adversarial the test plays the deviating relay with raw transactions.

A case whose catalog expectation differs from the observed behaviour is marked xfail(strict=True) with the exact observed result; the
expectation is never edited. Revision 5 has none (XFAILED is empty; the final test asserts that disagreements == XFAILED). OBSERVED (case id
-> record) and EXECUTED are in e2_support and the last test checks that every catalog id was concluded exactly once (run the whole module; a
`-k` subset fails that final test by design).

How the catalog's directives are realised (a choice of this executor, stated so it can be reviewed):
  REQUEST_ACCESS      the user signs; the honest relay forwards to the PBC; the witness checkpoint is accepted by the DBC; the witness's
                      decision (the "certificate") is collected NOW. Cases that stop at the PBC (rollback, fabricated outcome) omit the DBC part.
  FORWARD_OR_CONSUME  the (possibly deviating) relay submits request + certificate + records to ACSC.consumeDecision with a raw transaction.
  ADVANCE_CLOCK       the next DBC block is mined at an exact timestamp (evm_setNextBlockTimestamp), so "expiresAt exactly" is literal.
  SUBSTITUTE_SUBJECT  request.gid only (Alice -> Bob); the ORIGINAL certificate is presented unchanged (catalog qualification). Rewriting
                      decision.requestDigest as well is a separate control (supplement), which is where BAD_SIGNATURE arises.
  FABRICATE_TUPLE     the relay invents a request, credential records and decision for a subject (Mallory) who never asked the PBC (asserted:
                      no PSC record, no LSC log), built from the DBC's CURRENT checkpoint so every field matches; the decision is signed by a
                      NON-witness key. Control: the identical tuple signed with the witness key is accepted, so the signature alone is what
                      is rejected (this also shows the DBC verifies the witness quorum, not the existence of a PBC request).
  SUBSTITUTE_DESTINATION  the relay points the same signed material at another destination: destinationChainId, kssc, and both (three variants),
                      with the user's signature and the witness certificate untouched (agent 1's DecisionBinding field-substitution
                      realisation). A supplement adds the request-for-another-destination-certified-here variant.
  REPLAY_NEW_REFERENCE  in repaired-e the reference IS the digest of the user-signed request, so a fresh reference needs a freshly signed
                      request, which the catalog excludes. The relay can only reuse the original signed gid/nonce/certificate: (1) resubmit
                      them to the ACSC, (2) ask the honest witness for another certificate for the same request. Both must end in REPLAY. The
                      freshly-signed-same-nonce variant is a supplement (nonce reuse under a new digest).
  RELEASE / CRASH_RESTART / REPORT_OUTCOME  agent 2's durable Worker. The fault hook is the one the catalog's CRASH_RESTART names (crashPoint),
                      armed BEFORE the immediately preceding RELEASE (scheduleSemantics); a new Worker on the same state directory retries before
                      the grant expires; the honest relay reports the witness's GrantReceipt. A second grant, crashed the same way and retried
                      only after its expiry, yields expiredRetryError and shows that the expired retry emits no worker event and no new token.
                      The observed worker record has exactly the catalog's fields and is compared with equality.
"""
import pytest
from eth_utils import keccak

from hmbc_protocol import chain, eip712, keys, messages
from hmbc_protocol.client import UserClient
from hmbc_protocol.worker import SimulatedCrash, Worker
from hmbc_protocol import ledger as ledger_mod
import ledger_setup as setup
import e2_support as e2
from e2_support import Case, Flow, Obs, check_error, db_rows, grant_id_of, observe, pbc_code, request_digest, revert, snapshot

OBSERVED = e2.OBSERVED
XFAILED: set[str] = set()                                         # cases marked xfail(strict) with their observed result: none in revision 5
OUTCOME = "0x" + "ab" * 32
P1_POLICY = {"clauses": [[{"role": setup.ROLE_DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": setup.ROLE_ON_DUTY, "kind": "2", "issuerMode": "2"}]]}
H2_ROOT = setup.addr("H2-root")                                                              # data owner in the fixture
P1_RECORD = {"dataId": setup.DATA_P1, "owner": H2_ROOT, "payloadDigest": "0x" + keccak(text="synthetic payload P1").hex()}


def agree(*obs: Obs) -> str | None:
    """One error name if every attempt observed the same one; otherwise a MIXED marker (which can never equal a catalog code)."""
    errs = [o.error for o in obs]
    return errs[0] if len(set(errs)) == 1 else "MIXED:" + "/".join(str(e) for e in errs)


def worker(led, state_dir, **kw) -> Worker:
    return Worker(led, state_dir, clock=led.dbc.now, **kw)


# =================================================================================================================================
# E01  decision provenance
# =================================================================================================================================

def test_E01_subject_substitution(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E01-subject-substitution-repaired-e")
    case.step("REQUEST_ACCESS")
    signed, d = f.certified()                                        # user signs; PBC forwards; DBC checkpoint; witness certificate
    case.step("SUBSTITUTE_SUBJECT")
    bob = setup.addr("bob")
    forged = {**signed["request"], "gid": bob}                       # the relay swaps the subject, keeps everything else
    forged_digest = request_digest(led, forged)
    assert forged_digest != signed["requestDigest"]
    case.step("FORWARD_OR_CONSUME")
    before = (f.probe(signed["requestDigest"], "1"), f.probe(forged_digest, "1", bob))
    obs = observe(f.consume_raw, forged, d)                          # forged request + the original certificate
    after = (f.probe(signed["requestDigest"], "1"), f.probe(forged_digest, "1", bob))
    genuine = f.relay.deliver(signed, d)                             # control: the untouched request and certificate still work
    assert genuine is not None
    case.finish(obs.error, "REJECT" if obs.error is not None and before == after else "ACCEPT",
                stateUnchangedByRejection=before == after, genuineStillConsumes=True)


def test_E01_nonce_replay(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E01-nonce-replay-repaired-e")
    case.step("REQUEST_ACCESS")
    signed, d = f.certified()
    case.step("FORWARD_OR_CONSUME")
    grant_id = f.relay.deliver(signed, d)
    assert grant_id is not None and led.dbc.call(led.KSSC, "nonceConsumed", ctx.alice, "1") is True
    case.step("REPLAY_REQUEST")                                       # the IDENTICAL accepted request, both legs
    grant_before = led.dbc.call(led.KSSC, "grantDetails", grant_id)
    before = f.probe(signed["requestDigest"], "1")
    pbc = pbc_code(f.forward(signed))                                 # PBC leg: AccessDenied event, not a revert
    dbc = observe(f.consume_raw, signed["request"], d)                # DBC leg: identical request + identical certificate
    after = f.probe(signed["requestDigest"], "1")
    no_new_grant = led.dbc.call(led.KSSC, "grantDetails", grant_id) == grant_before and before == after
    case.finish(agree(pbc, dbc), "NO_NEW_GRANT" if no_new_grant and pbc.error and dbc.error else "NEW_GRANT",
                pbcLeg=pbc.error, dbcLeg=dbc.error)


def test_E01_expiry_boundary(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E01-expiry-boundary-repaired-e")
    case.step("REQUEST_ACCESS")
    signed, d = f.certified()
    expiry = min(int(signed["request"]["expiresAt"]), int(d["decision"]["expiresAt"]))     # the earlier of the two checks (now >= x rejects)
    case.step("ADVANCE_CLOCK")                                        # controlled DBC clock: the next block is mined at an exact second
    snap = snapshot(led.dbc)                                          # boundary control: one second BEFORE the boundary the same bytes grant
    ok = f.consume_at(signed["request"], d, expiry - 1)
    assert led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, signed["requestDigest"]))[5] is True and int(ok["status"], 16) == 1
    revert(led.dbc, snap)
    case.step("FORWARD_OR_CONSUME")
    before = f.probe(signed["requestDigest"], "1")
    obs = observe(f.consume_at, signed["request"], d, expiry)         # block.timestamp == expiresAt exactly
    after = f.probe(signed["requestDigest"], "1")
    case.finish(obs.error, "REJECT" if obs.error is not None and before == after else "ACCEPT", boundary=expiry,
                requestExpiresAt=signed["request"]["expiresAt"], decisionExpiresAt=d["decision"]["expiresAt"],
                acceptedAtBoundaryMinusOne=True)


def test_E01_forged_tuple(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E01-forged-tuple-repaired-e")
    case.step("FABRICATE_TUPLE")                                      # a request, records and decision for a subject who never asked the PBC
    f.accept_checkpoint()                                             # ambient honest DBC state: a live checkpoint, which concerns no request
    mallory = setup.addr("mallory")
    request = {**f.client.build_request(data_id=setup.DATA_P1, nonce="77", expires_at=str(led.pbc.now() + 30),
                                        auth_epoch=led.pbc.call(led.TMSC, "authEpoch")),
               "gid": mallory, "recipientKeyHash": "0x" + keccak(text="HMBC.recipient-key.mallory").hex()}
    until = str(led.pbc.now() + 86400)
    records = [{"issuer": ctx.h1, "role": setup.ROLE_DOCTOR, "kind": "1", "serial": "999", "anchorVersion": "1", "validUntil": until},
               {"issuer": ctx.h1, "role": setup.ROLE_ON_DUTY, "kind": "2", "serial": "0", "anchorVersion": "1", "validUntil": until}]
    forged = f.decision_for(request, records, signer="mallory")      # every field matches; only the signer is not a witness
    digest = request_digest(led, request)
    assert led.pbc.call(led.PSC, "getRequest", digest)["status"] == "0" and led.pbc.call(led.LSC, "firstRequestLogId", digest) == "0"   # no PBC request, no PBC log
    case.step("FORWARD_OR_CONSUME")
    before = f.probe(digest, "77", mallory)
    obs = observe(f.consume_raw, request, forged)
    after = f.probe(digest, "77", mallory)
    # control: the SAME tuple signed with the witness key is accepted, so the signature alone caused the rejection. That is a compromised witness,
    # which E's single trusted witness does not defend against: the DBC verifies the witness quorum, not the existence of a PBC request.
    snap = snapshot(led.dbc)
    f.consume_raw(request, f.decision_for(request, records, signer="witness-1"))
    control_grants = led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, digest))[5] is True
    revert(led.dbc, snap)
    assert control_grants, "the witness-signed control was refused, so the forged tuple was not 'otherwise matching' and BAD_SIGNATURE proves nothing"
    case.finish(obs.error, "REJECT" if obs.error is not None and before == after and after["grant"][5] is False else "ACCEPT",
                stateUnchanged=before == after, noPbcRequestOrLog=True, sameTupleWitnessSignedIsAccepted=control_grants)


def test_E01_wrong_destination(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E01-wrong-destination-repaired-e")
    case.step("REQUEST_ACCESS")
    signed, d = f.certified()
    case.step("SUBSTITUTE_DESTINATION")                               # the relay points the SAME signed material at another destination
    mallory = setup.addr("mallory")
    variants = {"otherChain": {**signed["request"], "destinationChainId": "38545"},
                "otherKssc": {**signed["request"], "kssc": mallory},
                "otherChainAndKssc": {**signed["request"], "destinationChainId": "38545", "kssc": mallory}}
    assert all(request_digest(led, v) != signed["requestDigest"] for v in variants.values())
    case.step("FORWARD_OR_CONSUME")                                   # nothing signed is rewritten: same user signature, same witness certificate
    before = f.probe(signed["requestDigest"], "1")
    obs = {name: observe(f.consume_raw, v, d) for name, v in variants.items()}
    after = f.probe(signed["requestDigest"], "1")
    assert f.relay.deliver(signed, d) is not None                     # control: the unsubstituted request still consumes here
    case.finish(agree(*obs.values()), "REJECT" if all(o.error for o in obs.values()) and before == after else "ACCEPT",
                variants={k: o.error for k, o in obs.items()}, stateUnchanged=before == after, genuineStillConsumes=True)


def test_E01_new_reference_replay(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E01-new-reference-replay-repaired-e")
    case.step("REQUEST_ACCESS")
    signed, d = f.certified()
    case.step("FORWARD_OR_CONSUME")
    grant_id = f.relay.deliver(signed, d)
    assert grant_id is not None
    case.step("REPLAY_NEW_REFERENCE")
    # In repaired-e the reference IS the digest of the user-signed request, so the relay cannot mint a fresh one without a freshly signed
    # request (excluded by the catalog). It can only reuse the original signed gid/nonce/certificate, by two routes:
    grant_before = led.dbc.call(led.KSSC, "grantDetails", grant_id)
    before = f.probe(signed["requestDigest"], "1")
    resubmit = observe(f.consume_raw, signed["request"], d)           # (1) the original request + certificate again, straight to the ACSC
    second_certificate = observe(f.decide, signed)                    # (2) ask the honest witness for another certificate for the same signed request
    after = f.probe(signed["requestDigest"], "1")
    no_new = led.dbc.call(led.KSSC, "grantDetails", grant_id) == grant_before and before == after
    case.finish(agree(resubmit, second_certificate), "NO_NEW_GRANT" if no_new and resubmit.error and second_certificate.error else "NEW_GRANT",
                resubmitOriginal=resubmit.error, secondCertificateFromWitness=second_certificate.error, stateUnchanged=before == after)


# =================================================================================================================================
# E02  trust freshness
# =================================================================================================================================

def test_E02_signed_list_rollback(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E02-signed-list-rollback-repaired-e")
    case.step("INSTALL_NEW_LIST")
    f.install_acl({**ctx.acl, "version": "2", "entries": []})        # TempACL v2: Alice removed from duty
    f.install_crl({**ctx.crl1, "version": "2", "revokedSerials": ["101"]})   # CRL v2: Alice's certificate (serial 101) revoked
    acl_head, crl_head, epoch = led.pbc.call(led.TMSC, "temporalAclState", ctx.h1), led.pbc.call(led.TMSC, "revocationListState", ctx.h1), led.pbc.call(led.TMSC, "authEpoch")
    assert (acl_head["version"], crl_head["version"], epoch) == ("2", "2", "5")
    case.step("REPLAY_OLD_LIST")                                      # an authorised H1 administrator resubmits the correctly signed v1 lists
    obs_acl = observe(f.install_acl, ctx.acl)
    obs_crl = observe(f.install_crl, ctx.crl1)
    retained = (led.pbc.call(led.TMSC, "temporalAclState", ctx.h1) == acl_head and led.pbc.call(led.TMSC, "revocationListState", ctx.h1) == crl_head
                and led.pbc.call(led.TMSC, "authEpoch") == epoch and led.pbc.call(led.TMSC, "isRevoked", ctx.h1, "101") is True
                and led.pbc.call(led.TMSC, "temporalWindow", ctx.h1, ctx.alice, setup.ROLE_ON_DUTY)["present"] is False)
    case.step("REQUEST_ACCESS")                                       # derived check ("retain v2"): Alice is still revoked on the PBC
    after = f.forward(f.sign(nonce="9"))
    assert after.code == "REVOKED", f"a rolled-back list would have let Alice through; PBC said {after.code}"
    case.finish(agree(obs_acl, obs_crl), "REJECT" if retained and obs_acl.error and obs_crl.error else "ACCEPT",
                aclReplay=obs_acl.error, crlReplay=obs_crl.error, v2Retained=retained, requestAfterReplay=after.code)


def test_E02_wrong_issuer(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E02-wrong-issuer-repaired-e")
    t = led.pbc.get_block()["timestamp"]
    bob = setup.addr("bob")
    h2_acl = {"authority": ctx.h2, "version": "1", "validUntil": str(t + 86400),
              "entries": [{"gid": bob, "role": setup.ROLE_ON_DUTY, "validFrom": str(t - 60), "validUntil": str(t + 3600)}]}
    h2_crl = {"authority": ctx.h2, "version": "2", "validUntil": str(t + 86400), "revokedSerials": []}
    snap = lambda: (led.pbc.call(led.TMSC, "temporalAclState", ctx.h2), led.pbc.call(led.TMSC, "revocationListState", ctx.h2), led.pbc.call(led.TMSC, "authEpoch"))   # noqa: E731
    before = snap()
    case.step("WRONG_ISSUER_UPDATE")                                  # H1's CA admin submits H2 lists carrying H2's GENUINE root signature
    obs_acl = observe(f.install_acl, h2_acl, admin="H1-ca-admin", root="H2-root")
    obs_crl = observe(f.install_crl, h2_crl, admin="H1-ca-admin", root="H2-root")
    unchanged = snap() == before
    f.install_acl(h2_acl, admin="H2-ca-admin", root="H2-root")        # control: H2's own admin may publish the very same list
    assert led.pbc.call(led.TMSC, "temporalWindow", ctx.h2, bob, setup.ROLE_ON_DUTY)["present"] is True
    case.finish(agree(obs_acl, obs_crl), "REJECT" if unchanged and obs_acl.error and obs_crl.error else "ACCEPT",
                aclUpdate=obs_acl.error, crlUpdate=obs_crl.error, h2StateUnchanged=unchanged, ownAdminAccepted=True)


def test_E02_pre_barrier_revocation(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E02-pre-barrier-revocation-repaired-e")
    case.step("REQUEST_ACCESS")                                       # request, PBC forward, checkpoint 1 accepted, certificate collected NOW
    signed, d = f.certified()
    assert (d["decision"]["result"], d["decision"]["stateSequence"]) == ("1", "1")
    case.step("REVOKE_ON_PBC")                                        # new TempACL without Alice: authEpoch 3 -> 4; no new checkpoint reaches the DBC
    rc = f.revoke_alice_on_duty()
    revoked_at = led.pbc.get_block(int(rc["blockNumber"], 16))["timestamp"]
    assert led.pbc.call(led.TMSC, "authEpoch") == "4"
    assert led.pbc.call(led.TMSC, "temporalWindow", ctx.h1, ctx.alice, setup.ROLE_ON_DUTY)["present"] is False
    exists, cp = led.dbc.call(led.KSSC, "currentCheckpoint")
    assert exists and (cp["sequence"], cp["authEpoch"]) == ("1", "3"), "the DBC must not have learned the revocation yet"
    snap = snapshot(led.dbc)
    case.step("FORWARD_OR_CONSUME")                                   # the SAME certificate, not re-collected
    obs = observe(f.consume_raw, signed["request"], d)
    allowed = led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, signed["requestDigest"]))
    consumed_at = led.dbc.get_block()["timestamp"]
    # measurement: the window is real but bounded by the earliest of request / decision / checkpoint expiry (never open-ended)
    bound = min(int(signed["request"]["expiresAt"]), int(d["decision"]["expiresAt"]), int(cp["expiresAt"]))
    revert(led.dbc, snap)
    snap2 = snapshot(led.dbc)                                         # the window's far end: last second still accepted, first second refused
    f.consume_at(signed["request"], d, bound - 1)
    last_accepted = led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, signed["requestDigest"]))[5]
    revert(led.dbc, snap2)
    late = observe(f.consume_at, signed["request"], d, bound)
    # the PBC itself already denies a NEW request for Alice: the lag is only the DBC's, not the PBC's
    new_request = f.forward(f.sign(nonce="2"))
    case.finish(obs.error, "ACCEPT" if obs.error is None and allowed[5] is True else "REJECT",
                revocationPbcTimestamp=revoked_at, consumedDbcTimestamp=consumed_at, immediateConsumeDelaySeconds=consumed_at - revoked_at,
                firstRefusedTimestamp=bound, lastAcceptedAfterRevocationSeconds=(bound - 1) - revoked_at, lastSecondAccepted=last_accepted,
                afterWindowConsume=late.error, newRequestOnPbc=new_request.code,
                note="PBC and DBC are separate Anvil clocks; second-level differences between them are indicative only")
    assert last_accepted is True and late.error == "EXPIRED" and new_request.code == "REVOKED"


def test_E02_post_barrier_revocation(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E02-post-barrier-revocation-repaired-e")
    case.step("REQUEST_ACCESS")
    signed, d = f.certified()
    case.step("REVOKE_ON_PBC")
    f.revoke_alice_on_duty()
    case.step("ACCEPT_CHECKPOINT")                                    # the DBC accepts a checkpoint carrying the new authEpoch
    cp2 = f.accept_checkpoint()
    assert (cp2["checkpoint"]["sequence"], cp2["checkpoint"]["authEpoch"]) == ("2", "4")
    case.step("FORWARD_OR_CONSUME")                                   # the OLD certificate is consumed without re-collection
    before = f.probe(signed["requestDigest"], "1")
    obs = observe(f.consume_raw, signed["request"], d)
    after = f.probe(signed["requestDigest"], "1")
    refused = observe(f.decide, signed)                               # an honest witness will not mint a replacement for the stale request
    case.finish(obs.error, "REJECT" if obs.error is not None and before == after and after["grant"][5] is False and after["nonceConsumed"] is False else "ACCEPT",
                noGrantNoNonceNoLog=before == after, witnessRecollection=refused.error)
    assert refused.error == "STALE_STATE"


def test_E02_expired_duty(ledger):
    duty_seconds = 27                                                 # request TTL is 30 s, so the duty entry must end inside that
    led = ledger_mod.Ledger.from_deployment(ledger.deployment)
    ctx = setup.setup_pbc(led, duty_seconds=duty_seconds)             # Alice's OnDuty entry ends duty_seconds after PBC setup
    f, case = Flow(led, ctx), Case("E02-expired-duty-repaired-e")
    case.step("REQUEST_ACCESS")                                       # forwarded and certified ALLOW while the duty entry is still valid
    signed, d = f.certified(ttl=30)
    duty_end = int(ctx.acl["entries"][0]["validUntil"])
    elapsed = led.dbc.get_block()["timestamp"] - (duty_end - duty_seconds)
    if elapsed >= duty_seconds - 3:
        raise e2.ClockPreconditionError(f"setup+request+checkpoint+decision took {elapsed}s of the {duty_seconds}s duty entry: environment too slow")
    cp_expiry = int(led.dbc.call(led.KSSC, "currentCheckpoint")[1]["expiresAt"])
    assert d["decision"]["result"] == "1" and [r["role"] for r in d["credentialRecords"]] == [setup.ROLE_DOCTOR, setup.ROLE_ON_DUTY]
    assert duty_end < min(int(signed["request"]["expiresAt"]), int(d["decision"]["expiresAt"]), cp_expiry), "request/decision/checkpoint must outlive the duty entry"
    case.step("ADVANCE_CLOCK")                                        # DBC clock to the duty boundary
    snap = snapshot(led.dbc)                                          # control: one second earlier the same bytes grant
    f.consume_at(signed["request"], d, duty_end - 1)
    assert led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, signed["requestDigest"]))[5] is True
    revert(led.dbc, snap)
    case.step("FORWARD_OR_CONSUME")
    before = f.probe(signed["requestDigest"], "1")
    obs = observe(f.consume_at, signed["request"], d, duty_end)
    after = f.probe(signed["requestDigest"], "1")
    case.finish(obs.error, "REJECT" if obs.error is not None and before == after else "ACCEPT", dutyEnd=duty_end, secondsUsedBeforeBoundary=elapsed,
                requestExpiresAt=signed["request"]["expiresAt"], decisionExpiresAt=d["decision"]["expiresAt"], checkpointExpiresAt=str(cp_expiry))


# =================================================================================================================================
# E03  audit correspondence
# =================================================================================================================================

def test_E03_dropped_outcome(world, tmp_path):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E03-dropped-outcome-repaired-e")
    case.step("REQUEST_ACCESS")
    case.step("FORWARD_OR_CONSUME")
    signed, d, grant_id = f.granted()
    case.step("RELEASE")
    w = worker(led, tmp_path / "state")
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    delivered = []
    w.release(grant_id, transmit=delivered.append)
    case.step("DROP_OUTCOME")                                         # the relay obtains the receipt and never reports it
    receipt = f.witness.attest_grant(grant_id)
    probe = f.probe(signed["requestDigest"], "1")
    local = [e["type"] for e in w.events()]
    assert local == ["RELEASE_INTENT", "RELEASE_SENT"] and len(delivered) == 1       # durable local logs exist...
    pending = probe["pscStatus"] == "1" and probe["outcomeLogId"] == "0"             # ...yet the PBC still has no outcome
    # reconciliation requires eventual delivery: the withheld receipt still records the outcome later (after the grant expired)
    setup.advance(led, 40)
    f.relay.report_outcome(signed["requestDigest"], OUTCOME, receipt)
    reconciled = f.probe(signed["requestDigest"], "1")
    assert reconciled["pscStatus"] == "2" and reconciled["outcomeLogId"] != "0"
    case.finish(None, "PENDING" if pending else "RECORDED", localEvents=local, pscStatusWhileDropped=probe["pscStatus"],
                reconciledAfterEventualDelivery=True)


def test_E03_fabricated_outcome(world):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E03-fabricated-outcome-repaired-e")
    case.step("REQUEST_ACCESS")
    signed = f.request()                                              # forwarded by the PBC; the DBC never saw it, so no grant exists
    digest, gid = signed["requestDigest"], grant_id_of(led, signed["requestDigest"])
    assert led.dbc.call(led.KSSC, "getGrant", gid)[5] is False
    case.step("FABRICATE_OUTCOME")
    before = f.probe(digest, "1")
    unattested = observe(led.pbc.send, f.relay_key, led.PSC, "reportOutcome", digest, gid, OUTCOME)     # the paper path, called by the configured relay
    forged = {"requestDigest": digest, "grantId": gid, "gid": ctx.alice, "dataId": setup.DATA_P1, "keyEpoch": "0",
              "grantExpiresAt": signed["request"]["expiresAt"], "witnessSetVersion": "1", "dbcChainId": str(led.dbc.chain_id),
              "kssc": led.KSSC.address, "dbcBlockNumber": "1", "dbcBlockHash": "0x" + "00" * 32}
    forged_sig = eip712.sign_digest(setup.key("mallory"), messages.digest_of("GrantReceipt", forged, messages.domain_for("GrantReceipt", forged, led.deployment)))
    attested = observe(led.pbc.send, f.relay_key, led.PSC, "reportAttestedOutcome", digest, OUTCOME, forged, [forged_sig])
    witness = observe(f.witness.attest_grant, gid)                    # the honest witness has no DBC grant to attest
    after = f.probe(digest, "1")
    case.finish(unattested.error, "REJECT" if before == after and after["pscStatus"] == "1" and after["outcomeLogId"] == "0" else "ACCEPT",
                unattestedPath=unattested.error, forgedReceipt=attested.error, honestWitness=witness.error)
    assert (attested.error, witness.error) == ("BAD_SIGNATURE", "NOT_COMMITTED")


def test_E03_duplicate_outcome(world, tmp_path):
    led, ctx = world
    f, case = Flow(led, ctx), Case("E03-duplicate-outcome-repaired-e")
    case.step("REQUEST_ACCESS")
    case.step("FORWARD_OR_CONSUME")
    signed, d, grant_id = f.granted()
    case.step("RELEASE")
    w = worker(led, tmp_path / "state")
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    w.release(grant_id)
    case.step("REPORT_OUTCOME")
    receipt = f.witness.attest_grant(grant_id)
    led.dbc.rpc("evm_mine")                                           # a later DBC block, so a second honest receipt differs from the first
    receipt2 = f.witness.attest_grant(grant_id)                       # obtained while the PBC still shows FORWARDED (the witness refuses afterwards)
    assert receipt2["receipt"]["dbcBlockNumber"] != receipt["receipt"]["dbcBlockNumber"]
    f.relay.report_outcome(signed["requestDigest"], OUTCOME, receipt)
    first = f.probe(signed["requestDigest"], "1")
    logs = led.pbc.call(led.LSC, "logCount")
    assert first["pscStatus"] == "2" and first["outcomeLogId"] != "0"
    case.step("DUPLICATE_OUTCOME")                                    # repeated reconciliation: same receipt; a different valid receipt and outcome digest
    same = observe(f.relay.report_outcome, signed["requestDigest"], OUTCOME, receipt)
    fresh = observe(f.relay.report_outcome, signed["requestDigest"], "0x" + "cd" * 32, receipt2)
    third = observe(f.witness.attest_grant, grant_id)                 # after the outcome the honest witness will not attest this grant again
    again = observe(f.consume_raw, signed["request"], d)              # and the DBC side: the consumed certificate cannot mint a second grant
    after = f.probe(signed["requestDigest"], "1")
    no_new = after == first and led.pbc.call(led.LSC, "logCount") == logs
    case.finish(agree(same, fresh), "NO_NEW_OUTCOME" if no_new and same.error and fresh.error else "NEW_OUTCOME",
                sameReceipt=same.error, secondValidReceiptNewOutcomeDigest=fresh.error, witnessAttestsAgainAfterOutcome=third.error,
                duplicateGrantAttempt=again.error)
    assert again.error == "REPLAY"


def _crash_case(world, tmp_path, case_id: str):
    """Shared schedule of the two crash cases. The hook is the one the CATALOG names (crashPoint), armed before the first RELEASE;
    the worker is then restarted on the same state directory and retries before the grant expires. A separate grant is crashed the same
    way and retried only after its expiry. Returns the raw observations; the catalog's `expected.worker` record is built from them."""
    led, ctx = world
    f, case = Flow(led, ctx), Case(case_id)
    fault = case.crash_fault()
    state = tmp_path / "state"
    case.step("REQUEST_ACCESS")
    case.step("FORWARD_OR_CONSUME")
    signed, d, grant_id = f.granted()
    case.step("RELEASE")                                              # the first attempt crashes at the injected point
    w = worker(led, state, faults={fault})
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    sent = []
    with pytest.raises(SimulatedCrash):
        w.release(grant_id, transmit=sent.append)
    persisted = db_rows(state, "select delivery, token, ciphertext_digest from releases")
    events_at_crash = [e[0] for e in db_rows(state, "select type from events order by id")]
    sent_at_crash = len(sent)
    case.step("CRASH_RESTART")                                        # a new process on the same durable state
    w2 = worker(led, state)
    case.step("RELEASE")                                              # the retry, before the original expiry
    resp = w2.release(grant_id, transmit=sent.append)
    case.step("REPORT_OUTCOME")
    receipt = f.witness.attest_grant(grant_id)
    f.relay.report_outcome(signed["requestDigest"], OUTCOME, receipt)
    reported = f.probe(signed["requestDigest"], "1")
    # a SEPARATE grant, crashed the same way and retried only after its original expiry
    signed_b, d_b, grant_b = f.granted(nonce="2")
    state_b = tmp_path / "state-b"
    wb = worker(led, state_b, faults={fault})
    wb.encrypt_record(P1_RECORD, P1_POLICY, "0")
    sent_b = []
    with pytest.raises(SimulatedCrash):
        wb.release(grant_b, transmit=sent_b.append)
    tokens_b = db_rows(state_b, "select token from releases")
    events_b = [e[0] for e in db_rows(state_b, "select type from events order by id")]
    setup.advance(led, 40)
    late = observe(worker(led, state_b).release, grant_b)
    after_b = (db_rows(state_b, "select token from releases"), [e[0] for e in db_rows(state_b, "select type from events order by id")])
    events = [e["type"] for e in w2.events()]
    row = persisted[0]
    record = {                                                        # the SAME closed field set as the catalog's expected.worker
        "releaseIntentCount": str(events.count("RELEASE_INTENT")), "releaseSentCount": str(events.count("RELEASE_SENT")),
        "sameCachedResponse": resp["responseEnvelope"]["token"] == row[1] and resp["ciphertextDigest"] == row[2] and all(x == resp for x in sent),
        "delivery": w2.status(grant_id)["delivery"], "expiredRetryError": late.error}
    expired_emits_no_event = after_b[1] == events_b and after_b[0] == tokens_b
    return case, record, dict(persisted=persisted, events_at_crash=events_at_crash, sent_at_crash=sent_at_crash, sent=sent, events=events,
                              reported=reported, expired_emits_no_event=expired_emits_no_event, f=f, signed=signed, receipt=receipt, w2=w2,
                              grant_id=grant_id)


def _crash_checks(r) -> bool:
    """Facts the catalog's qualification states in prose, checked from the observations (not hard-coded per crash point): the crash left
    delivery unknown, exactly one intent exists, the retry added exactly one attempt record, and the expired retry emitted nothing."""
    at_crash_sent = r["events_at_crash"].count("RELEASE_SENT")
    return (r["persisted"][0][0] == "unknown" and r["events_at_crash"].count("RELEASE_INTENT") == 1 and r["events"].count("RELEASE_INTENT") == 1
            and r["events"].count("RELEASE_SENT") == at_crash_sent + 1 and len(r["sent"]) == r["sent_at_crash"] + 1 and r["expired_emits_no_event"]
            and r["reported"]["pscStatus"] == "2")


def test_E03_crash_after_intent(world, tmp_path):
    case, record, r = _crash_case(world, tmp_path, "E03-crash-after-intent-repaired-e")
    conditional = _crash_checks(r) and record["expiredRetryError"] == "EXPIRED" and record["sameCachedResponse"]
    case.finish(None, "CONDITIONAL" if conditional else "UNCONDITIONAL", worker=record, eventsAtCrash=r["events_at_crash"],
                transmittedBeforeCrash=r["sent_at_crash"], eventsAfterRetry=r["events"], expiredRetryEmitsNoEvent=r["expired_emits_no_event"],
                outcomeRecorded=r["reported"]["pscStatus"] == "2")


def test_E03_crash_after_send(world, tmp_path):
    case, record, r = _crash_case(world, tmp_path, "E03-crash-after-send-repaired-e")
    dup = observe(r["f"].relay.report_outcome, r["signed"]["requestDigest"], OUTCOME, r["receipt"])      # reconciliation is idempotent
    conditional = _crash_checks(r) and record["expiredRetryError"] == "EXPIRED" and record["sameCachedResponse"] and dup.error == "REPLAY"
    case.finish(None, "CONDITIONAL" if conditional else "UNCONDITIONAL", worker=record, eventsAtCrash=r["events_at_crash"],
                transmittedBeforeCrash=r["sent_at_crash"], transmissionsTotal=len(r["sent"]), eventsAfterRetry=r["events"],
                expiredRetryEmitsNoEvent=r["expired_emits_no_event"], idempotentReconcile=dup.error, outcomeRecorded=r["reported"]["pscStatus"] == "2")


# =================================================================================================================================
# supplements (NOT catalog cases; they explain or extend a case and are not counted by the final test)
# =================================================================================================================================

def test_supplement_E01_substitution_variants_where_BAD_SIGNATURE_arises(world):
    """The catalog's BAD_SIGNATURE for subject substitution is real, but at other points than the naive field swap."""
    led, ctx = world
    f = Flow(led, ctx)
    signed, d = f.certified()
    forged = {**signed["request"], "gid": setup.addr("bob")}
    fd = request_digest(led, forged)
    # (a) the relay ALSO rewrites decision.requestDigest so check 4 passes; the witness signature no longer covers it: BAD_SIGNATURE
    rewritten = {"decision": {**d["decision"], "requestDigest": fd}, "signatures": d["signatures"]}
    assert observe(f.consume_raw, forged, d, cert=rewritten).error == "BAD_SIGNATURE"
    # (b) the relay forwards the substituted request to the PSC with Alice's signature: the PSC denies with BAD_SIGNATURE (a code, not a revert)
    swapped = {"request": forged, "requestDigest": fd, "signature": signed["signature"], "signer": signed["signer"]}
    assert f.forward(swapped).code == "BAD_SIGNATURE"
    assert led.pbc.call(led.PSC, "getRequest", fd)["status"] == "0"
    # (c) no variant produced a grant for Bob, and the genuine pair is still consumable
    assert led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, fd))[5] is False
    assert f.relay.deliver(signed, d) is not None


def test_supplement_E01_nonce_reuse_with_a_new_digest_is_rejected_by_the_dbc_nonce(world):
    """The identical-replay case is stopped by the existing grant; reusing the nonce under a NEW digest exercises the nonce itself.
    Defence in depth: the HONEST witness refuses (REPLAY) before signing; a deviating witness that signs ALLOW anyway is still stopped by the DBC."""
    from hmbc_protocol.witness import WitnessError
    led, ctx = world
    f = Flow(led, ctx)
    signed, d = f.certified(nonce="1", ttl=30)
    assert f.relay.deliver(signed, d) is not None
    second = f.sign_until("1", int(signed["request"]["expiresAt"]) - 10)   # same (gid, nonce), explicit expiry 10 s earlier -> a different digest
    assert second["requestDigest"] != signed["requestDigest"] and f.forward(second).code == "NONE"
    f.accept_checkpoint()
    with pytest.raises(WitnessError) as e:
        f.decide(second)
    assert e.value.code == "REPLAY"                                   # the honest witness never signs an ALLOW the DBC would revert
    forged = f.decision_for(second["request"], d["credentialRecords"], signer="witness-1")          # a deviating witness signs ALLOW anyway
    assert observe(f.consume_raw, second["request"], forged).error == "REPLAY"
    assert led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, second["requestDigest"]))[5] is False


def test_supplement_E01_request_for_another_destination_certified_here_is_still_wrong_destination(world):
    """The request's own destination binding is enforced independently of any signature: even a decision signed with the witness key
    (a deviating signer, outside E's single trusted witness) for a request that names another DBC is refused, and the identical
    construction for THIS destination is accepted, so the destination fields alone caused the rejection (agent 1's DecisionBinding variant)."""
    led, ctx = world
    f = Flow(led, ctx)
    signed, d = f.certified()
    records = d["credentialRecords"]
    mallory = setup.addr("mallory")
    base = f.client.build_request(data_id=setup.DATA_P1, nonce="5", expires_at=str(led.pbc.now() + 30), auth_epoch=led.pbc.call(led.TMSC, "authEpoch"))
    foreign = {**base, "destinationChainId": "38545", "kssc": mallory}
    refused = observe(f.consume_raw, foreign, f.decision_for(foreign, records, signer="witness-1"))
    assert refused.error == "WRONG_DESTINATION"
    assert led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, request_digest(led, foreign)))[5] is False
    f.consume_raw(base, f.decision_for(base, records, signer="witness-1"))
    assert led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, request_digest(led, base)))[5] is True


def register_bob(led) -> dict:
    """Fixture user Bob: a Researcher certificate from H2 (valid credentials, but the record's policy needs Doctor AND OnDuty)."""
    dep, t = led.deployment, led.pbc.now()
    bob, h2 = setup.addr("bob"), setup.addr("H2-root")
    cert = {"issuer": h2, "gid": bob, "roles": ["0x" + keccak(text="HMBC.role.Researcher").hex()], "serial": "201",
            "validFrom": "1700000000", "validUntil": "2100000000"}
    signed_cert = {"cert": cert, "signature": setup.sign("RoleCertificate", cert, dep, "H2-root")}
    cert_digest = "0x" + messages.digest_of("RoleCertificate", cert, messages.domain_for("RoleCertificate", cert, dep)).hex()
    reg = {"gid": bob, "certDigest": cert_digest, "recipientKeyHash": keys.recipient_key_hash("keyref:user:bob"), "expiresAt": str(t + 600)}
    led.pbc.send(setup.key("relay"), led.RSC, "register", reg, setup.sign("Registration", reg, dep, "bob"), signed_cert)
    return {"certificates": [signed_cert], "temporalClaims": []}


def test_supplement_bob_valid_credentials_but_insufficient_policy_is_a_signed_deny_the_dbc_audits(world):
    """A1-0017 / A3-0012 control: Bob's credentials are VALID but do not satisfy the record's policy. The honest witness signs DENY; the DBC
    logs it (AccessLog +1) without reverting, issues no grant and leaves the nonce unconsumed. A deviating witness signing ALLOW for Bob
    makes consumeDecision revert POLICY_DENIED with no AccessLog and no state change."""
    led, ctx = world
    f = Flow(led, ctx)
    bob = setup.addr("bob")
    bundle = register_bob(led)
    client = UserClient("bob", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client, nonce="1"))
    assert f.relay.forward(signed, bundle).code == "NONE"            # the PBC accepts Bob: his credentials are valid
    f.accept_checkpoint()
    d = f.decide(signed)
    assert d["decision"]["result"] == "0" and len(d["credentialRecords"]) == 1      # signed DENY; the valid Researcher record is still attested
    digest = signed["requestDigest"]
    before = f.probe(digest, "1", bob)
    assert before["nonceConsumed"] is False
    rc = f.consume_raw(signed["request"], d)                          # (1) the honest DENY: raw submission, so a revert would raise
    after = f.probe(digest, "1", bob)
    logs = [led.ACSC.decode_log(lg) for lg in rc["logs"] if lg["address"].lower() == led.ACSC.address]
    assert [n for n, _ in logs] == ["AccessLog"] and logs[0][1]["allowed"] is False and logs[0][1]["gid"] == bob
    assert chain.ERROR_NAMES[int(logs[0][1]["code"])] == "POLICY_DENIED"
    assert int(after["accessLogCount"]) == int(before["accessLogCount"]) + 1       # AccessLog +1
    assert after["grant"][5] is False and after["nonceConsumed"] is False         # no grant; NONCE_UNCHANGED
    forged = f.decision_for(signed["request"], d["credentialRecords"], signer="witness-1", result="1")      # (2) a deviating witness signs ALLOW
    rejected = observe(f.consume_raw, signed["request"], forged)
    assert rejected.error == "POLICY_DENIED"
    assert f.probe(digest, "1", bob) == after                                     # no AccessLog, no grant, nonce still unconsumed


# =================================================================================================================================
# negative controls: "reject everything" and "accept everything" must both fail
# =================================================================================================================================

def test_control_legitimate_flow_succeeds_end_to_end(world, tmp_path):
    """Grant allowed, release, completion, receipt and outcome recorded in the same fixture the rejection cases use."""
    led, ctx = world
    f = Flow(led, ctx)
    signed, d, grant_id = f.granted()
    g = led.dbc.call(led.KSSC, "getGrant", grant_id)
    assert g[5] is True and g[0] == signed["requestDigest"] and g[2] == ctx.alice and led.dbc.call(led.KSSC, "nonceConsumed", ctx.alice, "1") is True
    w = worker(led, tmp_path / "state")
    enc = w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    resp = w.release(grant_id)
    assert w.finish_decryption(resp, "keyref:user:alice") == {"schemaVersion": "v1", "adapterMode": "symbolic", "decryptable": True,
                                                              "dataId": setup.DATA_P1, "ciphertextDigest": enc["ciphertextDigest"]}
    receipt = f.witness.attest_grant(grant_id)
    f.relay.report_outcome(signed["requestDigest"], OUTCOME, receipt)
    p = f.probe(signed["requestDigest"], "1")
    assert p["pscStatus"] == "2" and p["outcomeLogId"] != "0"


def test_control_harness_detects_a_wrong_expectation(world):
    led, ctx = world
    f = Flow(led, ctx)
    # (1) a call that succeeds is never mistaken for a rejection: pytest.raises on it FAILS
    with pytest.raises(pytest.fail.Exception):
        with pytest.raises(chain.Rejected):
            led.pbc.call(led.TMSC, "authEpoch")
    assert observe(led.pbc.call, led.TMSC, "authEpoch").error is None
    # (2) the comparison every case ends in raises on a wrong, a missing and a surplus error code, and passes on the right ones
    for obs, expected in ((Obs("REPLAY"), "EXPIRED"), (Obs(None), "REPLAY"), (Obs("REPLAY"), None)):
        with pytest.raises(AssertionError):
            check_error(obs, expected)
    check_error(Obs("REPLAY"), "REPLAY")
    check_error(Obs(None), None)
    # (3) live: a real REPLAY rejection is reported as REPLAY, so asserting EXPIRED against it is a detected mismatch
    signed, d, _ = f.granted()
    replay = observe(f.consume_raw, signed["request"], d)
    assert replay.error == "REPLAY"
    with pytest.raises(AssertionError):
        check_error(replay, "EXPIRED")
    # (4) a dry-run Case ends in the same comparison: wrong catalog error / wrong outcome / skipped directive are all detected
    for err, outcome in (("EXPIRED", "NO_NEW_GRANT"), ("REPLAY", "REJECT")):
        c = Case("E01-nonce-replay-repaired-e", dry_run=True)
        c.performed = list(c.catalog_steps)
        with pytest.raises(AssertionError):
            c.finish(err, outcome)
    c = Case("E01-nonce-replay-repaired-e", dry_run=True)
    c.performed = c.catalog_steps[:-1]
    with pytest.raises(e2.StepScheduleError):
        c.finish("REPLAY", "NO_NEW_GRANT")
    c = Case("E01-nonce-replay-repaired-e", dry_run=True)
    c.performed = list(c.catalog_steps)
    c.finish("REPLAY", "NO_NEW_GRANT")                                # the catalog's own answer passes, so the check is not "fail always"


# =================================================================================================================================
# the last test: no catalog case may hide
# =================================================================================================================================

def test_zz_every_catalog_case_was_executed_exactly_once():
    expected_ids = sorted(f"{c}-repaired-e" for c in (
        "E01-subject-substitution", "E01-nonce-replay", "E01-expiry-boundary", "E02-signed-list-rollback", "E02-wrong-issuer",
        "E02-pre-barrier-revocation", "E02-post-barrier-revocation", "E02-expired-duty", "E03-dropped-outcome", "E03-fabricated-outcome",
        "E03-duplicate-outcome", "E03-crash-after-intent", "E03-crash-after-send",
        "E01-forged-tuple", "E01-wrong-destination", "E01-new-reference-replay"))               # the last three are new in revision 5
    import json
    print("\nOBSERVED " + json.dumps(OBSERVED, indent=1, sort_keys=True))
    assert e2.REPAIRED_E_IDS == expected_ids and len(expected_ids) == 16                 # the pinned catalog holds exactly these repaired-e cases
    assert sorted(e2.EXECUTED) == expected_ids, f"cases never concluded: {sorted(set(expected_ids) - set(e2.EXECUTED))}"
    assert all(n == 1 for n in e2.EXECUTED.values()), dict(e2.EXECUTED)
    assert sorted(OBSERVED) == expected_ids
    disagree = {cid for cid, r in OBSERVED.items() if (r["observedError"], r["observedOutcome"]) != (r["expectedError"], r["expectedOutcome"])}
    assert disagree == XFAILED, f"disagreements {sorted(disagree)} are not exactly the xfail-marked cases {sorted(XFAILED)}"
    for cid, rec in OBSERVED.items():
        assert {"classificationExpected", "expectedError", "observedError", "observedOutcome"} <= set(rec), cid
        assert rec["stepsExecuted"] == [s["action"] for s in e2.CATALOG[cid]["steps"]], cid
        assert rec["expectedError"] == e2.CATALOG[cid]["expected"]["error"] and rec["classificationExpected"] == e2.CATALOG[cid]["expected"]["classification"]
        assert rec["workerExpected"] == e2.CATALOG[cid]["expected"].get("worker") and rec["workerObserved"] == rec["workerExpected"], cid
    assert sorted(c for c, r in OBSERVED.items() if r["workerExpected"] is not None) == ["E03-crash-after-intent-repaired-e", "E03-crash-after-send-repaired-e"]
