import copy
import json
from pathlib import Path
import pytest
from jsonschema import ValidationError
from evaluation.schema import validate

DEPLOYMENTS=json.loads(Path('interfaces/vectors/deployment-agent1-candidate.json').read_text())['deployments']


@pytest.mark.parametrize('deployment',DEPLOYMENTS,ids=lambda d:d['profile'])
def test_current_owner_deployment_samples_validate(deployment):
    validate('LedgerDeployment',deployment)


@pytest.mark.parametrize('kind',['nested-extra','number-chain','chain-overflow','set-version','threshold','epoch','ttl','profile-mutation','abi-extra','bad-source-hash','missing-psc'])
def test_deployment_wire_and_e_constraints_reject(kind):
    d=copy.deepcopy(next(d for d in DEPLOYMENTS if d['profile']=='repaired-e'))
    if kind=='nested-extra':d['fixture']['witnessSet']['privateKey']='forbidden'
    if kind=='number-chain':d['chains']['pbc']['chainId']=18545
    if kind=='chain-overflow':d['chains']['pbc']['chainId']=str(2**256)
    if kind=='set-version':d['fixture']['witnessSet']['version']='2'
    if kind=='threshold':d['fixture']['witnessSet']['threshold']='2'
    if kind=='epoch':d['fixture']['keyEpoch']='1'
    if kind=='ttl':d['fixture']['ttlSeconds']['decision']='31'
    if kind=='profile-mutation':d['mutations']='32'
    if kind=='abi-extra':d['abi']['PSC']['unexpected']=True
    if kind=='bad-source-hash':d['sources']['src/PSC.sol']='not-a-hash'
    if kind=='missing-psc':del d['chains']['pbc']['contracts']['PSC']
    with pytest.raises((ValidationError,ValueError)):validate('LedgerDeployment',d)
