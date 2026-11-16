// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {
    Profile,
    isRepaired,
    ErrorCode,
    HMBCHash,
    Registration,
    SignedRoleCertificate,
    RevocationList,
    TemporalAcl,
    AccessRequest,
    CredentialRecord,
    CREDENTIAL_LONG_TERM,
    CREDENTIAL_TEMPORAL
} from "../src/types/ProtocolTypes.sol";
import {TMSC} from "../src/TMSC.sol";
import {LSC} from "../src/LSC.sol";

/// A-E1: TMSC updateTrustAnchors issuer scoping and validation effects, run once per profile.
abstract contract TrustAnchorsBase is HMBCFixture {
    function test_H1AdminCannotReplaceH2TemporalAcl() public {
        publishAcl(onDutyAcl(h2, 1, one(bob)), h2Pk, h2Admin);
        TMSC.AnchorState memory before = tmsc.temporalAclState(h2);
        uint64 epoch = tmsc.authEpoch();

        TemporalAcl memory forged = onDutyAcl(h2, 2, one(mallory));
        bytes memory h2Signed = signAcl(forged, h2Pk); // even with H2's genuine signature
        vm.prank(h1Admin);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        tmsc.updateTemporalAcl(forged, h2Signed);

        TMSC.AnchorState memory afterState = tmsc.temporalAclState(h2);
        assertEq(afterState.generation, before.generation, "H2 list head unchanged");
        assertEq(afterState.contentDigest, before.contentDigest, "H2 content unchanged");
        assertEq(tmsc.authEpoch(), epoch, "authEpoch unchanged");
        assertTrue(tmsc.temporalWindow(h2, bob, ROLE_ON_DUTY).present, "Bob still listed");
        assertFalse(tmsc.temporalWindow(h2, mallory, ROLE_ON_DUTY).present, "Mallory not listed");
    }

    function test_H1AdminCannotReplaceH2RevocationList() public {
        uint64[] memory serials = new uint64[](1);
        serials[0] = BOB_SERIAL;
        RevocationList memory l = revocationList(h2, 1, serials);
        bytes memory h2Signed = signCrl(l, h2Pk);
        vm.prank(h1Admin);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        tmsc.updateRevocationList(l, h2Signed);
        assertFalse(tmsc.revocationListState(h2).published, "nothing published for H2");
    }

    function test_UnknownAuthorityIsRejected() public {
        RevocationList memory l = revocationList(mallory, 1, new uint64[](0));
        bytes memory s = signCrl(l, malloryPk);
        vm.prank(h1Admin);
        expectRejected(ErrorCode.UNKNOWN_AUTHORITY);
        tmsc.updateRevocationList(l, s);
    }

    function test_NonAdminCannotUpdateEvenWithIssuerSignature() public {
        RevocationList memory l = revocationList(h1, 1, new uint64[](0));
        bytes memory s = signCrl(l, h1Pk);
        vm.prank(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        tmsc.updateRevocationList(l, s);
    }

    /// Profile distinction: H2's own admin submits an H2 list that H2's root did not sign.
    function test_ListNotSignedByIssuerRootKey() public {
        TemporalAcl memory acl = onDutyAcl(h2, 1, one(mallory));
        bytes memory wrongSigner = signAcl(acl, h1Pk);
        vm.prank(h2Admin);
        if (profile() == Profile.PAPER_MINIMAL) {
            tmsc.updateTemporalAcl(acl, wrongSigner);
            assertTrue(tmsc.temporalWindow(h2, mallory, ROLE_ON_DUTY).present, "minimal trusts the admin caller");
        } else {
            expectRejected(ErrorCode.BAD_SIGNATURE);
            tmsc.updateTemporalAcl(acl, wrongSigner);
            assertFalse(tmsc.temporalAclState(h2).published, "rejected list not installed");
        }
    }

    function test_UpdateAdvancesFig4PointerEpochAndLog() public {
        uint64 epoch0 = tmsc.authEpoch();
        uint256 logs0 = lsc.logCount();
        publishCrl(h1, h1Pk, h1Admin, 1, new uint64[](0));
        TMSC.AnchorState memory s1 = tmsc.revocationListState(h1);
        vm.roll(block.number + 5);
        publishCrl(h1, h1Pk, h1Admin, 2, new uint64[](0));
        TMSC.AnchorState memory s2 = tmsc.revocationListState(h1);
        assertEq(s2.generation, s1.generation + 1, "new list head");
        assertEq(s2.prevBlockNumber, s1.blockNumber, "Fig. 4 pointer to previous anchor block");
        assertEq(s2.version, 2, "version recorded");
        assertEq(tmsc.authEpoch(), epoch0 + 2, "authEpoch counts accepted updates");
        assertEq(lsc.logCount(), logs0 + 2, "each update triggers updateLog");
        (LSC.LogEntry memory e,) = lsc.getLog(logs0 + 2);
        assertTrue(e.kind == LSC.LogKind.TRUST_UPDATE, "TRUST_UPDATE log kind");
    }

    function test_CrlRevocationTakesEffectAtPbc() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(1);
        bytes memory s = signRequest(r, alicePk);
        uint64[] memory serials = new uint64[](1);
        serials[0] = ALICE_SERIAL;
        publishCrl(h1, h1Pk, h1Admin, 2, serials);
        assertTrue(tmsc.isRevoked(h1, ALICE_SERIAL), "serial revoked in latest CRL");
        if (isRepaired(profile())) {
            (, ErrorCode stale) = submit(r, s, aliceBundle());
            assertCode(stale, ErrorCode.STALE_STATE, "repaired: request signed under an older authEpoch");
            r = aliceRequest(2);
            s = signRequest(r, alicePk);
        }
        (, ErrorCode code) = submit(r, s, aliceBundle());
        assertCode(code, ErrorCode.REVOKED, "revoked certificate rejected by getUserValidation");
    }

    function test_TempAclRemovalRevokesOnDuty() public {
        publishTrustLists(one(alice));
        registerAlice();
        publishAcl(onDutyAcl(h1, 2, new address[](0)), h1Pk, h1Admin);
        AccessRequest memory r = aliceRequest(1);
        (, ErrorCode code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, ErrorCode.REVOKED, "OnDuty absent from latest TempACL");
    }

    function test_OnDutyOutsideEffectivePeriodIsExpired() public {
        publishTrustLists(one(alice));
        registerAlice();
        vm.warp(T0 + 8 hours); // entry validUntil == now
        AccessRequest memory r = aliceRequest(1);
        (, ErrorCode code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, ErrorCode.EXPIRED, "TempACL entry effective period ended (equality rejects)");
    }

    /// Aligns with candidate schema (A3-0003): a certificate whose validFrom >= validUntil is
    /// structurally invalid (MALFORMED), not merely expired.
    function test_CertificateWithEmptyIntervalIsMalformed() public {
        publishTrustLists(one(alice));
        SignedRoleCertificate memory c = aliceCert();
        c.cert.validFrom = c.cert.validUntil;
        c.signature = sig(h1Pk, HMBCHash.roleCertificateDigest(c.cert, PBC_CHAIN_ID, address(tmsc)));
        (ErrorCode code,) = tmsc.validateCertificate(c, uint64(block.timestamp));
        assertCode(code, ErrorCode.MALFORMED, "empty validity interval");
    }

    function test_VerifiedRecordsAreCanonical() public {
        publishTrustLists(one(alice));
        CredentialRecord[] memory recs = verifiedRecords(alice, aliceBundle());
        assertEq(recs.length, 2, "two records");
        assertEq(recs[0].issuer, h1, "long-term issuer");
        assertEq(recs[0].role, ROLE_DOCTOR, "long-term role");
        assertEq(recs[0].kind, CREDENTIAL_LONG_TERM, "long-term first");
        assertEq(recs[0].serial, ALICE_SERIAL, "serial");
        assertEq(recs[1].issuer, h1, "temporal issuer");
        assertEq(recs[1].role, ROLE_ON_DUTY, "temporal role");
        assertEq(recs[1].kind, CREDENTIAL_TEMPORAL, "temporal second");
        assertEq(recs[1].anchorVersion, 1, "TempACL version");
    }
}

