"""TEST-ONLY probe started by `testtools.mutant_run` in tests: prints ONE JSON line with the facts a test needs (pid, working directory, where `hmbc_protocol` and `testtools` were imported from, the mutant id of the
environment, the arguments it received) and exits 0. Not imported by any production module."""
import json
import os
import sys

import hmbc_protocol
import testtools

print(json.dumps({"pid": os.getpid(), "cwd": os.getcwd(), "hmbc_protocol": os.path.dirname(os.path.abspath(hmbc_protocol.__file__)), "testtools": os.path.dirname(os.path.abspath(testtools.__file__)),
                  "mutant": os.environ.get("HMBC_MUTANT"), "argv": sys.argv[1:]}, sort_keys=True))
