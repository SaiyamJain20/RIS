"""A killed initialisation must not strand a witness directory (agent 2, F phase). Written BEFORE the fix. PAPER-DERIVED RECONSTRUCTION; synthetic signer; one host.

Found by `test_witness_state_kill.py` (random SIGKILL of a child that is initialising a store; evidence/af2-kill-durability): in about 5% of the kills that landed in the first few milliseconds the
directory held a 4096-byte `signing.sqlite` and a `signing.sqlite-journal`, i.e. the process died while SQLite was switching the new file to WAL mode and left a HOT ROLLBACK JOURNAL. `_classify`
inspects the directory through a `mode=ro` connection, which cannot roll a hot journal back (SQLITE_READONLY_ROLLBACK, "attempt to write a readonly database"), so every later `init_store` refused the
directory as STORE_CORRUPT: the witness could never start there again without someone deleting the directory by hand. SUCCESSOR-WIRE section 5 says an interrupted initialisation is COMPLETED by the next
`init_store`.
The contract tested here:
  * an UNINITIALISED directory (no INITIALIZED marker, nothing ever recorded) whose database has a hot rollback journal is recovered by SQLite's own mechanism and the initialisation completes;
  * an INITIALISED directory (marker present) is NEVER repaired by the inspection: the same state is refused as STORE_CORRUPT and every byte of the main file and the journal is left as it was;
  * a corrupt file in an uninitialised directory is still refused (the retry is only for the read-only error class), and is not modified.
The hot journal is made deterministically: a child opens the database in rollback-journal mode with a tiny page cache, so the pager syncs the journal header while the write transaction is still open, and SIGKILLs itself before
the commit (an unsynced journal has a zero header and is not hot: the first version of this helper made exactly that mistake, which its precondition check caught)."""
import hashlib
import os
import signal
import sqlite3
import subprocess
import sys

import pytest

from hmbc_protocol import witness_state as ws
from test_witness_state import B, BIND, DBC, OWNER, h, obs

CHILD = r'''
import os, signal, sqlite3, sys
con = sqlite3.connect(sys.argv[1], isolation_level=None)
con.execute("PRAGMA journal_mode=DELETE")
if sys.argv[2] == "empty":
    con.execute("CREATE TABLE scratch(a)")
    con.execute("DROP TABLE scratch")
con.execute("PRAGMA cache_size=2")                        # a tiny page cache: the pager must SYNC the journal header before it spills dirty pages into the main file
con.execute("BEGIN")
con.execute("CREATE TABLE y(a)")
for _ in range(400):
    con.execute("INSERT INTO y VALUES (zeroblob(1000))")
os.kill(os.getpid(), signal.SIGKILL)
'''


def hot_journal(db, kind):
    r = subprocess.run([sys.executable, "-I", "-c", CHILD, db, kind], capture_output=True, text=True)
    assert r.returncode == -signal.SIGKILL, (r.returncode, r.stderr[-400:])
    journal = db + "-journal"
    assert os.path.exists(journal) and os.path.getsize(journal) > 0, "the child left no journal: the precondition of this test is missing"
    con = ws._ro(db)
    try:
        with pytest.raises(sqlite3.OperationalError) as e:
            con.execute("PRAGMA integrity_check").fetchone()
        assert (e.value.sqlite_errorcode & 0xFF) == sqlite3.SQLITE_READONLY, e.value          # the precondition: a read-only connection cannot read this file
    finally:
        con.close()


def files_sha(d):
    return {n: hashlib.sha256(open(os.path.join(d, n), "rb").read()).hexdigest() for n in sorted(os.listdir(d)) if not n.startswith(".")}


def test_init_store_completes_a_directory_a_kill_left_with_a_hot_rollback_journal(tmp_path):
    d = str(tmp_path / "witness-0")
    os.makedirs(d, mode=0o700)
    hot_journal(os.path.join(d, "signing.sqlite"), "empty")
    st = ws.init_store(d, BIND, B, OWNER)
    try:
        assert (st.binding_v2, st.owner, st.document) == (BIND, OWNER, B)
        sig = st.sign(type="StateCheckpoint", domain="0x" + "a1" * 32, wsv="2", key="1",
                      effect={"authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": B["chains"]["pbc"]["chainId"], "psc": "0x" + "bb" * 20,
                              "sourceBlockNumber": "138", "sourceBlockHash": h("block:%s:138" % B["chains"]["pbc"]["chainId"])},
                      expires_at="1791521610", digest=h("after-recovery"), signer=lambda dg: "0x" + (hashlib.sha256(dg.encode()).hexdigest() * 3)[:130], observe=lambda: obs(DBC, 160, 1791521600))
        assert sig.startswith("0x")
    finally:
        st.close()
    assert not os.path.exists(os.path.join(d, "signing.sqlite-journal"))              # the journal was rolled back and deleted by SQLite itself


def test_an_initialised_store_is_never_repaired_by_the_inspection(tmp_path):
    d = str(tmp_path / "witness-0")
    ws.init_store(d, BIND, B, OWNER).close()
    hot_journal(os.path.join(d, "signing.sqlite"), "keep")                              # an initialised store (marker present) whose file carries a hot rollback journal
    before = files_sha(d)
    for attempt in (lambda: ws.open_store(d, BIND, OWNER), lambda: ws.init_store(d, BIND, B, OWNER)):
        with pytest.raises(ws.StoreError) as e:
            attempt()
        assert (e.value.reason, e.value.code) == ("STORE_CORRUPT", "ADAPTER_UNAVAILABLE")
        assert files_sha(d) == before, "a refusal must leave every byte of the store as it was"


def test_a_corrupt_file_in_an_uninitialised_directory_is_still_refused_and_untouched(tmp_path):
    d = str(tmp_path / "witness-0")
    os.makedirs(d, mode=0o700)
    with open(os.path.join(d, "signing.sqlite"), "wb") as f:
        f.write(b"this is not a database" * 400)
    before = files_sha(d)
    with pytest.raises(ws.StoreError) as e:
        ws.init_store(d, BIND, B, OWNER)
    assert e.value.reason == "STORE_CORRUPT"
    assert files_sha(d) == before
