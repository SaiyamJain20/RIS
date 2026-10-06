// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "../test/utils/Fixture.sol";
import {Profile, ErrorCode, HMBCHash} from "../src/types/ProtocolTypes.sol";

/// PENDING repaired-e property (SPEC section 4, E03 repair "DBC grant evidence"): the PBC must not
/// record an OUTCOME for a request without evidence that the DBC authorized it. Written before the
/// repair exists; it is EXPECTED TO FAIL until RFC A1-0005 is accepted and implemented.
/// Run: FOUNDRY_PROFILE=pending forge test --root ledger
contract OutcomeEvidencePendingTest is HMBCFixture {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    function test_PENDING_E03_OutcomeRequiresDbcGrantEvidence() public {
        publishTrustLists(one(alice));
        registerAlice();
        (, bytes32 digest,) = aliceForwarded(1);
        bytes32 g = HMBCHash.grantId(digest, address(kssc), DBC_CHAIN_ID);
        vm.prank(relay);
        // No DBC grant exists. Desired: rejected (no attested DBC grant), no outcome log.
        try psc.reportOutcome(digest, g, keccak256("synthetic-outcome:released")) {
            revert("PENDING: outcome recorded without DBC grant evidence");
        } catch {}
        assertEq(lsc.outcomeLogId(digest), 0, "no outcome without DBC evidence");
    }
}
