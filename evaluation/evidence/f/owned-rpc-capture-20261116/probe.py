"""Retain one synthetic four-operation pipe run; no protocol/ledger service."""
import json
from pathlib import Path
import sys

from evaluation.owned_witness_capture import CapturedWitnessProcess
from evaluation.sealed_signing_capture_v1 import join_sealed_capture
from evaluation.tests.test_signing_event_join_v2 import event_for
from evaluation.tests.test_witness_history_v2 import fixture


def main(output):
    manifest, observations, evidence = fixture()
    events = [event_for(row) for row in evidence["conflicts"]]
    replies = [event["responseLine"] for event in events]
    program = "import sys\nreplies=" + repr(replies) + "\nfor reply in replies:\n if not sys.stdin.readline(): break\n print(reply,flush=True)\n"
    with CapturedWitnessProcess(
        [sys.executable, "-u", "-c", program], cwd=Path.cwd(), output=output,
        timeout=1, stop_grace=1,
    ) as child:
        for event in events:
            child.exchange(json.loads(event["requestLine"]))
    capture, receipt, acquisition = child.completed_capture()
    result = join_sealed_capture(capture, receipt, evidence, manifest=manifest,
                                 observations=observations, expected_owner=evidence["owner"],
                                 compiled_max_admins="8")
    summary = {
        "classification": "tested reconstruction result, synthetic child only",
        "capturedEvents": result["capturedEvents"],
        "signatureReplies": result["signatureReplies"],
        "types": [row["type"] for row in result["joined"]],
        "transportComplete": acquisition["transportComplete"],
        "captureAuthenticated": result["captureAuthenticated"],
        "transcriptCompletenessEstablished": result["transcriptCompletenessEstablished"],
        "integratedCasesRun": 0,
    }
    assert summary["capturedEvents"] == summary["signatureReplies"] == 4
    (output / "join-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
