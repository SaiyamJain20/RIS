// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {
    Profile,
    ErrorCode,
    HMBCHash,
    AccessRequest,
    AccessDecision,
    CredentialRecord,
    DecisionCertificate,
    StateCheckpoint,
    ForwardedRequest,
    ACTION_READ,
    RESULT_ALLOW,
    CREDENTIAL_LONG_TERM
} from "../src/types/ProtocolTypes.sol";

/// A-E2 / E01 decision provenance and replay. Expectations written before the first run
/// (evidence/ae2-first-run.txt). Paper profiles: the relay tuple carries no source binding, so
/// substitution/fabrication by the (assumed isolated) relay succeeds = SPEC_GAP observed under a
/// violated isolation assumption (stress). Repaired-e: every binding rejects with a stable code and
/// leaves no grant/nonce state.
abstract contract DecisionBindingPaperBase is HMBCFixture {
    function forward(bytes32 ref, address gid, CredentialRecord[] memory recs) internal returns (bool allowed, bytes32 g) {
        vm.prank(relay);
        return acsc.policyEnf(ForwardedRequest(ref, gid, DATA_P1, ACTION_READ), recs);
    }

    /// The relay forwards Alice's verified attributes under Bob's GID: Bob gets the grant.
    function test_E01_RelaySubjectSubstitution() public {
        publishTrustLists(one(alice));
        registerAlice();
        (, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        (bool allowed, bytes32 g) = forward(digest, bob, recs);
        assertTrue(allowed, "SPEC_GAP: no binding between forwarded GID and verified attributes");
        (,, address gid,,,) = kssc.getGrant(g);
        assertEq(gid, bob, "grant issued to the substituted subject");
    }

    /// The relay fabricates a request reference and attributes for an unregistered user who never
    /// asked the PBC: grant, and no PBC request log for that reference.
    function test_E01_RelayFabricatedRequest() public {
        CredentialRecord[] memory recs = new CredentialRecord[](2);
        recs[0] = CredentialRecord(h1, ROLE_DOCTOR, CREDENTIAL_LONG_TERM, 999, 1, T0 + 1 days);
        recs[1] = CredentialRecord(h1, ROLE_ON_DUTY, 2, 0, 1, T0 + 1 days);
        bytes32 ref = keccak256("fabricated-request");
        (bool allowed,) = forward(ref, mallory, recs);
        assertTrue(allowed, "SPEC_GAP: DBC cannot tell a fabricated tuple from a PBC decision");
        assertEq(lsc.firstRequestLogId(ref), 0, "no PBC request log behind the grant");
    }

    /// Re-forwarding the same decision under a new reference yields a second grant.
    function test_E01_RelayReplayUnderNewReference() public {
        publishTrustLists(one(alice));
        registerAlice();
        (, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        forward(digest, alice, recs);
        (bool again, bytes32 g2) = forward(keccak256(abi.encode(digest, "replay")), alice, recs);
        assertTrue(again && g2 != bytes32(0), "SPEC_GAP: no request-level replay protection on the DBC");
    }

    /// Delivered after the user's request expired: the tuple has no expiry, so it is granted.
    function test_E01_RelayDeliveryAfterRequestExpiry() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        vm.warp(r.expiresAt + 60);
        (bool allowed,) = forward(digest, alice, recs);
        assertTrue(allowed, "SPEC_GAP: no expiry in the forwarded tuple");
    }
}

contract DecisionBindingPaperStrictTest is DecisionBindingPaperBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_STRICT;
    }
}

contract DecisionBindingPaperMinimalTest is DecisionBindingPaperBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_MINIMAL;
    }
}

