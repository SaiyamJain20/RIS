"""Recompute producer vectors with eth-account/eth-abi, not ledger code.

These public, deterministic TEST-ONLY keys must never be used with real data/funds.
A matching result cross-checks encoding and recovery; it is not a protocol proof.
"""
import argparse
import copy
import json
import re
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_abi import encode
from eth_utils import keccak
from eth_keys.exceptions import BadSignature


def hx(value):
    return '0x' + bytes(value).hex()


def type_string(primary, types):
    def descendants(name, seen):
        for field in types[name]:
            base = field['type'].split('[')[0]
            if base in types and base not in seen and base != primary:
                seen.add(base)
                descendants(base, seen)
        return seen
    names = [primary] + sorted(descendants(primary, set()))
    return ''.join(name + '(' + ','.join(f"{f['type']} {f['name']}" for f in types[name]) + ')' for name in names)


def credential_digest(records):
    typehash = keccak(text='CredentialRecord(address issuer,bytes32 role,uint8 kind,uint64 serial,uint64 anchorVersion,uint64 validUntil)')
    hashes = []
    for record in records:
        hashes.append(keccak(encode(
            ['bytes32', 'address', 'bytes32', 'uint8', 'uint64', 'uint64', 'uint64'],
            [typehash, record['issuer'], bytes.fromhex(record['role'][2:]),
             *[int(record[k]) for k in ('kind', 'serial', 'anchorVersion', 'validUntil')]])))
    return hx(keccak(b''.join(hashes)))


def mutate_typed(typed, field, value):
    changed = copy.deepcopy(typed)
    target = changed['domain'] if field.startswith('domain.') else changed['message']
    parts = field.removeprefix('domain.').split('.')
    for part in parts[:-1]:
        match = re.fullmatch(r'(\w+)\[(\d+)\]', part)
        target = target[match[1]][int(match[2])] if match else target[part]
    last = parts[-1]
    match = re.fullmatch(r'(\w+)\[(\d+)\]', last)
    if match:
        target[match[1]][int(match[2])] = value
    else:
        target[last] = value
    if changed["primaryType"] == "AccessRequest" and field in ("sourceChainId", "psc"):
        changed["domain"]["chainId" if field == "sourceChainId" else "verifyingContract"] = value
    return changed


def verify_vectors(document):
    report = {'ok': True, 'signedVectors': 0, 'fieldMutations': 0, 'credentialArrays': 0, 'checks': 0, 'failures': []}
    def check(label, actual, expected):
        report['checks'] += 1
        if actual != expected:
            report['failures'].append({'check': label, 'actual': actual, 'expected': expected})
    expected={'Registration','RoleCertificate','RevocationList','TemporalAcl','AccessRequest','CredentialRecord[] credentialDigest','CredentialSet','AccessDecision','StateCheckpoint'}
    vectors=document.get('vectors',[])
    check('complete unique vector inventory',len(vectors)==len(expected) and {v.get('name') for v in vectors}==expected,True)
    for vector in vectors:
        name = vector['name']
        try:
            if 'typedData' not in vector:
                report['credentialArrays'] += 1
                base = credential_digest(vector['records'])
                check(name, base, vector['credentialDigest'])
                check(name + ':typeHash', hx(keccak(text=vector['typeString'])), vector['typeHash'])
                for mutation in vector['mutations']:
                    records = copy.deepcopy(vector['records'])
                    match = re.fullmatch(r'records\[(\d+)\]\.(\w+)', mutation['field'])
                    records[int(match[1])][match[2]] = mutation['mutatedValue']
                    report['fieldMutations'] += 1
                    digest = credential_digest(records)
                    check(name + ':' + mutation['field'], digest, mutation['digest'])
                    check(name + ':changed', digest != base, True)
                continue
            report['signedVectors'] += 1
            typed = vector['typedData']
            if typed['primaryType']!='CredentialSet':
                fields={m['field'].split('.')[0].split('[')[0] for m in vector['mutations'] if not m['field'].startswith('domain.')}
                check(name+':message mutation coverage',set(typed['message']).issubset(fields),True)
                domain_fields={m['field'] for m in vector['mutations']}
                if typed['primaryType']=='AccessRequest':
                    domain_covered={'sourceChainId','psc'}.issubset(domain_fields)
                else:
                    domain_covered={'domain.chainId','domain.verifyingContract'}.issubset(domain_fields)
                check(name+':domain mutation coverage',domain_covered,True)
            message = encode_typed_data(full_message=typed)
            signed = Account.sign_message(message, vector['signerPrivateKey'])
            check(name + ':typeHash', hx(keccak(text=type_string(typed['primaryType'], typed['types']))), vector['typeHash'])
            check(name + ':domain', hx(message.header), vector['domainSeparator'])
            check(name + ':struct', hx(message.body), vector['structHash'])
            check(name + ':digest', hx(signed.message_hash), vector['digest'])
            check(name + ':signature', hx(signed.signature), vector['signature'])
            check(name + ':signer', Account.recover_message(message, signature=vector['signature']).lower(), vector['signer'])
            for mutation in vector['mutations']:
                changed = encode_typed_data(full_message=mutate_typed(typed, mutation['field'], mutation['mutatedValue']))
                digest = hx(keccak(b'\x19' + changed.version + changed.header + changed.body))
                recovered = Account.recover_message(changed, signature=vector['signature']).lower()
                report['fieldMutations'] += 1
                check(name + ':' + mutation['field'] + ':digest', digest, mutation['digest'])
                check(name + ':' + mutation['field'] + ':recovery', recovered, mutation['recoveredFromBaseSignature'])
                check(name + ':mutation changes digest', digest != vector['digest'], True)
                check(name + ':mutation invalidates signer', recovered != vector['signer'], True)
        except (ValueError, TypeError, KeyError, AttributeError, BadSignature) as error:
            report['failures'].append({'check': name, 'error': str(error)})
    report['ok'] = not report['failures']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vectors', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = verify_vectors(json.loads(args.vectors.read_text()))
    output = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(output)
    print(output, end='')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
