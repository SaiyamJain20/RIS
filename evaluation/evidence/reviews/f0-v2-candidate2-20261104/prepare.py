"""Assemble a separate mapping candidate; no producer/consumer is switched."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
P = ROOT / 'interfaces/proposals/v2-candidate2'
OWNER = '52f39437771b0d5615b29015725c9f91d469d976'


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def ref(name):
    return {'$ref': '#/$defs/' + name}


def obj(props, optional=()):
    return {'type': 'object', 'properties': props,
            'required': [k for k in props if k not in optional], 'additionalProperties': False}


def owner(path):
    return subprocess.check_output(['git', 'show', OWNER + ':' + path], cwd=ROOT)


def main():
    P.mkdir(exist_ok=True)
    (P / 'vectors').mkdir(exist_ok=True)
    for source in (ROOT / 'interfaces/proposals/v2/vectors').iterdir():
        shutil.copyfile(source, P / 'vectors' / source.name)
    parser_inputs = json.loads((P / 'vectors/strict-json-expectations.json').read_text())
    for case in parser_inputs['cases']:
        case['targets'] = ['adapter', 'TEST-ONLY deviating_witness']
    parser_inputs['cases'] += [
        {'line': '{"operation":"collect_checkpoint","input":{},"unexpected":true}', 'expected': 'MALFORMED',
         'reason': 'unknown envelope field', 'targets': ['adapter']},
        {'line': '{"signature":"0x00"}', 'expected': 'MALFORMED', 'reason': 'truncated signature',
         'targets': ['adapter', 'TEST-ONLY deviating_witness']},
        {'line': '{"expiresAt":"01"}', 'expected': 'MALFORMED', 'reason': 'noncanonical decimal string',
         'targets': ['adapter', 'TEST-ONLY deviating_witness']},
        {'line': '{"witnessIndex":"4"}', 'expected': 'MALFORMED', 'reason': 'out-of-range witness selector', 'targets': ['adapter']},
        {'line': '{"witnessIndex":-Infinity}', 'expected': 'MALFORMED', 'reason': 'non-finite constant',
         'targets': ['adapter', 'TEST-ONLY deviating_witness']},
        {'construction': 'UTF-8 encoded line of 1048577 bytes (1MiB+1), using a repeated ASCII space after a JSON object',
         'expected': 'MALFORMED', 'reason': 'request exceeds byte bound; check before JSON parsing',
         'targets': ['adapter', 'TEST-ONLY deviating_witness']}]
    write(P / 'vectors/strict-json-expectations.json', parser_inputs)
    shutil.copyfile(ROOT / 'interfaces/proposals/v2/reason-codes.json', P / 'reason-codes.json')
    s = json.loads((ROOT / 'evaluation/evidence/reviews/f0-v2-owner-review-20261104/prospective-schema.json').read_text())
    s['$id'] = 'urn:hmbc2020:interface:v2:candidate2'
    s['title'] = 'HMBC2020 successor v2 candidate 2 — NOT FROZEN'
    s['x-status'] = 'COMPLETE_MAPPING_PROPOSAL; both exact mapping ACKs and separate F0 freeze pending; no execution'
    d = s['$defs']
    # Preserve both frozen v1 names, not just the entry. Successor E/F use V2 names.
    d['LedgerAbiContractsV2'] = d['LedgerAbiContracts']
    d['LedgerAbiContractsFV2'] = d.pop('LedgerAbiContractsF')
    d['LedgerAbiContracts'] = json.loads((ROOT / 'interfaces/v1/hmbc.schema.json').read_text())['$defs']['LedgerAbiContracts']
    d['LedgerDeploymentE']['properties']['abi'] = ref('LedgerAbiContractsV2')
    d['LedgerDeploymentF']['properties']['abi'] = ref('LedgerAbiContractsFV2')
    d['LedgerDeploymentF']['x-status'] = 'Proposed F successor carrier; NOT FROZEN'
    for shape in d['DeploymentBindingDocument']['oneOf']:
        names = shape['properties']['profile']['oneOf']
        if any(x['properties']['name'] == {'const': 'repaired-f'} for x in names):
            shape['properties']['interfaceVersion'] = {'const': 'v2'}
    # Closed layouts independently transcribed from EXPORT-LAYOUTS revision 9.
    # Numeric widths of signed message members are retained from the message types.
    dec = {'type': 'string', 'pattern': '^(0|[1-9][0-9]*)$'}
    witness_owner = {'type': 'string', 'pattern': '^witness:0x[0-9a-f]{40}$'}
    d['EvidenceObservation'] = obj({'chainId': copy.deepcopy(dec), 'blockNumber': copy.deepcopy(dec),
                                   'blockHash': ref('Hash'), 'timestamp': copy.deepcopy(dec)})
    d['BindingAnchor'] = obj({side: obj({'number': copy.deepcopy(dec), 'hash': ref('Hash')})
                              for side in ['pbc', 'dbc']})
    d['BindingExport'] = obj({'owner': {'oneOf': [{'const': 'worker'}, witness_owner]},
        'binding_v2': ref('FileHash'), 'document': ref('DeploymentBindingDocument'), 'anchor': ref('BindingAnchor')})
    d['WitnessEvidenceBinding'] = obj({'binding_v2': ref('FileHash'), 'document': ref('DeploymentBindingDocument')})
    d['WitnessEvidenceMarker'] = obj({'binding_v2': ref('FileHash'), 'owner': witness_owner, 'schema': {'const': '2'}})
    d['EvidenceSignature'] = {'type': 'string', 'pattern': '^0x[0-9a-f]{130}$',
        'description': 'Layout only; canonical secp256k1 and recovery remain mandatory independent semantic checks.'}
    d['EvidenceFault'] = obj({'reason': {'enum': ['number-regression', 'timestamp-regression', 'hash-changed']},
                              'previous': ref('EvidenceObservation'), 'observed': ref('EvidenceObservation')})
    d['EvidenceFaultClear'] = obj({'seq': copy.deepcopy(dec), 'fault': ref('EvidenceFault'),
        'clearedAgainst': ref('EvidenceObservation'), 'note': {'type': 'string', 'minLength': 1}})
    deaths = {
        'AccessDecision': ['expiry', 'overtaken-decision-sequence', 'overtaken-decision-grant'],
        'StateCheckpoint': ['expiry', 'overtaken-checkpoint'],
        'GrantReceipt': ['executed-receipt'],
        'GovernanceAction': ['expiry', 'overtaken-governance']}
    live, superseded = [], []
    for message, key in [('AccessDecision', 'requestDigest'), ('StateCheckpoint', 'sequence'),
                         ('GrantReceipt', 'requestDigest'), ('GovernanceAction', 'nonce')]:
        effect = copy.deepcopy(d[message]['properties'])
        effect.pop(key)
        effect.pop('expiresAt', None)
        d[message + 'Effect'] = obj(effect)
        if message == 'GovernanceAction':
            d[message + 'Effect']['properties']['witnessSetVersion'] = {'const': '2'}
        digest = {'digest': ref('Hash'), 'signature': ref('EvidenceSignature'), 'observation': ref('EvidenceObservation')}
        if message != 'GrantReceipt':
            digest['expiresAt'] = ref('Uint64')
        record = obj({'type': {'const': message}, 'domainSeparator': ref('Hash'),
            'witnessSetVersion': {'enum': ['1', '2']} if message != 'GovernanceAction' else {'const': '2'},
            'keyField': ref('Hash') if key == 'requestDigest' else ref('Uint64'),
            'effect': ref(message + 'Effect'), 'vHash': ref('FileHash'),
            'digests': {'type': 'array', 'minItems': 1, 'items': obj(digest)}})
        d[message + 'LiveRecord'] = record
        live.append(ref(message + 'LiveRecord'))
        old = copy.deepcopy(record)
        variants = []
        for kind in deaths[message]:
            dp = {'kind': {'const': kind}, 'observation': ref('EvidenceObservation')}
            if kind in ['overtaken-checkpoint', 'overtaken-governance', 'overtaken-decision-sequence']:
                dp['observed'] = copy.deepcopy(dec)
            variants.append(obj(dp))
        old['properties'].update(seq=copy.deepcopy(dec), death={'oneOf': variants})
        old['required'] += ['seq', 'death']
        if message == 'AccessDecision':
            old['allOf'] = [{'if': {'properties': {'death': {'properties': {'kind': {'const': 'overtaken-decision-grant'}}}}},
                'then': {'properties': {'effect': {'properties': {'result': {'const': '1'}}}}}}]
        d[message + 'SupersededRecord'] = old
        superseded.append(ref(message + 'SupersededRecord'))
    d['WitnessEvidence'] = obj({'schemaVersion': {'const': 'hmbc-witness-evidence/v2'},
        'owner': witness_owner, 'binding': ref('WitnessEvidenceBinding'), 'marker': ref('WitnessEvidenceMarker'),
        'observations': {'type': 'array', 'maxItems': 2, 'items': ref('EvidenceObservation')},
        'faulted': {'oneOf': [{'type': 'null'}, ref('EvidenceFault')]},
        'faultLog': {'type': 'array', 'items': ref('EvidenceFaultClear')},
        'conflicts': {'type': 'array', 'items': {'oneOf': live}},
        'superseded': {'type': 'array', 'items': {'oneOf': superseded}}, 'evidenceSha256': ref('FileHash')})
    d['ExporterError'] = {'oneOf': [obj({'code': {'const': code}, 'message': {'type': 'string', 'minLength': 1},
        'reason': {'const': reason}}) for reason, code in [('STORE_MISSING', 'ADAPTER_UNAVAILABLE'),
            ('STORE_CORRUPT', 'ADAPTER_UNAVAILABLE'), ('LEGACY_STATE', 'WRONG_DESTINATION')]]}
    write(P / 'hmbc.schema.json', s)
    for source, dest in [('protocol/f0/vectors/d50_binding_vector.json', 'd50-owner-vectors.json'),
                         ('protocol/f0/vectors/export_layouts_vectors.json', 'export-layout-owner-vectors.json')]:
        (P / dest).write_bytes(owner(source))
    inputs = ['protocol/f0/' + n for n in ['D50-DEPLOYMENT-BINDING.md', 'SIGNING-RULES.md',
              'SUCCESSOR-WIRE.md', 'EXPORT-LAYOUTS.md', 'MANIFEST.sha256', 'vectors/export_layouts_reference.py']]
    write(OUT / 'intended-pins.json', {'ownerCommit': OWNER,
        'ledgerCommit': '8a943a7c64e881ac0686587f01a9ebfaf2368706',
        'ledgerDesignSha256': '7eed1b29e79144d88d6b5bba33a414e4fcb6dc8fa8cb31262c0742e3baaebfd0',
        'files': {p: hashlib.sha256(owner(p)).hexdigest() for p in inputs},
        'status': 'CANDIDATE2_INPUTS_FOR_REVIEW; no final mapping ACK or F0 freeze'})
    shutil.copyfile(OUT / 'intended-pins.json', P / 'OWNER-PINS.json')
    print('Candidate2 schema and vectors assembled; no shared consumer changed.')


if __name__ == '__main__':
    main()
