"""Acquire public witness RPC frames from one owned, bounded pipe session.

Paper-derived HMBC2020 reconstruction. A clean session only establishes local
transport acquisition. It does not authenticate the child, ledger observations,
off-channel signing, complete signed history or persistence. Never use this
collector for the worker/token boundary. The caller owns argv/source pin review.
"""
import copy
import json
import os
import selectors
import time

from jsonschema import ValidationError

from evaluation.manifests import sha256
from evaluation.processes import JsonLinesProcess, MAX_LINE_BYTES
from evaluation.schema_v2 import validate
from evaluation.sealed_signing_capture_v1 import seal_capture

_KINDS = {"decision": "AccessDecision", "checkpoint": "StateCheckpoint",
          "receipt": "GrantReceipt", "governance": "GovernanceAction"}


class CapturedWitnessProcess(JsonLinesProcess):
    """Single-flight witness transport with a lossless journal and final receipt.

    Only `completed_capture` produces usable input for the signing-event join.
    Incomplete attempts are counted even when they produce no usable event.
    No cryptographic authenticity or global completeness claim follows.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attempts = 0
        self._events = []
        self._pending_event = None
        self._capture_failure = None
        self._final = None

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            self._capture_failure = exc_type.__name__
        self.stop()

    def exchange(self, request):
        # Refuse another boundary (including worker tokens) before journaling.
        fields = {"schemaVersion", "id", "round", "kind", "message"}
        if not (
            isinstance(request, dict) and set(request) == fields
            and request["schemaVersion"] == "hmbc-witness-rpc/v1"
            and type(request["id"]) is int and request["id"] >= 0
            and type(request["round"]) is int and request["round"] in (1, 2)
            and isinstance(request["kind"], str)
            and request["kind"] in _KINDS
            and isinstance(request["message"], dict)
        ):
            raise ValueError("Capture accepts only public witness RPC requests")
        try:
            validate(_KINDS[request["kind"]], request["message"])
        except (ValueError, ValidationError) as error:
            raise ValueError("Invalid public witness RPC message") from error
        try:
            response = super().exchange(request)
            if not (
                set(response) == {"schemaVersion", "id", "reply"}
                and response["schemaVersion"] == "hmbc-witness-rpc/v1"
                and type(response["id"]) is int and response["id"] == request["id"]
                and isinstance(response["reply"], dict)
            ):
                raise ValueError("Invalid witness RPC response envelope or request ID")
            self._events.append(self._pending_event)
            return response
        except BaseException as error:
            self._capture_failure = type(error).__name__
            self.stop()
            raise

    def exchange_crash(self, *args, **kwargs):
        raise ValueError("Witness capture does not accept the worker crash boundary")

    def _journal(self, direction, wire):
        with (self.output / "wire.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"attempt": self._attempts, "direction": direction,
                                     "hex": wire.hex()}, separators=(",", ":")) + "\n")

    def _roundtrip(self, wire, **kwargs):
        self._attempts += 1
        self._pending_event = None
        self._journal("request", wire)
        response = super()._roundtrip(wire, **kwargs)
        self._journal("response", response + b"\n")
        self._pending_event = {
            "sequence": str(self._attempts),
            "requestLine": wire[:-1].decode("utf-8"),
            "responseLine": response.decode("utf-8"),
        }
        return response

    def _drain_tail(self):
        """Observe natural stdout EOF; bound both time and retained byte count."""
        process = self._process
        if process is None:
            return False, b""
        if not process.stdin.closed:
            process.stdin.close()
        deadline = time.monotonic() + self.stop_grace
        tail = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    return False, bytes(tail)
                try:
                    chunk = os.read(process.stdout.fileno(), min(65536, MAX_LINE_BYTES - len(tail)))
                except BlockingIOError:
                    continue
                if not chunk:
                    return True, bytes(tail)
                tail.extend(chunk)
                if len(tail) >= MAX_LINE_BYTES:
                    return False, bytes(tail)

    def stop(self):
        if self._record is None or self._record["endedAt"] is not None:
            return
        stdout_eof, tail = False, b""
        try:
            stdout_eof, tail = self._drain_tail()
        except OSError as error:
            self._capture_failure = type(error).__name__
        finally:
            # Reap only this owned child, including on drain/validation failure.
            super().stop()
        if tail:
            (self.output / "stdout-tail.bin").write_bytes(tail)
        capture = {"schemaVersion": "hmbc-witness-rpc-capture/v1", "events": self._events}
        receipt = seal_capture(capture, observed_event_count=self._attempts)
        for name, document in (("capture", capture), ("receipt", receipt)):
            (self.output / (name + ".json")).write_text(json.dumps(document, indent=2) + "\n")
        stderr_bytes = (self.output / "stderr.log").stat().st_size
        failure = self._capture_failure or self._record["failure"]
        complete = bool(self._attempts and len(self._events) == self._attempts
                        and stdout_eof and not tail and not stderr_bytes
                        and self.returncode == 0 and failure is None)
        journal = self.output / "wire.jsonl"
        acquisition = {
            "schemaVersion": "hmbc-owned-witness-acquisition/v1",
            "pid": self.pid,
            "attemptCount": self._attempts,
            "eventCount": len(self._events),
            "stdoutEof": stdout_eof,
            "retainedTailBytes": len(tail),
            "stderrBytes": stderr_bytes,
            "exitCode": self.returncode,
            "failure": failure,
            "transportComplete": complete,
            "captureAuthenticated": False,
            "transcriptCompletenessEstablished": False,
            "processRecordSha256": sha256(self.output / "process.json"),
            "wireJournalSha256": sha256(journal) if journal.is_file() else None,
            "captureSha256": sha256(self.output / "capture.json"),
            "receiptSha256": sha256(self.output / "receipt.json"),
        }
        (self.output / "acquisition.json").write_text(json.dumps(acquisition, indent=2) + "\n")
        self._final = copy.deepcopy((capture, receipt, acquisition))

    def completed_capture(self):
        """Return isolated copies only after a clean and fully reaped pipe run."""
        if self._final is None:
            raise RuntimeError("Witness capture is not finished")
        if not self._final[2]["transportComplete"]:
            raise RuntimeError("Witness capture is incomplete; inspect acquisition.json")
        return copy.deepcopy(self._final)
