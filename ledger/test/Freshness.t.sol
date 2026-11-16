// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {
    Profile,
    isRepaired,
    ErrorCode,
    HMBCHash,
    RevocationList,
    TemporalAcl,
    TempAclEntry,
    AccessRequest,
    CredentialRecord,
    DecisionCertificate,
    StateCheckpoint,
    ForwardedRequest,
    RESULT_ALLOW
} from "../src/types/ProtocolTypes.sol";
import {TMSC} from "../src/TMSC.sol";

/// A-E2 / E02 trust-anchor freshness. Expectations were written from SPEC section 4 and the A1-0002
/// completions BEFORE the first run (first-run output: evidence/ae2-first-run.txt).
/// Classification per test: paper profiles = observed SPEC_GAP behavior (asserted as such, so the
/// gap is a recorded result, not a red build); repaired-e = REPAIR_SUPPORTED property.
abstract contract FreshnessBase is HMBCFixture {
    function repaired() internal pure returns (bool) {
        return isRepaired(profile());
    }

    /// Alice is on duty in H1 TempACL v1, removed in v2; then the issuer's CA-Admin re-submits the
    /// correctly signed v1. Paper: latest-appended wins, so the revocation is undone (SPEC_GAP C06).
    /// Repaired-e: STALE_ANCHOR, Alice stays revoked.
    function test_E02_StaleSignedTempAclReplay() public {
        publishTrustLists(one(alice));
        registerAlice();
        TemporalAcl memory v1 = onDutyAcl(h1, 1, one(alice));
        bytes memory v1Sig = signAcl(v1, h1Pk);
        publishAcl(onDutyAcl(h1, 2, new address[](0)), h1Pk, h1Admin);

        vm.prank(h1Admin);
        if (repaired()) expectRejected(ErrorCode.STALE_ANCHOR);
        tmsc.updateTemporalAcl(v1, v1Sig);

        AccessRequest memory r = aliceRequest(1);
        (, ErrorCode code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, repaired() ? ErrorCode.REVOKED : ErrorCode.NONE, "OnDuty after replay of signed v1");
    }

    /// Same for a CRL: v2 revokes Alice's certificate, then the signed v1 (empty) is re-submitted.
    function test_E02_StaleSignedCrlReplay() public {
        publishTrustLists(one(alice));
        registerAlice();
        RevocationList memory v1 = revocationList(h1, 1, new uint64[](0)); // same content as published v1
        bytes memory v1Sig = signCrl(v1, h1Pk);
        uint64[] memory serials = new uint64[](1);
        serials[0] = ALICE_SERIAL;
        publishCrl(h1, h1Pk, h1Admin, 2, serials);
        assertTrue(tmsc.isRevoked(h1, ALICE_SERIAL), "revoked by v2");

        vm.prank(h1Admin);
        if (repaired()) expectRejected(ErrorCode.STALE_ANCHOR);
        tmsc.updateRevocationList(v1, v1Sig);

        assertEq(tmsc.isRevoked(h1, ALICE_SERIAL) ? 1 : 0, repaired() ? 1 : 0, "revocation state after replay");
        AccessRequest memory r = aliceRequest(1);
        (, ErrorCode code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, repaired() ? ErrorCode.REVOKED : ErrorCode.NONE, "certificate after replay of signed v1");
    }

    /// Two different lists with the same version: paper accepts both (no versioning); repaired rejects.
    function test_E02_EqualVersionDifferentContent() public {
        publishAcl(onDutyAcl(h1, 5, one(alice)), h1Pk, h1Admin);
        TemporalAcl memory other = onDutyAcl(h1, 5, one(bob));
        bytes memory s = signAcl(other, h1Pk);
        vm.prank(h1Admin);
        if (repaired()) expectRejected(ErrorCode.STALE_ANCHOR);
        tmsc.updateTemporalAcl(other, s);
        assertTrue(tmsc.temporalWindow(h1, bob, ROLE_ON_DUTY).present != repaired(), "second v5 installed only in paper");
    }

    /// A list whose validUntil == now: paper installs it (no list validity semantics); repaired rejects.
    function test_E02_ExpiredListInstall() public {
        TemporalAcl memory acl = onDutyAcl(h1, 1, one(alice));
        acl.validUntil = uint64(block.timestamp);
        bytes memory s = signAcl(acl, h1Pk);
        vm.prank(h1Admin);
        if (repaired()) expectRejected(ErrorCode.STALE_ANCHOR);
        tmsc.updateTemporalAcl(acl, s);
        assertTrue(tmsc.temporalAclState(h1).published != repaired(), "expired list installed only in paper");
    }

    /// A list that expires while its entry is still effective. Repaired: STALE_ANCHOR at use.
    /// Paper: the entry remains usable (list validity is not part of the paper's model).
    function test_E02_ListExpiryAtUse() public {
        publishCrl(h1, h1Pk, h1Admin, 1, new uint64[](0));
        publishCrl(h2, h2Pk, h2Admin, 1, new uint64[](0));
        TemporalAcl memory acl = onDutyAcl(h1, 1, one(alice));
        acl.validUntil = T0 + 100;
        publishAcl(acl, h1Pk, h1Admin);
        registerAlice();
        vm.warp(T0 + 100);
        AccessRequest memory r = aliceRequest(1);
        (, ErrorCode code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, repaired() ? ErrorCode.STALE_ANCHOR : ErrorCode.NONE, "TempACL list expired, entry not");
    }

    /// A request is forwarded by the PBC, then H1 removes Alice from duty on the PBC, then the
    /// request reaches the DBC. Paper: grant (no DBC revocation barrier; SPEC_GAP). Repaired-e with no
    /// newer checkpoint yet: grant inside the documented pre-barrier window (interfaces v0).
    function test_E02_DelayedDeliveryAcrossPbcRevocationBeforeBarrier() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        StateCheckpoint memory cp;
        DecisionCertificate memory c;
        if (repaired()) {
            cp = acceptCheckpoint();
            c = certify(decisionFor(r, RESULT_ALLOW, recs, cp), witnessPk);
        }
        vm.warp(block.timestamp + 5);
        publishAcl(onDutyAcl(h1, 2, new address[](0)), h1Pk, h1Admin); // PBC revocation
        assertFalse(tmsc.temporalWindow(h1, alice, ROLE_ON_DUTY).present, "revoked on PBC");

        bytes32 grantId;
        vm.prank(relay);
        if (repaired()) grantId = acsc.consumeDecision(r, c, recs);
        else (, grantId) = acsc.policyEnf(ForwardedRequest(digest, alice, DATA_P1, r.action), recs);
        (,,,,, bool allowed) = kssc.getGrant(grantId);
        assertTrue(allowed, "grant issued after PBC revocation (pre-barrier / no barrier)");
    }

    /// Short duty: the OnDuty entry ends 10 s after the PBC decision, the decision is still unexpired
    /// when delivered. Paper: grant (DBC does not re-check attribute validity; SPEC_GAP).
    /// Repaired: EXPIRED (record validUntil checked at the DBC).
    function test_E02_DeliveryAfterOnDutyEntryEnds() public {
        publishCrl(h1, h1Pk, h1Admin, 1, new uint64[](0));
        publishCrl(h2, h2Pk, h2Admin, 1, new uint64[](0));
        TemporalAcl memory acl = onDutyAcl(h1, 1, one(alice));
        acl.entries[0].validUntil = T0 + 10;
        publishAcl(acl, h1Pk, h1Admin);
        registerAlice();
        (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        StateCheckpoint memory cp;
        DecisionCertificate memory c;
        if (repaired()) {
            cp = acceptCheckpoint();
            c = certify(decisionFor(r, RESULT_ALLOW, recs, cp), witnessPk);
        }
        vm.warp(T0 + 10);
        vm.prank(relay);
        if (repaired()) {
            expectRejected(ErrorCode.EXPIRED);
            acsc.consumeDecision(r, c, recs);
            assertFalse(kssc.nonceConsumed(alice, 1), "no nonce consumed");
        } else {
            (bool allowed,) = acsc.policyEnf(ForwardedRequest(digest, alice, DATA_P1, r.action), recs);
            assertTrue(allowed, "paper: grant after the duty period ended");
        }
    }
}

