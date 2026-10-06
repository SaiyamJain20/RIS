// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {Vm, VM_ADDRESS} from "../test/utils/Vm.sol";
import {
    HMBCHash,
    Registration,
    RoleCertificate,
    RevocationList,
    TemporalAcl,
    TempAclEntry,
    AccessRequest,
    CredentialRecord,
    AccessDecision,
    StateCheckpoint,
    ACTION_READ,
    RESULT_ALLOW,
    CREDENTIAL_LONG_TERM,
    CREDENTIAL_TEMPORAL
} from "../src/types/ProtocolTypes.sol";
import {SigLib} from "../src/lib/SigLib.sol";

/// E0 digest smoke vectors computed by the ledger's Solidity encoder.
/// Run: forge script script/ExportVectors.s.sol --root ledger
/// Writes exports/vectors/eip712-v0-ledger.json and exports/vectors/typed/<name>.json
/// (standard EIP-712 typed-data JSON for independent tools). Keys are TEST-ONLY, derived from
/// public labels exactly as in test/utils/Fixture.sol.
contract ExportVectors {
    Vm internal constant vm = Vm(VM_ADDRESS);

    uint256 internal constant PBC = 18545;
    uint256 internal constant DBC = 28545;
    uint64 internal constant T0 = 1_800_000_000;

    // Placeholder contract addresses for pure-encoding vectors (not a deployment).
    address internal immutable RSC_ADDR = _placeholder("rsc");
    address internal immutable TMSC_ADDR = _placeholder("tmsc");
    address internal immutable PSC_ADDR = _placeholder("psc");
    address internal immutable KSSC_ADDR = _placeholder("kssc");

    string internal constant DOMAIN_TYPE =
        '[{"name":"name","type":"string"},{"name":"version","type":"string"},{"name":"chainId","type":"uint256"},{"name":"verifyingContract","type":"address"}]';

    string[] internal _vectors;

    function _placeholder(string memory label) internal pure returns (address) {
        return address(uint160(uint256(keccak256(abi.encodePacked("hmbc-e0-vector-contract:", label)))));
    }

    function key(string memory label) internal pure returns (uint256) {
        return uint256(keccak256(abi.encodePacked("hmbc-e0-synthetic-key:", label)));
    }

    function run() external {
        address alice = vm.addr(key("alice"));
        address h1 = vm.addr(key("H1-root"));
        address witness = vm.addr(key("witness-1"));

        _registration(alice);
        _roleCertificate(h1, alice);
        _revocationList(h1);
        _temporalAcl(h1, alice);
        AccessRequest memory req = _accessRequest(alice);
        bytes32 credentialDigest = _credentialRecords(h1);
        _credentialSetCheck(h1);
        _accessDecision(HMBCHash.accessRequestDigest(req), credentialDigest, witness);
        _stateCheckpoint(witness);

        string memory doc = string.concat(
            "{",
            _kv("schemaVersion", _q("hmbc-eip712-vectors/v0-agent1")),
            ",",
            _kv("producer", _q("agent-1 ledger Solidity encoder (src/types/ProtocolTypes.sol)")),
            ",",
            _kv("interfaceVersion", _q("v0 proposed")),
            ",",
            _kv("note", _q("Synthetic TEST-ONLY keys: privateKey = keccak256('hmbc-e0-synthetic-key:' || label). Contract addresses are placeholders: address(uint160(uint256(keccak256('hmbc-e0-vector-contract:' || label)))). JSON uints are decimal strings, addresses lowercase.")),
            ",",
            _kv("vectors", _arr(_vectors)),
            "}"
        );
        vm.writeFile("exports/vectors/eip712-v0-ledger.json", doc);
    }

    // ------------------------------------------------------------------ per-type vectors

    function _registration(address alice) internal {
        Registration memory m =
            Registration(alice, keccak256("HMBC.vector.cert-digest"), keccak256("HMBC.recipient-key.alice"), T0 + 600);
        bytes32 ds = HMBCHash.domainSeparator(HMBCHash.REGISTRATION_DOMAIN, PBC, RSC_ADDR);
        string[] memory muts = new string[](6);
        for (uint256 i = 0; i < 4; i++) {
            Registration memory x = Registration(m.gid, m.certDigest, m.recipientKeyHash, m.expiresAt);
            string memory f;
            string memory v;
            if (i == 0) (f, v, x.gid) = ("gid", _addr(_flip(m.gid)), _flip(m.gid));
            if (i == 1) (f, v, x.certDigest) = ("certDigest", _b32(_flip(m.certDigest)), _flip(m.certDigest));
            if (i == 2) (f, v, x.recipientKeyHash) = ("recipientKeyHash", _b32(_flip(m.recipientKeyHash)), _flip(m.recipientKeyHash));
            if (i == 3) (f, v, x.expiresAt) = ("expiresAt", _u(m.expiresAt ^ 1), m.expiresAt ^ 1);
            muts[i] = _mutation(f, v, HMBCHash.toTypedDigest(ds, HMBCHash.hashRegistration(x)));
        }
        bytes32 sh = HMBCHash.hashRegistration(m);
        muts[4] = _mutation("domain.chainId", _u(PBC ^ 1), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.REGISTRATION_DOMAIN, PBC ^ 1, RSC_ADDR), sh));
        muts[5] = _mutation("domain.verifyingContract", _addr(_flip(RSC_ADDR)), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.REGISTRATION_DOMAIN, PBC, _flip(RSC_ADDR)), sh));
        string memory message = _obj4(
            _kv("gid", _addr(m.gid)),
            _kv("certDigest", _b32(m.certDigest)),
            _kv("recipientKeyHash", _b32(m.recipientKeyHash)),
            _kv("expiresAt", _u(m.expiresAt))
        );
        _emit(
            "Registration",
            '{"Registration":[{"name":"gid","type":"address"},{"name":"certDigest","type":"bytes32"},{"name":"recipientKeyHash","type":"bytes32"},{"name":"expiresAt","type":"uint64"}]}',
            HMBCHash.REGISTRATION_DOMAIN, PBC, RSC_ADDR, message,
            HMBCHash.REGISTRATION_TYPEHASH, sh, "alice", muts
        );
    }

    function _roleCertificate(address h1, address alice) internal {
        bytes32[] memory roles = new bytes32[](2);
        roles[0] = keccak256("HMBC.role.Doctor");
        roles[1] = keccak256("HMBC.role.Researcher");
        if (roles[1] < roles[0]) (roles[0], roles[1]) = (roles[1], roles[0]);
        RoleCertificate memory m = RoleCertificate(h1, alice, roles, 101, T0 - 3600, T0 + 365 days);
        bytes32 ds = HMBCHash.domainSeparator(HMBCHash.CREDENTIAL_DOMAIN, PBC, TMSC_ADDR);
        string[] memory muts = new string[](8);
        for (uint256 i = 0; i < 6; i++) {
            RoleCertificate memory x = RoleCertificate(m.issuer, m.gid, _copy(m.roles), m.serial, m.validFrom, m.validUntil);
            string memory f;
            string memory v;
            if (i == 0) (f, v, x.issuer) = ("issuer", _addr(_flip(m.issuer)), _flip(m.issuer));
            if (i == 1) (f, v, x.gid) = ("gid", _addr(_flip(m.gid)), _flip(m.gid));
            if (i == 2) {
                x.roles[0] = _flip(m.roles[0]);
                (f, v) = ("roles[0]", _b32(x.roles[0]));
            }
            if (i == 3) (f, v, x.serial) = ("serial", _u(m.serial ^ 1), m.serial ^ 1);
            if (i == 4) (f, v, x.validFrom) = ("validFrom", _u(m.validFrom ^ 1), m.validFrom ^ 1);
            if (i == 5) (f, v, x.validUntil) = ("validUntil", _u(m.validUntil ^ 1), m.validUntil ^ 1);
            muts[i] = _mutation(f, v, HMBCHash.toTypedDigest(ds, HMBCHash.hashRoleCertificate(x)));
        }
        bytes32 sh = HMBCHash.hashRoleCertificate(m);
        muts[6] = _mutation("domain.chainId", _u(PBC ^ 1), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.CREDENTIAL_DOMAIN, PBC ^ 1, TMSC_ADDR), sh));
        muts[7] = _mutation("domain.verifyingContract", _addr(_flip(TMSC_ADDR)), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.CREDENTIAL_DOMAIN, PBC, _flip(TMSC_ADDR)), sh));
        string[] memory rs = new string[](2);
        rs[0] = _b32(roles[0]);
        rs[1] = _b32(roles[1]);
        string memory message = string.concat(
            "{", _kv("issuer", _addr(m.issuer)), ",", _kv("gid", _addr(m.gid)), ",", _kv("roles", _arr(rs)), ",",
            _kv("serial", _u(m.serial)), ",", _kv("validFrom", _u(m.validFrom)), ",", _kv("validUntil", _u(m.validUntil)), "}"
        );
        _emit(
            "RoleCertificate",
            '{"RoleCertificate":[{"name":"issuer","type":"address"},{"name":"gid","type":"address"},{"name":"roles","type":"bytes32[]"},{"name":"serial","type":"uint64"},{"name":"validFrom","type":"uint64"},{"name":"validUntil","type":"uint64"}]}',
            HMBCHash.CREDENTIAL_DOMAIN, PBC, TMSC_ADDR, message,
            HMBCHash.ROLE_CERTIFICATE_TYPEHASH, sh, "H1-root", muts
        );
    }

    function _revocationList(address h1) internal {
        uint64[] memory serials = new uint64[](2);
        serials[0] = 7;
        serials[1] = 101;
        RevocationList memory m = RevocationList(h1, 3, T0 + 1 days, serials);
        bytes32 ds = HMBCHash.domainSeparator(HMBCHash.TRUST_DOMAIN, PBC, TMSC_ADDR);
        string[] memory muts = new string[](6);
        for (uint256 i = 0; i < 4; i++) {
            uint64[] memory s2 = new uint64[](2);
            s2[0] = serials[0];
            s2[1] = serials[1];
            RevocationList memory x = RevocationList(m.authority, m.version, m.validUntil, s2);
            string memory f;
            string memory v;
            if (i == 0) (f, v, x.authority) = ("authority", _addr(_flip(m.authority)), _flip(m.authority));
            if (i == 1) (f, v, x.version) = ("version", _u(m.version ^ 1), m.version ^ 1);
            if (i == 2) (f, v, x.validUntil) = ("validUntil", _u(m.validUntil ^ 1), m.validUntil ^ 1);
            if (i == 3) {
                x.revokedSerials[1] = serials[1] ^ 1;
                (f, v) = ("revokedSerials[1]", _u(x.revokedSerials[1]));
            }
            muts[i] = _mutation(f, v, HMBCHash.toTypedDigest(ds, HMBCHash.hashRevocationList(x)));
        }
        bytes32 sh = HMBCHash.hashRevocationList(m);
        muts[4] = _mutation("domain.chainId", _u(PBC ^ 1), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.TRUST_DOMAIN, PBC ^ 1, TMSC_ADDR), sh));
        muts[5] = _mutation("domain.verifyingContract", _addr(_flip(TMSC_ADDR)), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.TRUST_DOMAIN, PBC, _flip(TMSC_ADDR)), sh));
        string[] memory ss = new string[](2);
        ss[0] = _u(serials[0]);
        ss[1] = _u(serials[1]);
        string memory message = _obj4(
            _kv("authority", _addr(m.authority)),
            _kv("version", _u(m.version)),
            _kv("validUntil", _u(m.validUntil)),
            _kv("revokedSerials", _arr(ss))
        );
        _emit(
            "RevocationList",
            '{"RevocationList":[{"name":"authority","type":"address"},{"name":"version","type":"uint64"},{"name":"validUntil","type":"uint64"},{"name":"revokedSerials","type":"uint64[]"}]}',
            HMBCHash.TRUST_DOMAIN, PBC, TMSC_ADDR, message,
            HMBCHash.REVOCATION_LIST_TYPEHASH, sh, "H1-root", muts
        );
    }

    function _temporalAcl(address h1, address alice) internal {
        address bob = vm.addr(key("bob"));
        TemporalAcl memory m;
        m.authority = h1;
        m.version = 2;
        m.validUntil = T0 + 1 days;
        m.entries = new TempAclEntry[](2);
        (address a, address b) = alice < bob ? (alice, bob) : (bob, alice);
        m.entries[0] = TempAclEntry(a, keccak256("HMBC.role.OnDuty"), T0 - 60, T0 + 8 hours);
        m.entries[1] = TempAclEntry(b, keccak256("HMBC.role.OnDuty"), T0, T0 + 4 hours);
        bytes32 ds = HMBCHash.domainSeparator(HMBCHash.TRUST_DOMAIN, PBC, TMSC_ADDR);
        string[] memory muts = new string[](9);
        for (uint256 i = 0; i < 7; i++) {
            TemporalAcl memory x;
            x.authority = m.authority;
            x.version = m.version;
            x.validUntil = m.validUntil;
            x.entries = new TempAclEntry[](2);
            x.entries[0] = TempAclEntry(m.entries[0].gid, m.entries[0].role, m.entries[0].validFrom, m.entries[0].validUntil);
            x.entries[1] = TempAclEntry(m.entries[1].gid, m.entries[1].role, m.entries[1].validFrom, m.entries[1].validUntil);
            string memory f;
            string memory v;
            if (i == 0) (f, v, x.authority) = ("authority", _addr(_flip(m.authority)), _flip(m.authority));
            if (i == 1) (f, v, x.version) = ("version", _u(m.version ^ 1), m.version ^ 1);
            if (i == 2) (f, v, x.validUntil) = ("validUntil", _u(m.validUntil ^ 1), m.validUntil ^ 1);
            if (i == 3) (f, v, x.entries[1].gid) = ("entries[1].gid", _addr(_flip(m.entries[1].gid)), _flip(m.entries[1].gid));
            if (i == 4) (f, v, x.entries[1].role) = ("entries[1].role", _b32(_flip(m.entries[1].role)), _flip(m.entries[1].role));
            if (i == 5) (f, v, x.entries[1].validFrom) = ("entries[1].validFrom", _u(m.entries[1].validFrom ^ 1), m.entries[1].validFrom ^ 1);
            if (i == 6) (f, v, x.entries[1].validUntil) = ("entries[1].validUntil", _u(m.entries[1].validUntil ^ 1), m.entries[1].validUntil ^ 1);
            muts[i] = _mutation(f, v, HMBCHash.toTypedDigest(ds, HMBCHash.hashTemporalAcl(x)));
        }
        bytes32 sh = HMBCHash.hashTemporalAcl(m);
        muts[7] = _mutation("domain.chainId", _u(PBC ^ 1), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.TRUST_DOMAIN, PBC ^ 1, TMSC_ADDR), sh));
        muts[8] = _mutation("domain.verifyingContract", _addr(_flip(TMSC_ADDR)), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.TRUST_DOMAIN, PBC, _flip(TMSC_ADDR)), sh));
        string[] memory es = new string[](2);
        for (uint256 i = 0; i < 2; i++) {
            es[i] = _obj4(
                _kv("gid", _addr(m.entries[i].gid)),
                _kv("role", _b32(m.entries[i].role)),
                _kv("validFrom", _u(m.entries[i].validFrom)),
                _kv("validUntil", _u(m.entries[i].validUntil))
            );
        }
        string memory message = _obj4(
            _kv("authority", _addr(m.authority)),
            _kv("version", _u(m.version)),
            _kv("validUntil", _u(m.validUntil)),
            _kv("entries", _arr(es))
        );
        _emit(
            "TemporalAcl",
            '{"TemporalAcl":[{"name":"authority","type":"address"},{"name":"version","type":"uint64"},{"name":"validUntil","type":"uint64"},{"name":"entries","type":"TempAclEntry[]"}],"TempAclEntry":[{"name":"gid","type":"address"},{"name":"role","type":"bytes32"},{"name":"validFrom","type":"uint64"},{"name":"validUntil","type":"uint64"}]}',
            HMBCHash.TRUST_DOMAIN, PBC, TMSC_ADDR, message,
            HMBCHash.TEMPORAL_ACL_TYPEHASH, sh, "H1-root", muts
        );
    }

    function _accessRequest(address alice) internal returns (AccessRequest memory m) {
        m = AccessRequest(
            PBC, DBC, PSC_ADDR, KSSC_ADDR, alice, keccak256("HMBC.data.P1.MHR"), ACTION_READ, 1, 4, 0, 1, T0 + 30,
            keccak256("HMBC.recipient-key.alice")
        );
        string[] memory muts = new string[](13);
        for (uint256 i = 0; i < 13; i++) {
            AccessRequest memory x = _copyReq(m);
            string memory f;
            string memory v;
            if (i == 0) (f, v, x.sourceChainId) = ("sourceChainId", _u(m.sourceChainId ^ 1), m.sourceChainId ^ 1);
            if (i == 1) (f, v, x.destinationChainId) = ("destinationChainId", _u(m.destinationChainId ^ 1), m.destinationChainId ^ 1);
            if (i == 2) (f, v, x.psc) = ("psc", _addr(_flip(m.psc)), _flip(m.psc));
            if (i == 3) (f, v, x.kssc) = ("kssc", _addr(_flip(m.kssc)), _flip(m.kssc));
            if (i == 4) (f, v, x.gid) = ("gid", _addr(_flip(m.gid)), _flip(m.gid));
            if (i == 5) (f, v, x.dataId) = ("dataId", _b32(_flip(m.dataId)), _flip(m.dataId));
            if (i == 6) (f, v, x.action) = ("action", _u(m.action ^ 1), m.action ^ 1);
            if (i == 7) (f, v, x.policyVersion) = ("policyVersion", _u(m.policyVersion ^ 1), m.policyVersion ^ 1);
            if (i == 8) (f, v, x.authEpoch) = ("authEpoch", _u(m.authEpoch ^ 1), m.authEpoch ^ 1);
            if (i == 9) (f, v, x.keyEpoch) = ("keyEpoch", _u(m.keyEpoch ^ 1), m.keyEpoch ^ 1);
            if (i == 10) (f, v, x.nonce) = ("nonce", _u(m.nonce ^ 1), m.nonce ^ 1);
            if (i == 11) (f, v, x.expiresAt) = ("expiresAt", _u(m.expiresAt ^ 1), m.expiresAt ^ 1);
            if (i == 12) (f, v, x.recipientKeyHash) = ("recipientKeyHash", _b32(_flip(m.recipientKeyHash)), _flip(m.recipientKeyHash));
            muts[i] = _mutation(f, v, HMBCHash.accessRequestDigest(x));
        }
        string memory message = string.concat(
            "{", _kv("sourceChainId", _u(m.sourceChainId)), ",", _kv("destinationChainId", _u(m.destinationChainId)), ",",
            _kv("psc", _addr(m.psc)), ",", _kv("kssc", _addr(m.kssc)), ",", _kv("gid", _addr(m.gid)), ",",
            _kv("dataId", _b32(m.dataId)), ",", _kv("action", _u(m.action)), ","
        );
        message = string.concat(
            message, _kv("policyVersion", _u(m.policyVersion)), ",", _kv("authEpoch", _u(m.authEpoch)), ",",
            _kv("keyEpoch", _u(m.keyEpoch)), ",", _kv("nonce", _u(m.nonce)), ",", _kv("expiresAt", _u(m.expiresAt)), ",",
            _kv("recipientKeyHash", _b32(m.recipientKeyHash)), "}"
        );
        _emit(
            "AccessRequest",
            '{"AccessRequest":[{"name":"sourceChainId","type":"uint256"},{"name":"destinationChainId","type":"uint256"},{"name":"psc","type":"address"},{"name":"kssc","type":"address"},{"name":"gid","type":"address"},{"name":"dataId","type":"bytes32"},{"name":"action","type":"uint8"},{"name":"policyVersion","type":"uint64"},{"name":"authEpoch","type":"uint64"},{"name":"keyEpoch","type":"uint64"},{"name":"nonce","type":"uint256"},{"name":"expiresAt","type":"uint64"},{"name":"recipientKeyHash","type":"bytes32"}]}',
            HMBCHash.REQUEST_DOMAIN, PBC, PSC_ADDR, message,
            HMBCHash.ACCESS_REQUEST_TYPEHASH, HMBCHash.hashAccessRequest(m), "alice", muts
        );
    }

    /// credentialDigest is not signed on its own; it is a field of AccessDecision. Exported as an
    /// encoding vector (records -> digest) with per-field mutations of record[1].
    function _credentialRecords(address h1) internal returns (bytes32 digest) {
        CredentialRecord[] memory rs = new CredentialRecord[](2);
        rs[0] = CredentialRecord(h1, keccak256("HMBC.role.Doctor"), CREDENTIAL_LONG_TERM, 101, 1, T0 + 1 days);
        rs[1] = CredentialRecord(h1, keccak256("HMBC.role.OnDuty"), CREDENTIAL_TEMPORAL, 0, 2, T0 + 8 hours);
        digest = HMBCHash.hashCredentialRecords(rs);
        string[] memory muts = new string[](6);
        for (uint256 i = 0; i < 6; i++) {
            CredentialRecord[] memory x = new CredentialRecord[](2);
            x[0] = rs[0];
            x[1] = CredentialRecord(rs[1].issuer, rs[1].role, rs[1].kind, rs[1].serial, rs[1].anchorVersion, rs[1].validUntil);
            string memory f;
            string memory v;
            if (i == 0) (f, v, x[1].issuer) = ("records[1].issuer", _addr(_flip(rs[1].issuer)), _flip(rs[1].issuer));
            if (i == 1) (f, v, x[1].role) = ("records[1].role", _b32(_flip(rs[1].role)), _flip(rs[1].role));
            if (i == 2) (f, v, x[1].kind) = ("records[1].kind", _u(rs[1].kind ^ 1), rs[1].kind ^ 1);
            if (i == 3) (f, v, x[1].serial) = ("records[1].serial", _u(rs[1].serial ^ 1), rs[1].serial ^ 1);
            if (i == 4) (f, v, x[1].anchorVersion) = ("records[1].anchorVersion", _u(rs[1].anchorVersion ^ 1), rs[1].anchorVersion ^ 1);
            if (i == 5) (f, v, x[1].validUntil) = ("records[1].validUntil", _u(rs[1].validUntil ^ 1), rs[1].validUntil ^ 1);
            muts[i] = _mutation(f, v, HMBCHash.hashCredentialRecords(x));
        }
        delete _mutDigest; // credentialDigest is unsigned: no recovery column
        string[] memory items = new string[](2);
        for (uint256 i = 0; i < 2; i++) {
            items[i] = string.concat(
                "{", _kv("issuer", _addr(rs[i].issuer)), ",", _kv("role", _b32(rs[i].role)), ",", _kv("kind", _u(rs[i].kind)), ",",
                _kv("serial", _u(rs[i].serial)), ",", _kv("anchorVersion", _u(rs[i].anchorVersion)), ",",
                _kv("validUntil", _u(rs[i].validUntil)), "}"
            );
        }
        _vectors.push(
            string.concat(
                "{",
                _kv("name", _q("CredentialRecord[] credentialDigest")),
                ",",
                _kv("typeString", _q("CredentialRecord(address issuer,bytes32 role,uint8 kind,uint64 serial,uint64 anchorVersion,uint64 validUntil)")),
                ",",
                _kv("typeHash", _b32(HMBCHash.CREDENTIAL_RECORD_TYPEHASH)),
                ",",
                _kv("encoding", _q("keccak256(concat(hashStruct(record_i))) == EIP-712 encodeData of CredentialRecord[]; records ordered strictly ascending by (kind, issuer, role)")),
                ",",
                _kv("records", _arr(items)),
                ",",
                _kv("credentialDigest", _b32(digest)),
                ",",
                _kv("mutations", _arr(muts)),
                "}"
            )
        );
    }

    /// Encoding check only (NOT an interface type): wrapping CredentialRecord[] in a signed struct
    /// lets an independent EIP-712 implementation confirm the credentialDigest array encoding,
    /// because hashStruct(CredentialSet) = keccak256(typeHash || credentialDigest).
    function _credentialSetCheck(address h1) internal {
        CredentialRecord[] memory rs = new CredentialRecord[](2);
        rs[0] = CredentialRecord(h1, keccak256("HMBC.role.Doctor"), CREDENTIAL_LONG_TERM, 101, 1, T0 + 1 days);
        rs[1] = CredentialRecord(h1, keccak256("HMBC.role.OnDuty"), CREDENTIAL_TEMPORAL, 0, 2, T0 + 8 hours);
        bytes32 typeHash = keccak256(
            "CredentialSet(CredentialRecord[] records)"
            "CredentialRecord(address issuer,bytes32 role,uint8 kind,uint64 serial,uint64 anchorVersion,uint64 validUntil)"
        );
        bytes32 sh = keccak256(abi.encode(typeHash, HMBCHash.hashCredentialRecords(rs)));
        string[] memory items = new string[](2);
        for (uint256 i = 0; i < 2; i++) {
            items[i] = string.concat(
                "{", _kv("issuer", _addr(rs[i].issuer)), ",", _kv("role", _b32(rs[i].role)), ",", _kv("kind", _u(rs[i].kind)), ",",
                _kv("serial", _u(rs[i].serial)), ",", _kv("anchorVersion", _u(rs[i].anchorVersion)), ",",
                _kv("validUntil", _u(rs[i].validUntil)), "}"
            );
        }
        _emit(
            "CredentialSet",
            '{"CredentialSet":[{"name":"records","type":"CredentialRecord[]"}],"CredentialRecord":[{"name":"issuer","type":"address"},{"name":"role","type":"bytes32"},{"name":"kind","type":"uint8"},{"name":"serial","type":"uint64"},{"name":"anchorVersion","type":"uint64"},{"name":"validUntil","type":"uint64"}]}',
            HMBCHash.DECISION_DOMAIN, DBC, KSSC_ADDR, string.concat('{"records":', _arr(items), "}"),
            typeHash, sh, "witness-1", new string[](0)
        );
    }

    function _accessDecision(bytes32 requestDigest, bytes32 credentialDigest, address) internal {
        AccessDecision memory m = AccessDecision(
            requestDigest, RESULT_ALLOW, credentialDigest, 5, 1, 1234, keccak256("HMBC.vector.pbc-block-1234"), T0 + 30
        );
        bytes32 ds = HMBCHash.domainSeparator(HMBCHash.DECISION_DOMAIN, DBC, KSSC_ADDR);
        string[] memory muts = new string[](10);
        for (uint256 i = 0; i < 8; i++) {
            AccessDecision memory x = AccessDecision(
                m.requestDigest, m.result, m.credentialDigest, m.stateSequence, m.witnessSetVersion, m.sourceBlockNumber,
                m.sourceBlockHash, m.expiresAt
            );
            string memory f;
            string memory v;
            if (i == 0) (f, v, x.requestDigest) = ("requestDigest", _b32(_flip(m.requestDigest)), _flip(m.requestDigest));
            if (i == 1) (f, v, x.result) = ("result", _u(m.result ^ 1), m.result ^ 1);
            if (i == 2) (f, v, x.credentialDigest) = ("credentialDigest", _b32(_flip(m.credentialDigest)), _flip(m.credentialDigest));
            if (i == 3) (f, v, x.stateSequence) = ("stateSequence", _u(m.stateSequence ^ 1), m.stateSequence ^ 1);
            if (i == 4) (f, v, x.witnessSetVersion) = ("witnessSetVersion", _u(m.witnessSetVersion ^ 1), m.witnessSetVersion ^ 1);
            if (i == 5) (f, v, x.sourceBlockNumber) = ("sourceBlockNumber", _u(m.sourceBlockNumber ^ 1), m.sourceBlockNumber ^ 1);
            if (i == 6) (f, v, x.sourceBlockHash) = ("sourceBlockHash", _b32(_flip(m.sourceBlockHash)), _flip(m.sourceBlockHash));
            if (i == 7) (f, v, x.expiresAt) = ("expiresAt", _u(m.expiresAt ^ 1), m.expiresAt ^ 1);
            muts[i] = _mutation(f, v, HMBCHash.toTypedDigest(ds, HMBCHash.hashAccessDecision(x)));
        }
        bytes32 sh = HMBCHash.hashAccessDecision(m);
        muts[8] = _mutation("domain.chainId", _u(DBC ^ 1), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.DECISION_DOMAIN, DBC ^ 1, KSSC_ADDR), sh));
        muts[9] = _mutation("domain.verifyingContract", _addr(_flip(KSSC_ADDR)), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.DECISION_DOMAIN, DBC, _flip(KSSC_ADDR)), sh));
        string memory message = string.concat(
            "{", _kv("requestDigest", _b32(m.requestDigest)), ",", _kv("result", _u(m.result)), ",",
            _kv("credentialDigest", _b32(m.credentialDigest)), ",", _kv("stateSequence", _u(m.stateSequence)), ",",
            _kv("witnessSetVersion", _u(m.witnessSetVersion)), ","
        );
        message = string.concat(
            message, _kv("sourceBlockNumber", _u(m.sourceBlockNumber)), ",", _kv("sourceBlockHash", _b32(m.sourceBlockHash)), ",",
            _kv("expiresAt", _u(m.expiresAt)), "}"
        );
        _emit(
            "AccessDecision",
            '{"AccessDecision":[{"name":"requestDigest","type":"bytes32"},{"name":"result","type":"uint8"},{"name":"credentialDigest","type":"bytes32"},{"name":"stateSequence","type":"uint64"},{"name":"witnessSetVersion","type":"uint64"},{"name":"sourceBlockNumber","type":"uint256"},{"name":"sourceBlockHash","type":"bytes32"},{"name":"expiresAt","type":"uint64"}]}',
            HMBCHash.DECISION_DOMAIN, DBC, KSSC_ADDR, message,
            HMBCHash.ACCESS_DECISION_TYPEHASH, sh, "witness-1", muts
        );
    }

    function _stateCheckpoint(address) internal {
        StateCheckpoint memory m =
            StateCheckpoint(5, 4, 1, 0, 1, PBC, PSC_ADDR, 1234, keccak256("HMBC.vector.pbc-block-1234"), T0 + 60);
        bytes32 ds = HMBCHash.domainSeparator(HMBCHash.STATE_DOMAIN, DBC, KSSC_ADDR);
        string[] memory muts = new string[](12);
        for (uint256 i = 0; i < 10; i++) {
            StateCheckpoint memory x = StateCheckpoint(
                m.sequence, m.authEpoch, m.policyVersion, m.keyEpoch, m.witnessSetVersion, m.sourceChainId, m.psc,
                m.sourceBlockNumber, m.sourceBlockHash, m.expiresAt
            );
            string memory f;
            string memory v;
            if (i == 0) (f, v, x.sequence) = ("sequence", _u(m.sequence ^ 1), m.sequence ^ 1);
            if (i == 1) (f, v, x.authEpoch) = ("authEpoch", _u(m.authEpoch ^ 1), m.authEpoch ^ 1);
            if (i == 2) (f, v, x.policyVersion) = ("policyVersion", _u(m.policyVersion ^ 1), m.policyVersion ^ 1);
            if (i == 3) (f, v, x.keyEpoch) = ("keyEpoch", _u(m.keyEpoch ^ 1), m.keyEpoch ^ 1);
            if (i == 4) (f, v, x.witnessSetVersion) = ("witnessSetVersion", _u(m.witnessSetVersion ^ 1), m.witnessSetVersion ^ 1);
            if (i == 5) (f, v, x.sourceChainId) = ("sourceChainId", _u(m.sourceChainId ^ 1), m.sourceChainId ^ 1);
            if (i == 6) (f, v, x.psc) = ("psc", _addr(_flip(m.psc)), _flip(m.psc));
            if (i == 7) (f, v, x.sourceBlockNumber) = ("sourceBlockNumber", _u(m.sourceBlockNumber ^ 1), m.sourceBlockNumber ^ 1);
            if (i == 8) (f, v, x.sourceBlockHash) = ("sourceBlockHash", _b32(_flip(m.sourceBlockHash)), _flip(m.sourceBlockHash));
            if (i == 9) (f, v, x.expiresAt) = ("expiresAt", _u(m.expiresAt ^ 1), m.expiresAt ^ 1);
            muts[i] = _mutation(f, v, HMBCHash.toTypedDigest(ds, HMBCHash.hashStateCheckpoint(x)));
        }
        bytes32 sh = HMBCHash.hashStateCheckpoint(m);
        muts[10] = _mutation("domain.chainId", _u(DBC ^ 1), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.STATE_DOMAIN, DBC ^ 1, KSSC_ADDR), sh));
        muts[11] = _mutation("domain.verifyingContract", _addr(_flip(KSSC_ADDR)), HMBCHash.toTypedDigest(HMBCHash.domainSeparator(HMBCHash.STATE_DOMAIN, DBC, _flip(KSSC_ADDR)), sh));
        string memory message = string.concat(
            "{", _kv("sequence", _u(m.sequence)), ",", _kv("authEpoch", _u(m.authEpoch)), ",",
            _kv("policyVersion", _u(m.policyVersion)), ",", _kv("keyEpoch", _u(m.keyEpoch)), ",",
            _kv("witnessSetVersion", _u(m.witnessSetVersion)), ","
        );
        message = string.concat(
            message, _kv("sourceChainId", _u(m.sourceChainId)), ",", _kv("psc", _addr(m.psc)), ",",
            _kv("sourceBlockNumber", _u(m.sourceBlockNumber)), ",", _kv("sourceBlockHash", _b32(m.sourceBlockHash)), ",",
            _kv("expiresAt", _u(m.expiresAt)), "}"
        );
        _emit(
            "StateCheckpoint",
            '{"StateCheckpoint":[{"name":"sequence","type":"uint64"},{"name":"authEpoch","type":"uint64"},{"name":"policyVersion","type":"uint64"},{"name":"keyEpoch","type":"uint64"},{"name":"witnessSetVersion","type":"uint64"},{"name":"sourceChainId","type":"uint256"},{"name":"psc","type":"address"},{"name":"sourceBlockNumber","type":"uint256"},{"name":"sourceBlockHash","type":"bytes32"},{"name":"expiresAt","type":"uint64"}]}',
            HMBCHash.STATE_DOMAIN, DBC, KSSC_ADDR, message,
            HMBCHash.STATE_CHECKPOINT_TYPEHASH, sh, "witness-1", muts
        );
    }

    // ------------------------------------------------------------------ emit one signed vector

    struct Spec {
        string primaryType;
        string types; // '{"T":[...]...}' without EIP712Domain
        string domainName;
        uint256 chainId;
        address verifyingContract;
        string message;
        bytes32 typeHash;
        bytes32 structHash;
        string signerLabel;
    }

    function _emit(
        string memory primaryType,
        string memory typesWithoutDomain,
        string memory domainName,
        uint256 chainId,
        address verifyingContract,
        string memory message,
        bytes32 typeHash,
        bytes32 structHash,
        string memory signerLabel,
        string[] memory mutations
    ) internal {
        _emitSpec(
            Spec(primaryType, typesWithoutDomain, domainName, chainId, verifyingContract, message, typeHash, structHash, signerLabel),
            mutations
        );
    }

    function _typedJson(Spec memory sp) internal pure returns (string memory) {
        string memory domain = _obj4(
            _kv("name", _q(sp.domainName)),
            _kv("version", _q("1")),
            _kv("chainId", _u(sp.chainId)),
            _kv("verifyingContract", _addr(sp.verifyingContract))
        );
        string memory types = string.concat('{"EIP712Domain":', DOMAIN_TYPE, ",", _tail(sp.types));
        return string.concat(
            "{", _kv("types", types), ",", _kv("primaryType", _q(sp.primaryType)), ",", _kv("domain", domain), ",",
            _kv("message", sp.message), "}"
        );
    }

    function _emitSpec(Spec memory sp, string[] memory mutations) internal {
        bytes32 ds = HMBCHash.domainSeparator(sp.domainName, sp.chainId, sp.verifyingContract);
        bytes32 digest = HMBCHash.toTypedDigest(ds, sp.structHash);
        uint256 pk = key(sp.signerLabel);
        bytes memory signature = _signDigest(pk, digest);
        require(SigLib.tryRecover(digest, signature) == vm.addr(pk), "recovery mismatch");
        string memory typed = _typedJson(sp);
        vm.writeFile(string.concat("exports/vectors/typed/", sp.primaryType, ".json"), typed);
        string memory head = string.concat(
            "{", _kv("name", _q(sp.primaryType)), ",", _kv("typedData", typed), ",", _kv("typeHash", _b32(sp.typeHash)), ",",
            _kv("domainSeparator", _b32(ds)), ",", _kv("structHash", _b32(sp.structHash)), ",", _kv("digest", _b32(digest)), ","
        );
        string memory signerPart = string.concat(
            _kv("signerLabel", _q(sp.signerLabel)), ",", _kv("signerPrivateKey", _b32(bytes32(pk))), ",",
            _kv("signer", _addr(vm.addr(pk))), ",", _kv("signature", _q(vm.toString(signature))), ","
        );
        _vectors.push(string.concat(head, signerPart, _kv("mutations", _arr(_withRecovery(mutations, signature))), "}"));
    }

    function _signDigest(uint256 pk, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    /// Appends the address recovered from the base signature over each mutated digest. A correct
    /// implementation must never recover the original signer there.
    function _withRecovery(string[] memory muts, bytes memory signature) internal returns (string[] memory out) {
        out = new string[](muts.length);
        for (uint256 i = 0; i < muts.length; i++) {
            out[i] = string.concat(_trimClose(muts[i]), ",", _kv("recoveredFromBaseSignature", _addr(SigLib.tryRecover(_mutDigest[i], signature))), "}");
        }
        delete _mutDigest;
    }

    bytes32[] internal _mutDigest;

    function _mutation(string memory field, string memory valueJson, bytes32 mutatedDigest)
        internal
        returns (string memory)
    {
        _mutDigest.push(mutatedDigest);
        return string.concat("{", _kv("field", _q(field)), ",", _kv("mutatedValue", valueJson), ",", _kv("digest", _b32(mutatedDigest)), "}");
    }

    // ------------------------------------------------------------------ helpers

    function _copy(bytes32[] memory xs) internal pure returns (bytes32[] memory ys) {
        ys = new bytes32[](xs.length);
        for (uint256 i = 0; i < xs.length; i++) {
            ys[i] = xs[i];
        }
    }

    function _copyReq(AccessRequest memory m) internal pure returns (AccessRequest memory) {
        return AccessRequest(
            m.sourceChainId, m.destinationChainId, m.psc, m.kssc, m.gid, m.dataId, m.action, m.policyVersion, m.authEpoch,
            m.keyEpoch, m.nonce, m.expiresAt, m.recipientKeyHash
        );
    }

    function _flip(address a) internal pure returns (address) {
        return address(uint160(a) ^ 1);
    }

    function _flip(bytes32 b) internal pure returns (bytes32) {
        return b ^ bytes32(uint256(1));
    }

    function _q(string memory s) internal pure returns (string memory) {
        return string.concat('"', s, '"');
    }

    function _kv(string memory k, string memory v) internal pure returns (string memory) {
        return string.concat(_q(k), ":", v);
    }

    function _u(uint256 x) internal pure returns (string memory) {
        return _q(vm.toString(x));
    }

    function _b32(bytes32 x) internal pure returns (string memory) {
        return _q(vm.toString(x));
    }

    function _addr(address a) internal pure returns (string memory) {
        bytes memory hexChars = "0123456789abcdef";
        bytes memory out = new bytes(42);
        out[0] = "0";
        out[1] = "x";
        uint160 v = uint160(a);
        for (uint256 i = 0; i < 20; i++) {
            uint8 b = uint8(v >> (8 * (19 - i)));
            out[2 + 2 * i] = hexChars[b >> 4];
            out[3 + 2 * i] = hexChars[b & 15];
        }
        return _q(string(out));
    }

    function _obj4(string memory a, string memory b, string memory c, string memory d)
        internal
        pure
        returns (string memory)
    {
        return string.concat("{", a, ",", b, ",", c, ",", d, "}");
    }

    function _arr(string[] memory xs) internal pure returns (string memory out) {
        out = "[";
        for (uint256 i = 0; i < xs.length; i++) {
            out = string.concat(out, i == 0 ? "" : ",", xs[i]);
        }
        out = string.concat(out, "]");
    }

    /// '{"T":...}' -> '"T":...}' (drops the leading brace).
    function _tail(string memory s) internal pure returns (string memory) {
        bytes memory b = bytes(s);
        bytes memory out = new bytes(b.length - 1);
        for (uint256 i = 1; i < b.length; i++) {
            out[i - 1] = b[i];
        }
        return string(out);
    }

    /// '{...}' -> '{...' (drops the trailing brace).
    function _trimClose(string memory s) internal pure returns (string memory) {
        bytes memory b = bytes(s);
        bytes memory out = new bytes(b.length - 1);
        for (uint256 i = 0; i + 1 < b.length; i++) {
            out[i] = b[i];
        }
        return string(out);
    }
}
