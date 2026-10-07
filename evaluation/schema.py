"""Strict candidate wire validation plus canonical ordering/range checks.

Schemas are review proposals, not an E0 freeze. Signature recovery is a separate
vector/implementation check; this module enforces only the canonical encoding.
"""
import json
import math
import re
from pathlib import Path, PurePosixPath
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[1] / 'interfaces/proposals/v1'
FORMATS = FormatChecker()
SECP256K1_N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141
OPERATIONS = {'prepare_request':'PrepareRequest', 'collect_decision':'CollectDecision',
              'release':'Release', 'encrypt_record':'EncryptRecord',
              'finish_decryption':'FinishDecryption', 'rotate_epoch':'RotateEpoch'}


@FORMATS.checks('user-key-ref')
def user_key_ref(value):
    return isinstance(value,str) and bool(re.fullmatch(r'keyref:user:[a-z0-9][a-z0-9-]{0,63}',value))


@FORMATS.checks('evidence-path')
def evidence_path(value):
    if not isinstance(value,str) or not value or '\\' in value or '\x00' in value: return False
    path=PurePosixPath(value)
    return not path.is_absolute() and all(part not in ('','..','.') for part in value.split('/'))


def finite_json(value):
    if isinstance(value,float) and not math.isfinite(value): raise ValueError('MALFORMED: non-finite JSON number')
    if isinstance(value,dict):
        for child in value.values(): finite_json(child)
    elif isinstance(value,list):
        for child in value: finite_json(child)


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
    elif name=='SymbolicPolicy':
        if any(clause[0]['issuerMode']=='2' for clause in value['clauses']):
            raise ValueError('MALFORMED: first requirement cannot use SAME_AS_FIRST')
    elif name=='EncryptRecordInput': semantics('SymbolicPolicy',value['policy'])
    elif name=='CollectDecisionResult': semantics('CredentialRecords',value['credentialRecords'])
    elif name=='FinishDecryptionInput': semantics('ReleaseResult',value['response'])
    elif name=='AdapterRequest' or name.endswith('Request') and name.removesuffix('Request') in OPERATIONS.values():
        semantics(OPERATIONS[value['operation']]+'Input',value['input'])
    elif name=='AdapterResponse' or name.endswith('Response') and name.removesuffix('Response') in OPERATIONS.values():
        if value['ok']:
            result=value['result']
            if 'credentialRecords' in result: semantics('CollectDecisionResult',result)


def validate(name,value):
    finite_json(value)
    if not re.fullmatch(r'[A-Za-z0-9]+',name): raise ValueError('Unknown schema name')
    schema=json.loads((SCHEMAS/'hmbc.schema.json').read_text())
    if name not in schema['$defs']: raise ValueError('Unknown schema name')
    schema['$ref']='#/$defs/'+name
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema,format_checker=FORMATS).validate(value)
    semantics(name,value)


def validate_response(operation,value):
    if operation not in OPERATIONS: raise ValueError('MALFORMED: unknown operation')
    validate(OPERATIONS[operation]+'Response',value)


def validate_json_line(name,line):
    if not isinstance(line,str) or len(line.encode('utf-8'))>1048576:
        raise ValueError('MALFORMED: request line exceeds 1 MiB')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('MALFORMED: duplicate JSON key')
            result[key]=value
        return result
    def constant(_): raise ValueError('MALFORMED: non-finite JSON constant')
    try: value=json.loads(line,object_pairs_hook=pairs,parse_constant=constant)
    except (json.JSONDecodeError,RecursionError) as error: raise ValueError('MALFORMED: invalid JSON') from error
    validate(name,value)
    return value
