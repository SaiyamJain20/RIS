import copy
import json
from pathlib import Path

import pytest

from evaluation.vectors import verify_vectors

VECTORS = Path('interfaces/vectors/eip712-agent1-candidate.json')


def test_independent_encoder_matches_all_peer_vectors_and_mutations():
    report = verify_vectors(json.loads(VECTORS.read_text()))
    assert report['ok']
    assert report['signedVectors'] == 9
    assert report['fieldMutations'] == 83
    assert report['credentialArrays'] == 1
    assert report['checks'] >= 100


@pytest.mark.parametrize('field', ['digest', 'signature', 'signer', 'structHash', 'domainSeparator'])
def test_peer_expected_value_corruption_is_detected(field):
    data = json.loads(VECTORS.read_text())
    data['vectors'][0][field] = '0x' + '00' * ((len(data['vectors'][0][field]) - 2) // 2)
    assert not verify_vectors(data)['ok']


def test_mutation_without_digest_change_is_detected():
    data = json.loads(VECTORS.read_text())
    data['vectors'][0]['mutations'][0]['digest'] = data['vectors'][0]['digest']
    assert not verify_vectors(data)['ok']


def test_empty_or_incomplete_vector_pack_is_not_a_success():
    data=json.loads(VECTORS.read_text())
    assert not verify_vectors({'vectors':[]})['ok']
    data['vectors']=data['vectors'][:-1]
    assert not verify_vectors(data)['ok']


def test_removed_mutation_coverage_is_detected():
    data=json.loads(VECTORS.read_text())
    data['vectors'][0]['mutations']=[]
    assert not verify_vectors(data)['ok']


def test_receipt_vector_and_its_domain_mutations_are_required():
    data=json.loads(VECTORS.read_text())
    receipt=next(v for v in data['vectors'] if v['name']=='GrantReceipt')
    data['vectors'].remove(receipt)
    assert not verify_vectors(data)['ok']
    data['vectors'].append(receipt)
    receipt['mutations']=[m for m in receipt['mutations'] if m['field']!='domain.verifyingContract']
    assert not verify_vectors(data)['ok']
