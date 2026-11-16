"""D-6 (agent 2): the TEST-ONLY deviating witness reads its pinned deployment with the strict JSON parser of the carried adapter (duplicate member names, NaN/Infinity and invalid UTF-8 are refused),
not plain `json.loads` (S2-0007). Written BEFORE the change. The tool is a mutation fixture; this closes a hardening item only, it adds no behaviour."""
import pytest

from testtools import deviating_witness as dw


def run(tmp_path, raw, capsys):
    p = tmp_path / "deployment.json"
    p.write_bytes(raw)
    with pytest.raises(SystemExit) as e:
        dw.main(["--deployment", str(p), "receipt", "--grant-id", "0x" + "00" * 32, "--field", "gid"])
    return str(e.value)


@pytest.mark.parametrize("raw,needle", [(b'{"chains": 1, "chains": 2}', "duplicate"), (b'{"a": NaN}', "non-standard JSON constant NaN"), (b'{"a": Infinity}', "non-standard JSON constant Infinity"), (b'{"a": -Infinity}', "non-standard JSON constant -Infinity"),
                                        (b"\xff\xfe", "not valid UTF-8"), (b"{", "invalid JSON")])
def test_a_deployment_file_the_strict_parser_refuses_is_refused_cleanly_and_named(tmp_path, capsys, raw, needle):
    msg = run(tmp_path, raw, capsys)
    assert msg.startswith("refusing:") and needle in msg, msg


def test_a_well_formed_but_unusable_deployment_still_reaches_the_ledger_stage(tmp_path, capsys):
    msg = run(tmp_path, b"{}", capsys)
    assert msg.startswith("refusing:") and "KeyError" in msg and "invalid JSON" not in msg and "duplicate" not in msg, msg
