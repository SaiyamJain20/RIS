"""Strict candidate wire validation plus canonical ordering/range checks.

Schemas are review proposals, not an E0 freeze. Signature recovery is a separate
vector/implementation check; this module enforces only the canonical encoding.
"""
import json
import re
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[1] / 'interfaces/proposals/v1'
FORMATS = FormatChecker()
SECP256K1_N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141


def _uint(value, bits):
    return isinstance(value,str) and bool(re.fullmatch(r'0|[1-9][0-9]*',value)) and len(value)<=len(str(2**bits-1)) and int(value)<2**bits


for _bits in (8,64,256):
    FORMATS.checks(f'uint{_bits}')(lambda value,bits=_bits: _uint(value,bits))


@FORMATS.checks('canonical-signature')
def canonical_signature(value):
    if not isinstance(value,str) or not re.fullmatch(r'0x[0-9a-f]{130}',value): return False
    raw=bytes.fromhex(value[2:]);r=int.from_bytes(raw[:32]);s=int.from_bytes(raw[32:64])
    return 0<r<SECP256K1_N and 0<s<=SECP256K1_N//2 and raw[64] in (27,28)


def ordered(values, key):
    keys=[key(v) for v in values]
    if any(a>=b for a,b in zip(keys,keys[1:])): raise ValueError('MALFORMED: canonical order/uniqueness required')


def semantics(name,value):
    if name=='CredentialRecords':
        ordered(value,lambda v:(int(v['kind']),v['issuer'],v['role']))
        for record in value:
            if record['kind']=='2' and record['serial']!='0': raise ValueError('MALFORMED: temporal serial must be zero')
    elif name=='SignedRoleCertificate':semantics('RoleCertificate',value['cert'])
    elif name=='CredentialBundle':
        if not value['certificates'] and not value['temporalClaims']: raise ValueError('MALFORMED: empty credential bundle')
        ordered(value['certificates'],lambda v:v['cert']['issuer'])
        ordered(value['temporalClaims'],lambda v:(v['authority'],v['role']))
        for signed in value['certificates']: semantics('RoleCertificate',signed['cert'])
    elif name=='RoleCertificate':
        ordered(value['roles'],lambda v:v)
        if int(value['validFrom'])>=int(value['validUntil']): raise ValueError('MALFORMED: invalid certificate interval')
    elif name=='RevocationList': ordered(value['revokedSerials'],lambda v:int(v))
    elif name=='TemporalAcl':
        ordered(value['entries'],lambda v:(v['gid'],v['role']))
        for entry in value['entries']: semantics('TempAclEntry',entry)
    elif name=='TempAclEntry':
        if value['gid']=='0x'+'00'*20: raise ValueError('MALFORMED: zero temporal subject')
        if int(value['validFrom'])>=int(value['validUntil']): raise ValueError('MALFORMED: invalid temporal interval')


def validate(name,value):
    if not re.fullmatch(r'[A-Za-z0-9]+',name): raise ValueError('Unknown schema name')
    schema=json.loads((SCHEMAS/'hmbc.schema.json').read_text())
    if name not in schema['$defs']: raise ValueError('Unknown schema name')
    schema['$ref']='#/$defs/'+name
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema,format_checker=FORMATS).validate(value)
    semantics(name,value)
