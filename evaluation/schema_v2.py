"""Explicit v2 shape and declared semantic checks for synthetic F evaluation.

The E validator and its consumers stay unchanged. This module does not recover
signatures, reconstruct source observations, validate exporter history, or prove
store completeness/durability, actual timing or transaction acceptance. A D50
hash authenticates nothing: anchored source reconstruction remains mandatory.
"""
import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from evaluation import schema as legacy

SCHEMAS = Path(__file__).resolve().parents[1] / 'interfaces/v2'
OPERATIONS = legacy.OPERATIONS | {'collect_governance': 'CollectGovernance'}
# A private checker avoids changing E validation when this module is imported.
FORMATS = FormatChecker()
for _name, _check in [('user-key-ref', legacy.user_key_ref),
                       ('evidence-path', legacy.evidence_path),
                       ('canonical-signature', legacy.canonical_signature)]:
    FORMATS.checks(_name)(_check)
for _bits in (8, 32, 64, 256):
    FORMATS.checks(f'uint{_bits}')(lambda v, bits=_bits: legacy._uint(v, bits))

_INHERITED = {'CredentialRecords', 'CredentialBundle', 'RoleCertificate',
              'RevocationList', 'TemporalAcl', 'TempAclEntry', 'SymbolicPolicy'}
_BASE_NAMES = {'0': 'paper-strict', '1': 'paper-minimal',
               '2': 'repaired-e', '3': 'repaired-f'}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _require(condition, message):
    if not condition:
        raise ValueError('MALFORMED: ' + message)


def _binding_document(value):
    profile = value['profile']
    enum = profile['enum']
    _require(_BASE_NAMES.get(enum) == profile['name'], 'binding base profile')
    carriers = list(value['immutables'].values())
    masks = {int(c['mutations']) for c in carriers}
    _require(len(masks) == 1, 'binding mutation holders disagree')
    mask = next(iter(masks))
    _require(all(c.get('profile', enum) == enum for c in carriers), 'binding profile holders disagree')
    allowed = mask <= 511 if enum == '3' else mask in ({0, 1, 2, 4, 8, 16, 32} if enum == '2' else {0})
    _require(allowed, 'binding mutation mask')
    groups = list(value['witnessSets'].values())
    for group in groups:
        witnesses = group['witnesses']
        _require(len(set(witnesses)) == len(witnesses), 'duplicate binding witness')
        _require(1 <= int(group['threshold']) <= len(witnesses), 'binding threshold')
    if enum == '3':
        _require(all(g == groups[0] for g in groups), 'F ordered witness sets disagree')
        _require(all(g['version'] == '2' and len(g['witnesses']) == 4 and
                     g['threshold'] in ('2', '3') for g in groups), 'F witness configuration')
        _require(mask == 0 or groups[0]['threshold'] == '3', 'nonzero mutation with q2')


def _collection(value):
    outcomes = value['outcomes']
    _require(len({o['witness'] for o in outcomes}) == 4, 'duplicate outcome witness')
    for outcome in outcomes:
        _require((int(outcome['replies']) == 0) == (outcome['status'] == 'silent'), 'outcome reply count')
    signers = value['submittedSigners']
    legacy.ordered(signers, lambda v: v)
    _require(len(signers) in (0, 3), 'pool submitted signer count')
    _require(set(signers) <= {o['witness'] for o in outcomes if o['status'] == 'signed'}, 'unsigned submission')
    reports = value.get('recordedReports', [])
    inconsistent = value.get('inconsistentReports', [])
    legacy.ordered(reports, lambda r: int(r['witnessIndex']))
    legacy.ordered(inconsistent, lambda r: int(r['witnessIndex']))
    _require(not {r['witnessIndex'] for r in reports} &
             {r['witnessIndex'] for r in inconsistent}, 'overlapping report partitions')
    snapshot_messages = [r['message'] for r in reports]
    for reporter in inconsistent:
        messages = [r['message'] for r in reporter['reports']]
        legacy.ordered(messages, _canonical)
        snapshot_messages.extend(messages)
    _require(len({m['sequence'] for m in snapshot_messages}) <= 1, 'snapshot sequence mismatch')
    # Late duplicates may be retained as arrival evidence; only sort, not dedupe.
    late_keys = [(int(r['witnessIndex']), _canonical(r['message'])) for r in value.get('lateReports', [])]
    _require(late_keys == sorted(late_keys), 'late report order')
    candidates = {}
    for report in reports:
        candidates.setdefault(_canonical(report['message']), []).append(report['witnessIndex'])
    eligible = [(m, ids) for m, ids in candidates.items() if len(ids) >= 2]
    _require(('adopted' in value) == (len(eligible) == 1), 'checkpoint selection')
    if 'timing' not in value:
        return
    timing = value['timing']
    start = int(timing['ledgerNowAtStart'])
    remaining = int(timing['proposalExpiresAt']) - start
    _require(remaining > 2, 'collection contacted witnesses inside reserve')
    deadline = min(10000, (remaining - 2) * 1000)
    _require(int(timing['collectionDeadlineMs']) == deadline, 'collection deadline')
    closed = int(timing['snapshotClosedAtMs'])
    closed_by = timing['snapshotClosedBy']
    if closed_by == 'all-replied':
        _require(closed < min(5000, deadline), 'all-replied close bound')
    elif closed_by == 'deadline':
        _require(closed == deadline <= 5000, 'deadline close bound')
    else:
        _require(closed == 5000 < deadline, 'reply-timeout close bound')
    if 'adopted' in value:
        adopted = value['adopted']
        message, reporters = eligible[0]
        _require(_canonical(adopted['message']) == message and adopted['reporters'] == reporters,
                 'adopted message/reporters')
        action = ('skipped_deadline' if closed >= deadline else
                  'skipped_validity' if int(adopted['message']['expiresAt']) * 1000 -
                  (start * 1000 + closed) <= 2000 else 'sent')
        _require(adopted['reproposal'] == action, 'reproposal precedence/validity')


