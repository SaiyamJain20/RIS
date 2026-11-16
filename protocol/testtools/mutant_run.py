"""TEST-ONLY launcher: start one allowed module from a built mutant tree by EXEC (agent 2, F phase; gap G3). PAPER-DERIVED RECONSTRUCTION. Not imported by any production module; not an adapter operation.

    python -m testtools.mutant_run --tree /abs/tree --mutant M1 --module hmbc_protocol.witness_main -- <the module's own arguments>

It checks that the tree is an untampered build of the named mutant (`testtools.mutant_tree.verify_tree`), then changes the working directory to the tree and replaces itself (`os.execv`) with
`python -B -m MODULE ARGS...`. Because `-m` puts the working directory first on `sys.path`, the module AND everything it imports come from the mutated tree; the process keeps the launcher's pid, so a supervisor's pid
file, a SIGSTOP and a SIGKILL name the real process. Child processes of the started module (the adapter's supervised witnesses) inherit the working directory and therefore also run the tree's code.
Allow-list (nothing else is started): `hmbc_protocol.witness_main` (it refuses a deployment that does not declare a TEST-ONLY key derivation), `testtools.faulty_adapter_v2` (it refuses a deployment that does
not declare TEST-ONLY synthetic keys, even with no variant) and `testtools.mutant_probe` (prints facts for tests). A path argument must be absolute (the working directory changes); a refusal is ONE closed line
`refusing: ...` on stderr, exit 2, nothing on stdout, nothing started, no path echoed.
"""
from __future__ import annotations

import os
import sys

from testtools import mutant_tree as mt

ALLOWED = ("hmbc_protocol.witness_main", "testtools.faulty_adapter_v2", "testtools.mutant_probe")


def _refuse(msg: str) -> int:
    sys.stderr.write(f"refusing: {msg}\n")
    return 2


def _parse(argv):
    """`--tree T --mutant M --module X [-- args...]`: exactly these flags, each once, before an optional `--`."""
    if "--" in argv:
        i = argv.index("--")
        head, rest = argv[:i], argv[i + 1:]
    else:
        head, rest = argv, []
    if len(head) % 2 or any(not a.startswith("--") for a in head[::2]):
        return None
    flags = {}
    for k, v in zip(head[::2], head[1::2]):
        if k in flags or k not in ("--tree", "--mutant", "--module"):
            return None
        flags[k] = v
    if set(flags) != {"--tree", "--mutant", "--module"}:
        return None
    return flags["--tree"], flags["--mutant"], flags["--module"], rest


def main(argv) -> int:
    parsed = _parse(argv)
    if parsed is None:
        return _refuse("usage: --tree ABSOLUTE_DIR --mutant ID --module MODULE [-- module arguments]")
    tree, mutant, module, rest = parsed
    if module not in ALLOWED:
        return _refuse("the module is not on the allow-list")
    for a in rest:
        if not a.startswith("-") and ("/" in a or os.sep in a) and not os.path.isabs(a):
            return _refuse("a path argument must be absolute")
    try:
        mt.verify_tree(tree, mutant)
    except mt.MutantError as e:
        return _refuse(str(e))
    env = dict(os.environ, HMBC_MUTANT=mutant)
    os.chdir(tree)
    os.execve(sys.executable, [sys.executable, "-B", "-m", module, *rest], env)       # never returns
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