contract FreshnessPaperStrictTest is FreshnessBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_STRICT;
    }
}

contract FreshnessPaperMinimalTest is FreshnessBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_MINIMAL;
    }
}

/// Repaired-e only: the checkpoint is the revocation barrier and must be monotone and fresh.
contract FreshnessRepairedTest is FreshnessBase {
    function profile() internal pure virtual override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    /// After the DBC accepts a newer checkpoint, a decision made under the older one is STALE_STATE,
    /// with no grant and no nonce consumption.
    function test_E02_RevocationBarrierBlocksOlderDecision() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        StateCheckpoint memory cp1 = acceptCheckpoint();
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, cp1), witnessPk);
        publishAcl(onDutyAcl(h1, 2, new address[](0)), h1Pk, h1Admin);
        vm.warp(block.timestamp + 1);
        StateCheckpoint memory cp2 = acceptCheckpoint(); // carries the new authEpoch
        assertTrue(cp2.authEpoch > cp1.authEpoch, "revocation advanced authEpoch");

        expectRejected(ErrorCode.STALE_STATE);
        acsc.consumeDecision(r, c, recs);
        assertFalse(kssc.nonceConsumed(alice, 1), "no nonce consumed");
        (,,,,, bool allowed) = kssc.getGrant(HMBCHash.grantId(digest, address(kssc), DBC_CHAIN_ID));
        assertFalse(allowed, "no grant after the barrier");
    }

    function test_E02_CheckpointMonotonicityAndFreshness() public {
        StateCheckpoint memory cp2 = checkpointNow();
        cp2.sequence = 2;
        kssc.acceptState(cp2, signCheckpoint(cp2, witnessPk));

        StateCheckpoint memory older = checkpointNow();
        older.sequence = 1;
        bytes[] memory s1 = signCheckpoint(older, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(older, s1); // rollback

        bytes[] memory s2 = signCheckpoint(cp2, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(cp2, s2); // replay of the same sequence

        StateCheckpoint memory lowerEpoch = checkpointNow();
        lowerEpoch.sequence = 3;
        lowerEpoch.authEpoch = cp2.authEpoch;
        StateCheckpoint memory higher = checkpointNow();
        higher.sequence = 3;
        higher.authEpoch = cp2.authEpoch + 2;
        kssc.acceptState(higher, signCheckpoint(higher, witnessPk));
        lowerEpoch.sequence = 4;
        bytes[] memory s3 = signCheckpoint(lowerEpoch, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(lowerEpoch, s3); // authEpoch decrease

        StateCheckpoint memory tooLong = checkpointNow();
        tooLong.sequence = 5;
        tooLong.authEpoch = higher.authEpoch;
        tooLong.expiresAt = uint64(block.timestamp) + CHECKPOINT_TTL + 1;
        bytes[] memory s4 = signCheckpoint(tooLong, witnessPk);
        expectRejected(ErrorCode.MALFORMED);
        kssc.acceptState(tooLong, s4);

        StateCheckpoint memory expired = checkpointNow();
        expired.sequence = 5;
        expired.authEpoch = higher.authEpoch;
        expired.expiresAt = uint64(block.timestamp);
        bytes[] memory s5 = signCheckpoint(expired, witnessPk);
        expectRejected(ErrorCode.EXPIRED);
        kssc.acceptState(expired, s5); // now == expiresAt

        StateCheckpoint memory foreign = checkpointNow();
        foreign.sequence = 5;
        foreign.authEpoch = higher.authEpoch;
        bytes[] memory s6 = signCheckpoint(foreign, malloryPk);
        expectRejected(ErrorCode.BAD_SIGNATURE);
        kssc.acceptState(foreign, s6);

        (, StateCheckpoint memory cur) = kssc.currentCheckpoint();
        assertEq(cur.sequence, 3, "only accepted checkpoints changed state");
    }

    function test_E02_DecisionMayNotOutliveCheckpoint() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        StateCheckpoint memory cp = acceptCheckpoint();
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, cp), witnessPk);
        c.decision.expiresAt = cp.expiresAt + 1; // a decision may not outlive its checkpoint
        c = certify(c.decision, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        acsc.consumeDecision(r, c, recs);
    }
}