contract DecisionBindingRepairedTest is HMBCFixture {
    AccessRequest internal r;
    CredentialRecord[] internal recs;
    StateCheckpoint internal cp;
    DecisionCertificate internal cert;

    function profile() internal pure virtual override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    function setUp() public override {
        super.setUp();
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory req,, CredentialRecord[] memory rs) = aliceForwarded(1);
        r = req;
        for (uint256 i = 0; i < rs.length; i++) {
            recs.push(rs[i]);
        }
        cp = acceptCheckpoint();
        cert = certify(decisionFor(r, RESULT_ALLOW, recs, cp), witnessPk);
    }

    function rejectsWithoutState(AccessRequest memory rq, DecisionCertificate memory c, CredentialRecord[] memory rs, ErrorCode code, string memory what)
        internal
    {
        uint256 logs = acsc.accessLogCount();
        expectRejected(code);
        acsc.consumeDecision(rq, c, rs);
        assertFalse(kssc.nonceConsumed(alice, 1), string.concat(what, ": nonce untouched"));
        assertEq(acsc.accessLogCount(), logs, string.concat(what, ": no access log"));
    }

    function test_E01_PositiveControl() public {
        bytes32 g = acsc.consumeDecision(r, cert, recs);
        (,,,,, bool allowed) = kssc.getGrant(g);
        assertTrue(allowed, "unmodified certificate grants");
    }

    /// Each AccessRequest field substituted while the original certificate is presented.
    function test_E01_RequestFieldSubstitution() public {
        for (uint256 i = 0; i < 13; i++) {
            AccessRequest memory x = r;
            ErrorCode want = ErrorCode.WRONG_SUBJECT;
            if (i == 0) (x.sourceChainId, want) = (x.sourceChainId + 1, ErrorCode.WRONG_DESTINATION);
            if (i == 1) (x.destinationChainId, want) = (x.destinationChainId + 1, ErrorCode.WRONG_DESTINATION);
            if (i == 2) (x.psc, want) = (mallory, ErrorCode.WRONG_DESTINATION);
            if (i == 3) (x.kssc, want) = (mallory, ErrorCode.WRONG_DESTINATION);
            if (i == 4) x.gid = bob;
            if (i == 5) x.dataId = keccak256("HMBC.data.P2.MHR");
            if (i == 6) (x.action, want) = (2, ErrorCode.MALFORMED);
            if (i == 7) x.policyVersion += 1;
            if (i == 8) x.authEpoch += 1;
            if (i == 9) x.keyEpoch += 1;
            if (i == 10) x.nonce += 1;
            if (i == 11) x.expiresAt += 1;
            if (i == 12) x.recipientKeyHash = BOB_RECIPIENT_KEY_HASH;
            rejectsWithoutState(x, cert, recs, want, string.concat("request field ", vm.toString(i)));
        }
        test_E01_PositiveControl(); // the unmodified certificate still works afterwards
    }

    /// Each AccessDecision field substituted while keeping the original witness signature.
    function test_E01_DecisionFieldSubstitution() public {
        for (uint256 i = 0; i < 8; i++) {
            DecisionCertificate memory c = cert;
            AccessDecision memory d = c.decision;
            AccessDecision memory x = AccessDecision(
                d.requestDigest, d.result, d.credentialDigest, d.stateSequence, d.witnessSetVersion,
                d.sourceBlockNumber, d.sourceBlockHash, d.expiresAt
            );
            ErrorCode want = ErrorCode.BAD_SIGNATURE;
            if (i == 0) (x.requestDigest, want) = (keccak256("other request"), ErrorCode.WRONG_SUBJECT);
            if (i == 1) x.result = 0;
            if (i == 2) x.credentialDigest = keccak256("other credentials");
            if (i == 3) x.stateSequence += 1;
            if (i == 4) (x.witnessSetVersion, want) = (x.witnessSetVersion + 1, ErrorCode.STALE_STATE);
            if (i == 5) x.sourceBlockNumber += 1;
            if (i == 6) x.sourceBlockHash = keccak256("other block");
            if (i == 7) x.expiresAt -= 1;
            DecisionCertificate memory mc = DecisionCertificate(x, c.signatures);
            rejectsWithoutState(r, mc, recs, want, string.concat("decision field ", vm.toString(i)));
        }
    }

    /// Records that do not hash to the signed credentialDigest.
    function test_E01_RecordSubstitution() public {
        CredentialRecord[] memory x = new CredentialRecord[](recs.length);
        for (uint256 i = 0; i < recs.length; i++) {
            x[i] = recs[i];
        }
        x[0].issuer = h2;
        rejectsWithoutState(r, cert, x, ErrorCode.WRONG_SUBJECT, "issuer substituted");
        CredentialRecord[] memory fewer = new CredentialRecord[](1);
        fewer[0] = recs[0];
        rejectsWithoutState(r, cert, fewer, ErrorCode.WRONG_SUBJECT, "record dropped");
    }

    /// A decision signed in another destination's domain (another KSSC address) does not verify here.
    function test_E01_DecisionDomainBinding() public {
        DecisionCertificate memory c;
        c.decision = cert.decision;
        c.signatures = new bytes[](1);
        c.signatures[0] = sig(witnessPk, HMBCHash.accessDecisionDigest(cert.decision, DBC_CHAIN_ID, mallory));
        rejectsWithoutState(r, c, recs, ErrorCode.BAD_SIGNATURE, "foreign KSSC domain");
        c.signatures[0] = sig(witnessPk, HMBCHash.accessDecisionDigest(cert.decision, DBC_CHAIN_ID + 1, address(kssc)));
        rejectsWithoutState(r, c, recs, ErrorCode.BAD_SIGNATURE, "foreign chain domain");
    }

    /// A request signed for another destination, certified in THIS DBC's domain by the witness.
    /// Repaired-e rejects with WRONG_DESTINATION (the request's own destination binding).
    function test_E01_RequestForOtherDestinationCertifiedHere() public {
        AccessRequest memory x = r;
        x.kssc = mallory;
        x.destinationChainId = DBC_CHAIN_ID + 7;
        DecisionCertificate memory c = certify(decisionFor(x, RESULT_ALLOW, recs, cp), witnessPk);
        rejectsWithoutState(x, c, recs, ErrorCode.WRONG_DESTINATION, "request for another destination");
    }

    function test_E01_SignatureEncodings() public {
        DecisionCertificate memory c;
        c.decision = cert.decision;
        c.signatures = new bytes[](2);
        c.signatures[0] = cert.signatures[0];
        c.signatures[1] = cert.signatures[0];
        rejectsWithoutState(r, c, recs, ErrorCode.DUPLICATE_SIGNER, "duplicate signer");

        c.signatures = new bytes[](0);
        rejectsWithoutState(r, c, recs, ErrorCode.INSUFFICIENT_QUORUM, "no signatures");

        // High-s malleated twin of a valid signature: (r, n - s, v ^ 1) recovers the same key.
        bytes memory s0 = cert.signatures[0];
        bytes32 rr;
        bytes32 ss;
        uint8 v;
        assembly {
            rr := mload(add(s0, 32))
            ss := mload(add(s0, 64))
            v := byte(0, mload(add(s0, 96)))
        }
        uint256 n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141;
        c.signatures = new bytes[](1);
        c.signatures[0] = abi.encodePacked(rr, bytes32(n - uint256(ss)), v == 27 ? uint8(28) : uint8(27));
        rejectsWithoutState(r, c, recs, ErrorCode.BAD_SIGNATURE, "high-s malleable signature");

        c.signatures[0] = abi.encodePacked(rr, ss); // 64-byte compact form
        rejectsWithoutState(r, c, recs, ErrorCode.BAD_SIGNATURE, "64-byte signature");
    }

    /// Two different requests that reuse nonce 1: the second is REPLAY although both are certified.
    function test_E01_NonceReuseAcrossDifferentRequests() public {
        bytes32 g1 = acsc.consumeDecision(r, cert, recs);
        vm.warp(block.timestamp + 1);
        AccessRequest memory r2 = aliceRequest(1); // same nonce, later expiresAt -> new digest
        (bytes32 d2, ErrorCode code) = submit(r2, signRequest(r2, alicePk), aliceBundle());
        assertCode(code, ErrorCode.NONE, "PBC accepts the second request (distinct digest)");
        DecisionCertificate memory c2 = certify(decisionFor(r2, RESULT_ALLOW, recs, cp), witnessPk);
        expectRejected(ErrorCode.REPLAY);
        acsc.consumeDecision(r2, c2, recs);
        (,,,,, bool first) = kssc.getGrant(g1);
        (,,,,, bool second) = kssc.getGrant(HMBCHash.grantId(d2, address(kssc), DBC_CHAIN_ID));
        assertTrue(first && !second, "only the first use of (gid, nonce) granted");
    }

    function test_E01_DecisionExpiryBoundary() public {
        vm.warp(cert.decision.expiresAt);
        rejectsWithoutState(r, cert, recs, ErrorCode.EXPIRED, "now == decision.expiresAt");
        vm.warp(cert.decision.expiresAt - 1);
        test_E01_PositiveControl();
    }

    function test_E01_RequestExpiryAtDbc() public {
        AccessDecision memory d = cert.decision;
        d.expiresAt = cp.expiresAt; // decision outlives the request, checkpoint still fresh
        DecisionCertificate memory c = certify(d, witnessPk);
        vm.warp(r.expiresAt);
        rejectsWithoutState(r, c, recs, ErrorCode.EXPIRED, "now == request.expiresAt");
    }
}
