"""Hash explicit inputs and retain command failures; never infer a run from a commit."""
import hashlib
import json
import math
import os
import signal
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


def record_command(argv,cwd,log,timeout=60,env=None,*,owned_process_group=False,stop_grace=2):
    """Bounded command, optionally own a fresh POSIX group for shell/Forge children.

    Group cleanup is confined to a session we created while the direct child is
    unreaped. Normal synchronous commands must not daemonize descendants.
    """
    start=now();began=time.monotonic();log=Path(log);log.parent.mkdir(parents=True,exist_ok=True)
    timed_out=False;pid=None;cleanup=None;process=None
    state_path=Path(str(log)+'.process.json')
    def save(status):
        if owned_process_group:
            state_path.write_text(json.dumps(dict(pid=pid,processGroup=pid,status=status,groupCleanup=cleanup),indent=2)+'\n')
    def stop_group():
        nonlocal cleanup
        cleanup='TERM_THEN_KILL'
        for sig in (signal.SIGTERM,signal.SIGKILL):
            try: os.killpg(pid,sig)
            except ProcessLookupError: pass
            if sig == signal.SIGTERM: time.sleep(stop_grace)
        process.wait(timeout=5)
    with log.open('wb') as output:
        try:
            if owned_process_group:
                if os.name != 'posix' or stop_grace < 0 or not math.isfinite(stop_grace):
                    raise ValueError('Owned command requires POSIX and a finite nonnegative stop budget')
                process=subprocess.Popen(argv,cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                pid=process.pid
                try:
                    save('RUNNING')
                    code=process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    timed_out=True;code=124;stop_group()
                except BaseException:
                    stop_group();raise
                finally: save('STOPPED' if process.returncode is not None else 'CLEANUP_FAILED')
            else:
                result=subprocess.run(argv,cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=timeout,check=False)
                code=result.returncode
        except subprocess.TimeoutExpired:
            code=124;timed_out=True
        except OSError as error:
            code=127;output.write(str(error).encode())
    return {'argv':list(argv),'cwd':str(Path(cwd).resolve()),'startedAt':start,'endedAt':now(),'exitCode':code,'timedOut':timed_out,'elapsedSeconds':time.monotonic()-began,'outputSha256':sha256(log),
            'pid':pid,'processGroup':pid if owned_process_group else None,'groupCleanup':cleanup,'environmentSha256':None if env is None else canonical_hash(env)}
