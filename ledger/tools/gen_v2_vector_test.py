#!/usr/bin/env python3
"""Generate a Forge test that checks interface-v2 proposal signing vectors with the ledger's own hashing (agent 1, F0).

Input to the v2 mapping review (A3-0066). For every vector in `<proposal>/vectors/signing.json` the generated test
recomputes the domain separator, struct hash and digest in Solidity and compares them with the vector:
- StateCheckpoint, AccessDecision and GrantReceipt through the E functions in `src/types/ProtocolTypes.sol`
  (`HMBCHash.*Digest`), which KSSC and PSC use today;
- GovernanceAction through design 2.2 section 2 (`ledger/f0/A-F1-DESIGN.md`): type string below, admins hashed as
  32-byte words (`keccak256(abi.encodePacked(address[]))`), domain {HMBCGovernance, "1", chainId, Governance}.
  Governance.sol does not exist yet, so this is the planned encoding, not a run of the contract.
It then runs the existing QuorumLib (`src/lib/SigLib.sol`) on the vector signatures against the four witnesses of
`<proposal>/vectors/witnesses.json`: accepted at q3, two signatures insufficient at q3 and enough at q2, another digest
gives BAD_SIGNATURE, and SET signatures do not authorize REMOVE. It also checks that each witness address follows the
TEST-ONLY derivation keccak256("hmbc-e0-synthetic-key:" || label); no key is printed or written.

With --implemented (the A-F1 tree), the GovernanceAction cases also require that the implemented
HMBCHash.hashGovernanceAction / governanceActionDigest / GOVERNANCE_ACTION_TYPEHASH equal the vector.

Usage (repository root): build a scratch copy, never inside ledger/:
  cp -r ledger/src ledger/foundry.toml <scratch>/ && mkdir <scratch>/test
  python3 -I ledger/tools/gen_v2_vector_test.py [--implemented] <interface dir> > <scratch>/test/V2VectorsCheck.t.sol
  forge test --root <scratch>
Standard library only. Prints Solidity to stdout; exit 0, or exit 1 on an unknown vector type.
"""
import json
import sys

GOV_TYPE = (
    "GovernanceAction(uint8 action,address root,address[] admins,uint64 nonce,uint64 witnessSetVersion,"
    "uint64 expiresAt)"
)


def addr(a):
    return f'address(bytes20(hex"{a[2:]}"))'


def b32(x):
    return f"bytes32({x})"


def digest_body(name, d, m):
    """Solidity lines computing (dig, dom, sh, th) for one vector."""
    chain, vc = d["chainId"], addr(d["verifyingContract"])
    out = [f'        dom = HMBCHash.domainSeparator("{d["name"]}", {chain}, {vc});']
    if name == "GovernanceAction":
        out += [f'        th = keccak256("{GOV_TYPE}");', f"        address[] memory admins = new address[]({len(m['admins'])});"]
        out += [f"        admins[{i}] = {addr(a)};" for i, a in enumerate(m["admins"])]
        out += [
            f"        sh = keccak256(abi.encode(th, uint8({m['action']}), {addr(m['root'])}, "
            f"keccak256(abi.encodePacked(admins)), uint64({m['nonce']}), uint64({m['witnessSetVersion']}), "
            f"uint64({m['expiresAt']})));",
            "        dig = HMBCHash.toTypedDigest(dom, sh);",
        ]
        if IMPLEMENTED:
            # A-F1 tree: the implemented library must give the same struct hash and digest.
            out += [
                f"        GovernanceAction memory ga = GovernanceAction({m['action']}, {addr(m['root'])}, admins, "
                f"{m['nonce']}, {m['witnessSetVersion']}, {m['expiresAt']});",
                '        require(HMBCHash.hashGovernanceAction(ga) == sh, "implemented structHash");',
                f'        require(HMBCHash.governanceActionDigest(ga, {chain}, {vc}) == dig, "implemented digest");',
                '        require(HMBCHash.GOVERNANCE_ACTION_TYPEHASH == th, "implemented typehash");',
            ]
    elif name == "StateCheckpoint":
        out += [
            f"        StateCheckpoint memory x = StateCheckpoint({m['sequence']}, {m['authEpoch']}, {m['policyVersion']}, "
            f"{m['keyEpoch']}, {m['witnessSetVersion']}, {m['sourceChainId']}, {addr(m['psc'])}, "
            f"{m['sourceBlockNumber']}, {b32(m['sourceBlockHash'])}, {m['expiresAt']});",
            "        sh = HMBCHash.hashStateCheckpoint(x);",
            f"        dig = HMBCHash.stateCheckpointDigest(x, {chain}, {vc});",
        ]
    elif name == "AccessDecision":
        out += [
            f"        AccessDecision memory x = AccessDecision({b32(m['requestDigest'])}, {m['result']}, "
            f"{b32(m['credentialDigest'])}, {m['stateSequence']}, {m['witnessSetVersion']}, {m['sourceBlockNumber']}, "
            f"{b32(m['sourceBlockHash'])}, {m['expiresAt']});",
            "        sh = HMBCHash.hashAccessDecision(x);",
            f"        dig = HMBCHash.accessDecisionDigest(x, {chain}, {vc});",
        ]
    elif name == "GrantReceipt":
        out += [
            f"        GrantReceipt memory x = GrantReceipt({b32(m['requestDigest'])}, {b32(m['grantId'])}, {addr(m['gid'])}, "
            f"{b32(m['dataId'])}, {m['keyEpoch']}, {m['grantExpiresAt']}, {m['witnessSetVersion']}, {m['dbcChainId']}, "
            f"{addr(m['kssc'])}, {m['dbcBlockNumber']}, {b32(m['dbcBlockHash'])});",
            "        sh = HMBCHash.hashGrantReceipt(x);",
            f"        dig = HMBCHash.grantReceiptDigest(x, {chain}, {vc});",
        ]
    else:
        return None
    return out


