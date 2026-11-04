// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {
    Profile,
    ErrorCode,
    HMBCHash,
    AccessRequest,
    CredentialRecord,
    GrantReceipt,
    RESULT_ALLOW
} from "../src/types/ProtocolTypes.sol";
import {PSC} from "../src/PSC.sol";

/// E03 repair (A1-0008 revision 2; ACK A3-0005 agent 3, A2-0002 agent 2): in repaired-e the PBC
/// records an outcome only with a witness-signed GrantReceipt matching its forwarded record and an
/// existing allowed DBC grant. Written BEFORE the implementation (first run:
/// evidence/receipt-first-run.txt). The receipt is grant evidence, never delivery evidence.
contract OutcomeEvidenceRepairedTest is HMBCFixture {
    bytes32 internal constant OUTCOME = keccak256("synthetic-outcome:released");
    AccessRequest internal r;
    bytes32 internal digest;
    bytes32 internal grantId;
    GrantReceipt internal g;

    function profile() internal pure virtual override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    function setUp() public override {
        super.setUp();
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory req, bytes32 d, CredentialRecord[] memory recs) = aliceForwarded(1);
        r = req;
        digest = d;
        grantId = deliver(req, recs, d, RESULT_ALLOW);
        g = receiptFor(grantId);
    }

    function rejects(bytes32 d, GrantReceipt memory x, bytes[] memory sigs, ErrorCode code, string memory what)
        internal
    {
        vm.prank(relay);
        expectRejected(code);
        psc.reportAttestedOutcome(d, OUTCOME, x, sigs);
        assertTrue(psc.getRequest(digest).status == PSC.RequestStatus.FORWARDED, string.concat(what, ": still pending"));
        assertEq(lsc.outcomeLogId(digest), 0, string.concat(what, ": no outcome log"));
    }

    function test_E03_AttestedOutcomeRecorded() public {
        GrantReceipt memory x = g;
        vm.prank(relay);
        uint256 logId = psc.reportAttestedOutcome(digest, OUTCOME, x, signReceipt(x, witnessPk));
        assertTrue(logId > lsc.firstRequestLogId(digest), "outcome logged after the request");
        assertEq(lsc.outcomeLogId(digest), logId, "OUTCOME_RECORDED");
        assertTrue(psc.getRequest(digest).status == PSC.RequestStatus.OUTCOME_RECORDED, "status");
    }

    /// Each receipt field substituted AND re-signed by the witness: the binding checks, not the
    /// signature, must reject. Codes follow the A1-0008 check order.
    function test_E03_ReceiptFieldSubstitution() public {
        for (uint256 i = 0; i < 10; i++) {
            GrantReceipt memory x = g;
            ErrorCode want;
            if (i == 0) (x.requestDigest, want) = (keccak256("other request"), ErrorCode.WRONG_SUBJECT);
            if (i == 1) (x.grantId, want) = (keccak256("other grant"), ErrorCode.WRONG_DESTINATION);
            if (i == 2) (x.gid, want) = (bob, ErrorCode.WRONG_SUBJECT);
            if (i == 3) (x.dataId, want) = (keccak256("HMBC.data.P2.MHR"), ErrorCode.WRONG_SUBJECT);
            if (i == 4) (x.keyEpoch, want) = (1, ErrorCode.WRONG_EPOCH);
            if (i == 5) (x.grantExpiresAt, want) = (r.expiresAt + 1, ErrorCode.MALFORMED);
            if (i == 6) (x.grantExpiresAt, want) = (0, ErrorCode.MALFORMED);
            if (i == 7) (x.witnessSetVersion, want) = (witnessSetVersion() + 1, ErrorCode.STALE_STATE);
            if (i == 8) (x.dbcChainId, want) = (DBC_CHAIN_ID + 1, ErrorCode.WRONG_DESTINATION);
            if (i == 9) (x.kssc, want) = (mallory, ErrorCode.WRONG_DESTINATION);
            rejects(digest, x, signReceipt(x, witnessPk), want, string.concat("receipt field case ", vm.toString(i)));
        }
        test_E03_AttestedOutcomeRecorded(); // the genuine receipt still works afterwards
    }

    function test_E03_ReceiptSignatureChecks() public {
        GrantReceipt memory x = g;
        bytes[] memory good = signReceipt(x, witnessPk);
        x.dbcBlockHash = keccak256("other block"); // informational field, but signed
        rejects(digest, x, good, ErrorCode.BAD_SIGNATURE, "modified after signing");
        x = g;
        rejects(digest, x, signReceipt(x, malloryPk), ErrorCode.BAD_SIGNATURE, "non-witness signer");
        rejects(digest, x, new bytes[](0), ErrorCode.INSUFFICIENT_QUORUM, "no signature");
        bytes[] memory dup = new bytes[](2);
        dup[0] = good[0];
        dup[1] = good[0];
        rejects(digest, x, dup, ErrorCode.DUPLICATE_SIGNER, "duplicate signature");
        bytes[] memory foreignDomain = new bytes[](1);
        foreignDomain[0] = sig(witnessPk, HMBCHash.grantReceiptDigest(x, PBC_CHAIN_ID, mallory));
        rejects(digest, x, foreignDomain, ErrorCode.BAD_SIGNATURE, "signed for another PSC");
    }

    function test_E03_ReceiptCallerStateAndReplay() public {
        GrantReceipt memory x = g;
        bytes[] memory sigs = signReceipt(x, witnessPk);
        vm.prank(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        psc.reportAttestedOutcome(digest, OUTCOME, x, sigs);
        rejects(keccak256("never forwarded"), x, sigs, ErrorCode.WRONG_SUBJECT, "unknown request");
        vm.prank(relay);
        psc.reportAttestedOutcome(digest, OUTCOME, x, sigs);
        vm.prank(relay);
        expectRejected(ErrorCode.REPLAY);
        psc.reportAttestedOutcome(digest, OUTCOME, x, sigs);
    }

    /// The unattested paper path is disabled in repaired-e.
    function test_E03_UnattestedOutcomeDisabled() public {
        vm.prank(relay);
        expectRejected(ErrorCode.WRONG_PROFILE);
        psc.reportOutcome(digest, grantId, OUTCOME);
        assertEq(lsc.outcomeLogId(digest), 0, "no outcome");
    }

    /// Former test-pending control: a forwarded request that the DBC never authorized cannot get a
    /// PBC outcome (no unattested path; an honest witness has no grant to attest; a forged receipt fails).
    function test_E03_NoOutcomeWithoutDbcGrantEvidence() public {
        AccessRequest memory r2 = aliceRequest(2);
        (bytes32 d2,) = submit(r2, signRequest(r2, alicePk), aliceBundle());
        bytes32 g2 = HMBCHash.grantId(d2, address(kssc), DBC_CHAIN_ID);
        (,,,,, bool allowed) = kssc.getGrant(g2);
        assertFalse(allowed, "DBC never authorized request 2");
        vm.prank(relay);
        expectRejected(ErrorCode.WRONG_PROFILE);
        psc.reportOutcome(d2, g2, OUTCOME);
        GrantReceipt memory forged = GrantReceipt(
            d2, g2, alice, DATA_P1, 0, r2.expiresAt, witnessSetVersion(), DBC_CHAIN_ID, address(kssc), 1, bytes32(0)
        );
        vm.prank(relay);
        expectRejected(ErrorCode.BAD_SIGNATURE);
        psc.reportAttestedOutcome(d2, OUTCOME, forged, signReceipt(forged, malloryPk));
        assertEq(lsc.outcomeLogId(d2), 0, "no outcome without DBC grant evidence");
    }

    /// A receipt attests a past DBC fact: reconciliation after the grant expired is allowed (it never
    /// re-authorizes a release).
    function test_E03_LateReconciliationAfterGrantExpiry() public {
        GrantReceipt memory x = g;
        vm.warp(x.grantExpiresAt + 3600);
        vm.prank(relay);
        psc.reportAttestedOutcome(digest, OUTCOME, x, signReceipt(x, witnessPk));
        assertTrue(lsc.outcomeLogId(digest) != 0, "late outcome recorded");
    }
}

contract OutcomeEvidencePaperStrictTest is HMBCFixture {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_STRICT;
    }

    /// Paper profiles keep the unattested outcome path (observed SPEC_GAP); the attested entry is off.
    function test_E03_AttestedEntryDisabledInPaperProfiles() public {
        GrantReceipt memory x;
        vm.prank(relay);
        expectRejected(ErrorCode.WRONG_PROFILE);
        psc.reportAttestedOutcome(bytes32(uint256(1)), bytes32(0), x, new bytes[](0));
    }
}
