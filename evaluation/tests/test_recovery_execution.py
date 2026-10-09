"""Full access/recovery collector on synthetic native and adapter inputs.

Exercises real codecs, signature checks, worker joins and oracle. No services or
integrated evidence. Restart must happen once after export and retain request.
"""
import copy
import importlib
import json

import pytest
from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_access_execution import Model


class RecoveryModel(Model):
    def __init__(self,*args):
        super().__init__(*args);self.restarts=0;self.crash_reply=None;self.production=False
        self.crash_finished=False;self.returncode=None

    def exchange_crash(self,request,*,point,validate_response):
        assert request['operation']=='release'
        reply=super().exchange(request);self.crash_reply=copy.deepcopy(reply)
        self.releases[0]['completedAttempts']=0
        if point=='after_intent':
            self.worker_events=self.worker_events[:1];self.releases[0]['sendAttempts']=0;reply=None
        else:validate_response(reply)
        self.crash_finished=True;self.returncode=86
        return reply

    def restart(self):
        assert self.crash_finished and self.restarts==0
        self.restarts+=1;self.production=True;self.returncode=None
        return self

    def exchange(self,request):
        if request['operation']=='release' and self.production:
            self.worker_events.append(dict(self.worker_events[0],type='RELEASE_SENT'))
            self.releases[0]['sendAttempts']+=1;self.releases[0]['completedAttempts']+=1
            return copy.deepcopy(self.crash_reply)
        return super().exchange(request)

    def snapshot(self):
        p=json.loads(super().snapshot());p['counts']['releaseSentCount']=str(sum(e['type']=='RELEASE_SENT' for e in self.worker_events))
        return json.dumps(p).encode()


@pytest.mark.parametrize('profile',['paper-strict','paper-minimal','repaired-e'])
@pytest.mark.parametrize('point',['after_intent','after_send'])
def test_full_collector_joins_checked_recovery_and_outcome(artifacts,inputs,tmp_path,profile,point):
    m=RecoveryModel(artifacts,inputs,profile)
    assert importlib.util.find_spec('evaluation.recovery_execution') is not None,'Recovery adapter composition missing'
    module=importlib.import_module('evaluation.recovery_execution')
    session=module.RecoveryAdapter(m,restart=m.restart,point=point,pbc=m.pbc,dbc=m.dbc,
                                  deployment=m.dep,worker_snapshot=m.snapshot,output=tmp_path/'recovery')
    access=importlib.import_module('evaluation.access_execution')
    result=access.execute_access(m.pbc,m.dbc,session,deployment_bytes=json.dumps(m.dep).encode(),
                                user_label='alice',user=m.users['alice'],record=m.record,policy=m.policy,
                                expected_allow=True,worker_snapshot=m.snapshot,output=tmp_path/'access',recovery_point=point)
    assert result['ok'] and m.restarts==1
    assert result['oracle']['classification']==('REPAIR_SUPPORTED' if profile=='repaired-e' else 'BLOCKED')
    assert [e['type'] for e in result['observed']['events']].count('DBC_AUTHORIZED')==1
    assert [e['type'] for e in result['observed']['events']].count('OUTCOME_RECORDED')==1
    proof=json.loads((tmp_path/'recovery/result.json').read_text())
    assert proof['ok'] and proof['delivery']=='unknown'
    assert proof['sendAttempts']==(1 if point=='after_intent' else 2)
    assert all('"token"' not in p.read_text() for p in (tmp_path/'recovery').glob('*.json'))