def _semantics(name, value):
    if name in _INHERITED:
        legacy.semantics(name, value)
    elif name in ('GovernanceAction', 'CollectGovernanceInput'):
        legacy.ordered(value['admins'], lambda v: v)
    elif name == 'LedgerAbiEntryV2':
        ranges = value['immutableReferences']
        end = 0
        for span in ranges:
            start, length = int(span['start']), int(span['length'])
            _require(start >= end and start + length <= int(value['runtimeBytes']), 'immutable range bounds/order')
            end = start + length
        digest = hashlib.sha256(_canonical(ranges).encode()).hexdigest()
        _require(digest == value['immutableRefsSha256'], 'immutable object-list hash')
    elif name == 'DeploymentBindingDocument':
        _binding_document(value)
    elif name in ('BindingExport', 'WitnessEvidenceBinding'):
        _require(value['binding_v2'] == _binding_digest(value['document']), 'binding fingerprint')
    elif name == 'LedgerDeploymentF':
        _require(value['mutations'] == '0' or value['fixture']['witnessSet']['threshold'] == '3',
                 'nonzero mutation with q2')
    elif name == 'Collection':
        _collection(value)
    elif name == 'CollectCheckpointResult' and 'adopted' in value.get('collection', {}):
        adopted = value['collection']['adopted']
        _require(adopted['reproposal'] == 'sent' and value['checkpoint'] == adopted['message'],
                 'successful checkpoint differs from sent adoption')


def _walk(rule, value, validator, seen, definitions):
    """Visit applicable named definitions, including nested envelope branches."""
    if not isinstance(rule, dict):
        return
    if '$ref' in rule:
        name = rule['$ref'].removeprefix('#/$defs/')
        key = (name, id(value))
        if key not in seen:
            seen.add(key)
            _semantics(name, value)
            _walk(definitions[name], value, validator, seen, definitions)
    for branch in rule.get('allOf', []):
        _walk(branch, value, validator, seen, definitions)
    for keyword in ('oneOf', 'anyOf'):
        for branch in rule.get(keyword, []):
            if validator.evolve(schema=branch).is_valid(value):
                _walk(branch, value, validator, seen, definitions)
    if 'if' in rule:
        branch = 'then' if validator.evolve(schema=rule['if']).is_valid(value) else 'else'
        _walk(rule.get(branch, {}), value, validator, seen, definitions)
    if isinstance(value, dict):
        for field, child_rule in rule.get('properties', {}).items():
            if field in value:
                _walk(child_rule, value[field], validator, seen, definitions)
    if isinstance(value, list):
        prefix = rule.get('prefixItems', [])
        for i, child in enumerate(value):
            child_rule = prefix[i] if i < len(prefix) else rule.get('items', {})
            _walk(child_rule, child, validator, seen, definitions)


def validate(name, value):
    """Check v2 shape and the documented subset of declared semantic rules."""
    legacy.finite_json(value)
    document = json.loads((SCHEMAS / 'hmbc.schema.json').read_text())
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9]+', name) or name not in document['$defs']:
        raise ValueError('Unknown v2 schema name')
    document['$ref'] = '#/$defs/' + name
    validator = Draft202012Validator(document, format_checker=FORMATS)
    validator.validate(value)
    _walk({'$ref': document['$ref']}, value, validator, set(), document['$defs'])


def validate_response(operation, value):
    if operation not in OPERATIONS:
        raise ValueError('MALFORMED: unknown operation')
    validate(OPERATIONS[operation] + 'Response', value)


def validate_json_line(name, line):
    if not isinstance(line, str) or len(line.encode('utf-8')) > 1048576:
        raise ValueError('MALFORMED: request line exceeds 1 MiB')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('MALFORMED: duplicate JSON key')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('MALFORMED: non-finite JSON constant')

    try:
        value = json.loads(line, object_pairs_hook=pairs, parse_constant=constant)
    except (json.JSONDecodeError, RecursionError) as error:
        raise ValueError('MALFORMED: invalid JSON') from error
    validate(name, value)
    return value


def _binding_digest(document):
    preimage = b'hmbc-deployment-binding/v2\n' + _canonical(document).encode('ascii')
    return hashlib.sha256(preimage).hexdigest()


def binding_hash(document):
    validate('DeploymentBindingDocument', document)
    return _binding_digest(document)
