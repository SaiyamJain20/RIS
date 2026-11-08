"""The carried worker on profile 3 (repaired-f) (agent 2, slice 10a). Written BEFORE the one-line change in `worker.py`.

FINDING (live, then reproduced here): `Worker._recipient_for` branched on `PSC.profile == "2"` (repaired-e) and treated EVERY other profile as a PAPER profile, so on a real repaired-f ledger a valid grant
(carrying the recipient commitment the PSC enforced at request time, exactly as in repaired-e) was refused WRONG_SUBJECT "a paper-profile grant is expected to carry no recipient commitment". The profile-3
change is one the accepted plan allows in the owned source. Profiles 0 and 1 (paper) must behave exactly as before.
"""
import pytest

from hmbc_protocol.worker import Worker, WorkerError

REG = "0x" + "aa" * 32
OTHER = "0x" + "bb" * 32
ZERO = "0x" + "00" * 32


class FakeChain:
    def __init__(self, profile, registered):
        self.profile, self.registered = profile, registered

    def call(self, contract, fn, *args):
        return {"profile": self.profile, "recipientKeyHash": self.registered}[fn]


class Led:
    def __init__(self, profile, registered=REG):
        self.pbc, self.PSC, self.RSC = FakeChain(profile, registered), object(), object()


def recipient(profile, grant_recipient, registered=REG):
    w = Worker.__new__(Worker)
    w.led = Led(profile, registered)
    return w._recipient_for({"gid": "0x" + "11" * 20, "recipientKeyHash": grant_recipient})


@pytest.mark.parametrize("profile", ["2", "3"])
def test_the_repaired_profiles_bind_a_release_to_the_grants_own_registered_recipient(profile):
    assert recipient(profile, REG) == REG


@pytest.mark.parametrize("profile", ["2", "3"])
def test_the_repaired_profiles_refuse_a_zero_or_different_recipient_commitment(profile):
    for bad in (ZERO, OTHER):
        with pytest.raises(WorkerError) as e:
            recipient(profile, bad)
        assert e.value.code == "WRONG_SUBJECT" and "unbound or differs" in e.value.message


@pytest.mark.parametrize("profile", ["0", "1"])
def test_the_paper_profiles_are_unchanged_a_zero_grant_binds_to_the_registered_key(profile):
    assert recipient(profile, ZERO) == REG
    with pytest.raises(WorkerError) as e:
        recipient(profile, REG)
    assert e.value.code == "WRONG_SUBJECT" and "paper-profile grant" in e.value.message
    with pytest.raises(WorkerError) as e:
        recipient(profile, ZERO, registered=ZERO)
    assert "no registered recipient key" in e.value.message


def test_an_unknown_profile_is_treated_as_the_carried_paper_branch_does_not_guess_a_repaired_one():
    assert recipient("4", ZERO) == REG                                    # unchanged carried behaviour for a profile no ledger defines