contract TrustAnchorsPaperStrictTest is TrustAnchorsBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_STRICT;
    }
}

contract TrustAnchorsPaperMinimalTest is TrustAnchorsBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_MINIMAL;
    }
}

contract TrustAnchorsRepairedTest is TrustAnchorsBase {
    function profile() internal pure virtual override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    function test_RepairedRequiresPublishedFreshCrl() public {
        SignedRoleCertificate memory cert = aliceCert();
        Registration memory reg = Registration(
            alice, HMBCHash.roleCertificateDigest(cert.cert, PBC_CHAIN_ID, address(tmsc)), ALICE_RECIPIENT_KEY_HASH, T0 + 600
        );
        bytes memory possession = sig(alicePk, HMBCHash.registrationDigest(reg, PBC_CHAIN_ID, address(rsc)));
        expectRejected(ErrorCode.STALE_ANCHOR);
        rsc.register(reg, possession, cert); // no H1 CRL published yet

        RevocationList memory shortCrl = RevocationList(h1, 1, T0 + 100, new uint64[](0));
        bytes memory s = signCrl(shortCrl, h1Pk);
        vm.prank(h1Admin);
        tmsc.updateRevocationList(shortCrl, s);
        rsc.register(reg, possession, cert);
        publishAcl(onDutyAcl(h1, 1, one(alice)), h1Pk, h1Admin);

        vm.warp(T0 + 100); // CRL validUntil == now
        AccessRequest memory r = aliceRequest(1);
        (, ErrorCode code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, ErrorCode.STALE_ANCHOR, "repaired: expired CRL cannot vouch for the certificate");
    }
}
