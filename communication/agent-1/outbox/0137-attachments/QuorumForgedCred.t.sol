// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;
// Agent 1 SCRATCH test (not part of the ledger module; run on a git-archive copy of 85c59f5).
// Question (RQ2-F trust matrix, governance-quorum row): does the DBC's on-chain policy check bound a
// COMPROMISED witness quorum (3 of 4) to requesters whose real credentials satisfy the policy?
// Setup: nothing is registered or submitted on the PBC. The requester and the credential issuer are
// arbitrary addresses that no TMSC ever saw. Classification: tested reconstruction result OUTSIDE the
// f=1 bound (three Byzantine signers).
import {HMBCFixture} from "./utils/Fixture.sol";
import {Profile, HMBCHash, AccessRequest, CredentialRecord, StateCheckpoint, AccessDecision,
    DecisionCertificate, RESULT_ALLOW, CREDENTIAL_LONG_TERM, CREDENTIAL_TEMPORAL, ErrorCode, Rejected}
    from "../src/types/ProtocolTypes.sol";

contract QuorumForgedCredF is HMBCFixture {
    address constant MALLORY = address(0xBAD);
    address constant FAKE_ISSUER = address(0xF00);

    function profile() internal pure override returns (Profile) { return Profile.REPAIRED_F; }

    function pks(uint256 n) internal view returns (uint256[] memory xs) {
        xs = new uint256[](n);
        for (uint256 i = 0; i < n; i++) xs[i] = witnessPks[i];
    }

    function cert(AccessDecision memory d, uint256[] memory k) internal view returns (DecisionCertificate memory c) {
        c.decision = d;
        c.signatures = sortedSigs(k, HMBCHash.accessDecisionDigest(d, DBC_CHAIN_ID, address(kssc)));
    }

    function forged(bool withOnDuty) internal view returns (CredentialRecord[] memory recs) {
        recs = new CredentialRecord[](withOnDuty ? 2 : 1);
        uint64 until = uint64(block.timestamp) + 1 days;
        recs[0] = CredentialRecord(FAKE_ISSUER, ROLE_DOCTOR, CREDENTIAL_LONG_TERM, 1, 0, until);
        if (withOnDuty) recs[1] = CredentialRecord(FAKE_ISSUER, ROLE_ON_DUTY, CREDENTIAL_TEMPORAL, 1, 0, until);
    }

    function setupCheckpoint() internal returns (StateCheckpoint memory cp) {
        cp = checkpointNow();
        kssc.acceptState(cp, sortedSigs(pks(3), HMBCHash.stateCheckpointDigest(cp, DBC_CHAIN_ID, address(kssc))));
    }

    /// Three signers + forged records that fit the policy shape: the DBC grants.
    function test_quorum_forged_credentials_get_a_grant() public {
        StateCheckpoint memory cp = setupCheckpoint();
        AccessRequest memory r = accessRequest(MALLORY, keccak256("mallory-key"), 1);
        CredentialRecord[] memory recs = forged(true);
        assertTrue(!tmsc.isAuthority(FAKE_ISSUER), "issuer is no authority on the PBC");
        bytes32 g = acsc.consumeDecision(r, cert(decisionFor(r, RESULT_ALLOW, recs, cp), pks(3)), recs);
        assertTrue(g != bytes32(0), "grant created");
        (, bytes32 dataId, address gid,,, bool allowed) = kssc.getGrant(g);
        assertTrue(allowed && gid == MALLORY && dataId == DATA_P1, "grant is for Mallory on DATA_P1");
    }

    /// Control 1: the same forged ALLOW with only two signers is refused (f=1 holds).
    function test_control_two_signers_refused() public {
        StateCheckpoint memory cp = setupCheckpoint();
        AccessRequest memory r = accessRequest(MALLORY, keccak256("mallory-key"), 1);
        CredentialRecord[] memory recs = forged(true);
        DecisionCertificate memory c = cert(decisionFor(r, RESULT_ALLOW, recs, cp), pks(2));
        vm.expectRevert(abi.encodeWithSelector(Rejected.selector, ErrorCode.INSUFFICIENT_QUORUM));
        acsc.consumeDecision(r, c, recs);
    }

    /// Control 2: the on-chain policy is still evaluated: forged records that do not fit it are refused.
    function test_control_records_not_fitting_policy_refused() public {
        StateCheckpoint memory cp = setupCheckpoint();
        AccessRequest memory r = accessRequest(MALLORY, keccak256("mallory-key"), 1);
        CredentialRecord[] memory recs = forged(false);
        DecisionCertificate memory c = cert(decisionFor(r, RESULT_ALLOW, recs, cp), pks(3));
        vm.expectRevert(abi.encodeWithSelector(Rejected.selector, ErrorCode.POLICY_DENIED));
        acsc.consumeDecision(r, c, recs);
    }
}
