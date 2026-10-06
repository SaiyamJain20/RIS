"""Hash explicit inputs and retain command failures; never infer a run from a commit."""
import hashlib
import json
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path


def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def now():return datetime.now(timezone.utc).isoformat()


def safe_artifact(root,path):
    root=Path(root).resolve();candidate=Path(path)
    if candidate.is_absolute():raise ValueError('Evidence path must be relative')
    resolved=(root/candidate).resolve()
    if not resolved.is_relative_to(root):raise ValueError('Evidence path escapes run')
    return resolved


def hash_files(root,paths):
    return {str(path):sha256(safe_artifact(root,path)) for path in sorted(paths)}


def source_manifest(root):
    root=Path(root)
    files=[]
    for prefix in ('evaluation','interfaces'):
        for p in (root/prefix).rglob('*'):
            rel=p.relative_to(root)
            if p.is_file() and p.suffix in ('.py','.json','.csv','.pv','.md') and not any(part in ('runs','evidence','__pycache__','.pytest_cache') for part in rel.parts):files.append(rel)
    files += [Path(name) for name in ('pyproject.toml','uv.lock','AGENTS.md','README.md','SPEC.md','PLAN.md','communication/COMMON_AGENT_CONTEXT.md','communication/PROTOCOL.md','communication/agent-1/ROLE.md','communication/agent-2/ROLE.md','communication/agent-3/ROLE.md','communication/agent-3/outbox/0001-ack-distributed-startup.md','communication/agent-3/outbox/0002-rfc-e0-semantics-toolchain-receipt.md','communication/BOARD.md','communication/DECISIONS.md','communication/GATES.md','evaluation/evidence/source-map.csv','evaluation/evidence/assumptions.csv') if (root/name).is_file()]
    return hash_files(root,files)


def record_command(argv,cwd,log,timeout=60,env=None):
    start=now();began=time.monotonic();log=Path(log);log.parent.mkdir(parents=True,exist_ok=True)
    timed_out=False
    with log.open('wb') as output:
        try:
            result=subprocess.run(argv,cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=timeout,check=False)
            code=result.returncode
        except subprocess.TimeoutExpired:
            code=124;timed_out=True
        except OSError as error:
            code=127;output.write(str(error).encode())
    return {'argv':list(argv),'cwd':str(Path(cwd).resolve()),'startedAt':start,'endedAt':now(),'exitCode':code,'timedOut':timed_out,'elapsedSeconds':time.monotonic()-began,'outputSha256':sha256(log)}
