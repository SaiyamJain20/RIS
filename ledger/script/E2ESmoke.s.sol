// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {Vm, VM_ADDRESS} from "../test/utils/Vm.sol";
import {
    Profile,
    ErrorCode,
    HMBCHash,
    Registration,
    RoleCertificate,
    SignedRoleCertificate,
    RevocationList,
    TemporalAcl,
    TempAclEntry,
    AccessRequest,
    TemporalClaim,
    CredentialBundle,
    CredentialRecord,
    AccessDecision,
    DecisionCertificate,
    StateCheckpoint,
    ForwardedRequest,
    ACTION_READ,
    RESULT_ALLOW
} from "../src/types/ProtocolTypes.sol";
import {TMSC} from "../src/TMSC.sol";
import {RSC} from "../src/RSC.sol";
import {PSC} from "../src/PSC.sol";
import {KSSC} from "../src/KSSC.sol";
import {ACSC} from "../src/ACSC.sol";
import {FixtureConfig} from "./FixtureConfig.sol";

/// Ledger-only two-chain smoke of the legitimate Alice flow against a live deployment
/// (tools/e2e_smoke.sh). This is NOT the integration run: it signs as the user, witness and relay
/// inside Forge, so it exercises the contracts/ABI/chain bindings, not agent 2's services.
///   STAGE=pbc-setup    PBC: H1/H2 CRLs, H1 TempACL (Alice on duty), Alice registers
///   STAGE=pbc-request  PBC: relay submits Alice's signed request; saves request + records
///   STAGE=dbc-deliver  DBC: repaired-e: witness checkpoint + decision; paper: relay policyEnf
///   STAGE=pbc-outcome  PBC: relay reports the outcome
/// Env: STAGE, OUT_DIR, NONCE, and the deployed addresses TMSC, RSC, PSC (PBC) / ACSC, KSSC (DBC).
contract E2ESmoke {
    Vm internal constant vm = Vm(VM_ADDRESS);

    function run() external {
        bytes32 stage = keccak256(bytes(vm.envString("STAGE")));
        if (stage == keccak256("pbc-setup")) _setup();
        else if (stage == keccak256("pbc-request")) _request();
        else if (stage == keccak256("dbc-deliver")) _deliver();
        else if (stage == keccak256("pbc-outcome")) _outcome();
        else revert("unknown STAGE");
    }

    function _pk(string memory label) internal pure returns (uint256) {
        return FixtureConfig.key(label);
    }

    function _sig(uint256 pk, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    function _aliceCert(TMSC tmsc) internal view returns (SignedRoleCertificate memory sc) {
        bytes32[] memory roles = new bytes32[](1);
        roles[0] = FixtureConfig.ROLE_DOCTOR;
        // Fixed validity window (2023-11-14 .. 2036-07-18) so both stages present the same certificate.
        RoleCertificate memory c =
            RoleCertificate(vm.addr(_pk("H1-root")), vm.addr(_pk("alice")), roles, 101, 1_700_000_000, 2_100_000_000);
        sc = SignedRoleCertificate(c, _sig(_pk("H1-root"), HMBCHash.roleCertificateDigest(c, block.chainid, address(tmsc))));
    }

    function _setup() internal {
        TMSC tmsc = TMSC(vm.envAddress("TMSC"));
        RSC rsc = RSC(vm.envAddress("RSC"));
        uint64 t = uint64(block.timestamp);
        address h1 = vm.addr(_pk("H1-root"));
        address h2 = vm.addr(_pk("H2-root"));
        RevocationList memory crl1 = RevocationList(h1, 1, t + 1 days, new uint64[](0));
        RevocationList memory crl2 = RevocationList(h2, 1, t + 1 days, new uint64[](0));
        TemporalAcl memory acl;
        acl.authority = h1;
        acl.version = 1;
        acl.validUntil = t + 1 days;
        acl.entries = new TempAclEntry[](1);
        acl.entries[0] = TempAclEntry(vm.addr(_pk("alice")), FixtureConfig.ROLE_ON_DUTY, t - 60, t + 8 hours);

        vm.startBroadcast(_pk("H1-ca-admin"));
        tmsc.updateRevocationList(crl1, _sig(_pk("H1-root"), HMBCHash.revocationListDigest(crl1, block.chainid, address(tmsc))));
        tmsc.updateTemporalAcl(acl, _sig(_pk("H1-root"), HMBCHash.temporalAclDigest(acl, block.chainid, address(tmsc))));
        vm.stopBroadcast();
        vm.startBroadcast(_pk("H2-ca-admin"));
        tmsc.updateRevocationList(crl2, _sig(_pk("H2-root"), HMBCHash.revocationListDigest(crl2, block.chainid, address(tmsc))));
        vm.stopBroadcast();

        SignedRoleCertificate memory cert = _aliceCert(tmsc);
        Registration memory reg = Registration(
            vm.addr(_pk("alice")),
            HMBCHash.roleCertificateDigest(cert.cert, block.chainid, address(tmsc)),
            keccak256("HMBC.recipient-key.alice"),
            t + 600
        );
        bytes memory possession = _sig(_pk("alice"), HMBCHash.registrationDigest(reg, block.chainid, address(rsc)));
        vm.startBroadcast(_pk("relay")); // the user API submits; authority is Alice's signature
        rsc.register(reg, possession, cert);
        vm.stopBroadcast();
    }

    function _request() internal {
        TMSC tmsc = TMSC(vm.envAddress("TMSC"));
        PSC psc = PSC(vm.envAddress("PSC"));
        address alice = vm.addr(_pk("alice"));
        AccessRequest memory r = AccessRequest(
            block.chainid,
            FixtureConfig.DBC_CHAIN_ID,
            address(psc),
            vm.envAddress("KSSC"),
            alice,
            FixtureConfig.DATA_P1,
            ACTION_READ,
            FixtureConfig.POLICY_VERSION,
            tmsc.authEpoch(),
            0,
            vm.envUint("NONCE"),
            uint64(block.timestamp) + FixtureConfig.REQUEST_TTL,
            keccak256("HMBC.recipient-key.alice")
        );
        CredentialBundle memory b;
        b.certificates = new SignedRoleCertificate[](1);
        b.certificates[0] = _aliceCert(tmsc);
        b.temporalClaims = new TemporalClaim[](1);
        b.temporalClaims[0] = TemporalClaim(vm.addr(_pk("H1-root")), FixtureConfig.ROLE_ON_DUTY);
        (ErrorCode code, CredentialRecord[] memory recs) = tmsc.checkCredentials(alice, b, uint64(block.timestamp));
        require(code == ErrorCode.NONE, "credentials do not verify");
        bytes memory userSig = _sig(_pk("alice"), HMBCHash.accessRequestDigest(r));

        vm.startBroadcast(_pk("relay"));
        (bytes32 digest, ErrorCode decided) = psc.requestAccess(r, userSig, b);
        vm.stopBroadcast();
        require(decided == ErrorCode.NONE, "PBC denied the smoke request");
        vm.writeFile(
            string.concat(vm.envString("OUT_DIR"), "/request.hex"),
            vm.toString(abi.encode(r, recs, digest, block.number, blockhash(block.number - 1)))
        );
    }

    struct Pending {
        AccessRequest r;
        CredentialRecord[] recs;
        bytes32 digest;
        uint256 pbcBlock;
        bytes32 pbcHash;
    }

    function _loadPending() internal view returns (Pending memory p) {
        (p.r, p.recs, p.digest, p.pbcBlock, p.pbcHash) = abi.decode(
            vm.parseBytes(vm.readFile(string.concat(vm.envString("OUT_DIR"), "/request.hex"))),
            (AccessRequest, CredentialRecord[], bytes32, uint256, bytes32)
        );
    }

    function _deliver() internal {
        ACSC acsc = ACSC(vm.envAddress("ACSC"));
        KSSC kssc = KSSC(vm.envAddress("KSSC"));
        Pending memory p = _loadPending();
        bytes32 grantId;
        if (acsc.profile() == Profile.REPAIRED_E) {
            StateCheckpoint memory cp = _checkpoint(kssc, p);
            bytes[] memory cpSigs = new bytes[](1);
            cpSigs[0] = _sig(_pk("witness-1"), HMBCHash.stateCheckpointDigest(cp, block.chainid, address(kssc)));
            DecisionCertificate memory c = _certificate(kssc, p, cp.sequence);
            vm.startBroadcast(_pk("relay"));
            kssc.acceptState(cp, cpSigs);
            grantId = acsc.consumeDecision(p.r, c, p.recs);
            vm.stopBroadcast();
        } else {
            vm.startBroadcast(_pk("relay"));
            (, grantId) = acsc.policyEnf(ForwardedRequest(p.digest, p.r.gid, p.r.dataId, p.r.action), p.recs);
            vm.stopBroadcast();
        }
        (,,,,, bool allowed) = kssc.getGrant(grantId);
        require(allowed, "no grant on the DBC");
        vm.writeFile(string.concat(vm.envString("OUT_DIR"), "/grant.hex"), vm.toString(abi.encode(p.digest, grantId)));
    }

    /// The witness's view of PBC state for this smoke (one honest witness, q = 1 of 1).
    function _checkpoint(KSSC kssc, Pending memory p) internal view returns (StateCheckpoint memory cp) {
        (bool has, StateCheckpoint memory cur) = kssc.currentCheckpoint();
        cp = StateCheckpoint(
            has ? cur.sequence + 1 : 1,
            p.r.authEpoch,
            p.r.policyVersion,
            0,
            FixtureConfig.WITNESS_SET_VERSION,
            p.r.sourceChainId,
            p.r.psc,
            p.pbcBlock,
            p.pbcHash,
            uint64(block.timestamp) + FixtureConfig.CHECKPOINT_TTL
        );
    }

    function _certificate(KSSC kssc, Pending memory p, uint64 sequence)
        internal
        view
        returns (DecisionCertificate memory c)
    {
        c.decision = AccessDecision(
            p.digest,
            RESULT_ALLOW,
            HMBCHash.hashCredentialRecords(p.recs),
            sequence,
            FixtureConfig.WITNESS_SET_VERSION,
            p.pbcBlock,
            p.pbcHash,
            0
        );
        // A decision may not outlive its checkpoint (both in DBC time) or the request.
        uint64 cpExpiry = uint64(block.timestamp) + FixtureConfig.CHECKPOINT_TTL;
        c.decision.expiresAt = p.r.expiresAt < cpExpiry ? p.r.expiresAt : cpExpiry;
        c.signatures = new bytes[](1);
        c.signatures[0] = _sig(_pk("witness-1"), HMBCHash.accessDecisionDigest(c.decision, block.chainid, address(kssc)));
    }

    function _outcome() internal {
        PSC psc = PSC(vm.envAddress("PSC"));
        (bytes32 digest, bytes32 grantId) = abi.decode(
            vm.parseBytes(vm.readFile(string.concat(vm.envString("OUT_DIR"), "/grant.hex"))), (bytes32, bytes32)
        );
        vm.startBroadcast(_pk("relay"));
        psc.reportOutcome(digest, grantId, keccak256("HMBC.smoke.outcome.released"));
        vm.stopBroadcast();
        require(psc.getRequest(digest).status == PSC.RequestStatus.OUTCOME_RECORDED, "outcome not recorded");
    }
}