IMPLEMENTED = False


def main():
    global IMPLEMENTED
    args = sys.argv[1:]
    IMPLEMENTED = "--implemented" in args
    if IMPLEMENTED:
        args.remove("--implemented")
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    proposal = args[0]
    vectors = json.load(open(f"{proposal}/vectors/signing.json"))["vectors"]
    witnesses = json.load(open(f"{proposal}/vectors/witnesses.json"))["witnesses"]
    o = [
        "// SPDX-License-Identifier: UNLICENSED",
        "// GENERATED by ledger/tools/gen_v2_vector_test.py from an interface-v2 proposal. Scratch use only.",
        "pragma solidity 0.8.37;",
        'import "../src/types/ProtocolTypes.sol";',
        'import {QuorumLib} from "../src/lib/SigLib.sol";',
        "interface Vm { function addr(uint256) external pure returns (address); }",
        "contract V2VectorsCheck {",
        '    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));',
        "    function _witnesses() internal pure returns (address[] memory ws) {",
        f"        ws = new address[]({len(witnesses)});",
    ]
    o += [f"        ws[{i}] = {addr(w['address'])};" for i, w in enumerate(witnesses)]
    o += [
        "    }",
        "    function _eq(bytes32 a, bytes32 e, string memory what) internal pure { require(a == e, what); }",
        "    function _code(ErrorCode c, ErrorCode e, string memory what) internal pure { require(c == e, what); }",
        "    function test_V2_WitnessAddressesFollowTheSyntheticDerivation() public pure {",
        "        address[] memory ws = _witnesses();",
    ]
    o += [
        f'        require(vm.addr(uint256(keccak256(bytes("hmbc-e0-synthetic-key:{w["label"]}")))) == ws[{i}], "witness {i}");'
        for i, w in enumerate(witnesses)
    ]
    o.append("    }")
    for n, v in enumerate(vectors):
        td, name = v["typedData"], v["name"]
        body = digest_body(name, td["domain"], td["message"])
        if body is None:
            print(f"unknown vector type {name}", file=sys.stderr)
            return 1
        sigs = v["signatures"]
        o += [f"    function _sigs{n}() internal pure returns (bytes[] memory s) {{", f"        s = new bytes[]({len(sigs)});"]
        o += [f'        s[{i}] = hex"{s["signature"][2:]}";' for i, s in enumerate(sigs)]
        o += ["    }", f"    function _digest{n}() internal pure returns (bytes32 dig, bytes32 dom, bytes32 sh, bytes32 th) {{"]
        o += body + ["    }"]
        tag = f"{name}{n}"
        o += [
            f"    function test_V2_{tag}_HashesMatchTheVector() public pure {{",
            f"        (bytes32 dig, bytes32 dom, bytes32 sh, bytes32 th) = _digest{n}();",
            f'        _eq(dom, {b32(v["domainSeparator"])}, "domainSeparator");',
            f'        _eq(sh, {b32(v["structHash"])}, "structHash");',
            f'        _eq(dig, {b32(v["digest"])}, "digest");',
            f'        _eq(th, {b32(v["typeHash"])}, "typeHash");' if "typeHash" in v else "        th;",
            "    }",
            f"    function test_V2_{tag}_QuorumLibAcceptsAtQ3() public pure {{",
            f"        (bytes32 dig,,,) = _digest{n}();",
            f'        _code(QuorumLib.verify(dig, _sigs{n}(), _witnesses(), 3), ErrorCode.NONE, "q3");',
            "    }",
            f"    function test_V2_{tag}_TwoSignaturesInsufficientAtQ3() public pure {{",
            f"        (bytes32 dig,,,) = _digest{n}();",
            f"        bytes[] memory all = _sigs{n}();",
            "        bytes[] memory two = new bytes[](2);",
            "        two[0] = all[0];",
            "        two[1] = all[1];",
            '        _code(QuorumLib.verify(dig, two, _witnesses(), 3), ErrorCode.INSUFFICIENT_QUORUM, "q3 two");',
            '        _code(QuorumLib.verify(dig, two, _witnesses(), 2), ErrorCode.NONE, "q2 two");',
            "    }",
            f"    function test_V2_{tag}_OtherDigestIsBadSignature() public pure {{",
            f"        (bytes32 dig,,,) = _digest{n}();",
            f"        _code(QuorumLib.verify(keccak256(abi.encode(dig)), _sigs{n}(), _witnesses(), 3), "
            'ErrorCode.BAD_SIGNATURE, "other digest");',
            "    }",
        ]
    gov = {v["typedData"]["message"]["action"]: n for n, v in enumerate(vectors) if v["name"] == "GovernanceAction"}
    if "2" in gov and "3" in gov:
        o += [
            "    function test_V2_SetSignaturesDoNotAuthorizeRemove() public pure {",
            f"        (bytes32 removeDigest,,,) = _digest{gov['2']}();",
            f'        _code(QuorumLib.verify(removeDigest, _sigs{gov["3"]}(), _witnesses(), 3), ErrorCode.BAD_SIGNATURE, "set->remove");',
            "    }",
        ]
    o.append("}")
    print("\n".join(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
