// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {Vm} from "./utils/Vm.sol";
import {
    Profile,
    LogDetailMode,
    ErrorCode,
    HMBCHash,
    AccessRequest,
    CredentialRecord,
    DecisionCertificate,
    StateCheckpoint,
    RESULT_ALLOW
} from "../src/types/ProtocolTypes.sol";
import {LSC} from "../src/LSC.sol";
import {PSC} from "../src/PSC.sol";

/// A-E2 / E03 audit correspondence. Expectations written before the first run
/// (evidence/ae2-first-run.txt). REQUEST_LOGGED / PBC_DECIDED / DBC_AUTHORIZED / OUTCOME_RECORDED
/// are ledger events; RELEASE_INTENT / RELEASE_SENT are agent 2's off-chain worker states.
abstract contract AuditBase is HMBCFixture {
    bytes32 internal constant GRANT_ISSUED_TOPIC =
        keccak256("GrantIssued(bytes32,bytes32,address,bytes32,uint64,uint64,bytes32,bool,uint256)");
    bytes32 internal constant ACCESS_LOG_TOPIC =
        keccak256("AccessLog(uint256,bytes32,address,bytes32,bool,uint8,bytes32,bytes32,address)");

    /// A granted request whose outcome is never reported stays visibly pending on the PBC
    /// (FORWARDED, no outcome log). Holds in all profiles; reconciliation needs an honest reporter.
    function test_E03_DroppedOutcomeStaysVisiblyPending() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        bytes32 g = deliver(r, recs, digest, RESULT_ALLOW);
        (,,,,, bool allowed) = kssc.getGrant(g);
        assertTrue(allowed, "DBC_AUTHORIZED");
        assertTrue(psc.getRequest(digest).status == PSC.RequestStatus.FORWARDED, "PBC still pending");
        assertEq(lsc.outcomeLogId(digest), 0, "no OUTCOME_RECORDED");
    }

    /// The relay reports a "released" outcome for a request the DBC never authorized (the relay
    /// dropped the delivery). Paper: the PBC records it (SPEC_GAP; III-D3 logs whatever response
    /// arrives). Repaired-e: the unattested path is disabled (A1-0008), so nothing is recorded;
    /// attested-path cases are in OutcomeEvidence.t.sol.
    function test_E03_OutcomeWithoutDbcGrant() public {
        publishTrustLists(one(alice));
        registerAlice();
        (, bytes32 digest,) = aliceForwarded(1);
        bytes32 g = HMBCHash.grantId(digest, address(kssc), DBC_CHAIN_ID);
        (,,,,, bool allowed) = kssc.getGrant(g);
        assertFalse(allowed, "no DBC grant exists");
        vm.prank(relay);
        if (profile() == Profile.REPAIRED_E) expectRejected(ErrorCode.WRONG_PROFILE);
        psc.reportOutcome(digest, g, keccak256("synthetic-outcome:released"));
        assertTrue(
            (lsc.outcomeLogId(digest) != 0) != (profile() == Profile.REPAIRED_E),
            "outcome without DBC authorization: recorded in paper profiles only"
        );
    }

    /// Cross-chain correlation of a legitimate access: the DBC's GrantIssued and AccessLog carry the
    /// PBC request digest that LSC logged. (Paper: the reference is whatever the relay supplied;
    /// see DecisionBinding test_E01_RelayFabricatedRequest for the uncorrelated case.)
    function test_E03_EventsCorrelateWithPbcRequest() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        vm.recordLogs();
        bytes32 g = deliver(r, recs, digest, RESULT_ALLOW);
        Vm.Log[] memory logs = vm.getRecordedLogs();
        bool sawGrant;
        bool sawAccess;
        for (uint256 i = 0; i < logs.length; i++) {
            if (logs[i].topics[0] == GRANT_ISSUED_TOPIC) {
                sawGrant = true;
                assertEq(logs[i].topics[1], g, "GrantIssued.grantId");
                assertEq(logs[i].topics[2], digest, "GrantIssued.requestDigest == PBC digest");
            }
            if (logs[i].topics[0] == ACCESS_LOG_TOPIC) {
                sawAccess = true;
                assertEq(logs[i].topics[2], digest, "AccessLog.requestRef == PBC digest");
            }
        }
        assertTrue(sawGrant && sawAccess, "both DBC events emitted");
        assertTrue(lsc.firstRequestLogId(digest) != 0, "REQUEST_LOGGED on the PBC for the same digest");
    }

    /// LSC detail modes (C12): COMPLETE_DETAILS keeps the details; HASH_ONLY keeps only their hash.
    /// Either way the stored hash matches the PSC's request-detail encoding.
    function test_E03_LogDetailMode() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(1);
        (bytes32 digest,) = submit(r, signRequest(r, alicePk), aliceBundle());
        (LSC.LogEntry memory e, bytes memory details) = lsc.getLog(lsc.firstRequestLogId(digest));
        bytes memory expected =
            abi.encode(r.gid, r.dataId, r.action, r.destinationChainId, r.kssc, r.nonce, r.expiresAt, relay);
        assertTrue(e.kind == LSC.LogKind.REQUEST, "REQUEST log");
        assertEq(e.detailsHash, keccak256(expected), "details hash matches the request");
        if (logDetailMode() == LogDetailMode.COMPLETE_DETAILS) {
            assertEq(keccak256(details), keccak256(expected), "complete details stored");
        } else {
            assertEq(details.length, 0, "hash-only stores no details");
        }
    }
}

contract AuditPaperStrictTest is AuditBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_STRICT;
    }
}

contract AuditPaperStrictHashOnlyTest is AuditBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_STRICT;
    }

    function logDetailMode() internal pure override returns (LogDetailMode) {
        return LogDetailMode.HASH_ONLY;
    }
}

contract AuditPaperMinimalTest is AuditBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_MINIMAL;
    }
}

contract AuditRepairedTest is AuditBase {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    /// Trust boundary, not a pass: the DBC cannot see PBC logs, so a witness-signed decision for a
    /// request that was never submitted to the PBC is granted. Correspondence in repaired-e therefore
    /// rests on the trusted-witness assumption (E: one witness; F replaces it with q = 3 of 4).
    function test_E03_TrustedWitnessBoundaryUnloggedRequest() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(9); // never submitted to the PBC
        bytes32 digest = HMBCHash.accessRequestDigest(r);
        CredentialRecord[] memory recs = verifiedRecords(alice, aliceBundle());
        StateCheckpoint memory cp = acceptCheckpoint();
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, cp), witnessPk);
        bytes32 g = acsc.consumeDecision(r, c, recs);
        (,,,,, bool allowed) = kssc.getGrant(g);
        assertTrue(allowed, "granted on witness authority alone");
        assertEq(lsc.firstRequestLogId(digest), 0, "no PBC request log behind this grant");
    }
}

contract AuditRepairedHashOnlyTest is AuditBase {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    function logDetailMode() internal pure override returns (LogDetailMode) {
        return LogDetailMode.HASH_ONLY;
    }
}
