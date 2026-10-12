#!/usr/bin/bash
export PATH=/home/karma/.local/share/hmbc-tools/foundry-1.8.5:/usr/local/bin:/usr/bin:/bin
export HMBC_FOUNDRY_DIR=/home/karma/.local/share/hmbc-tools/foundry-1.8.5
export FOUNDRY_SOLC=/home/karma/.local/share/svm/0.8.37/solc-0.8.37
export HMBC_TEST_PORT_RANGE=19545-19699
exec .venv/bin/python -m pytest protocol/tests -q -rs -c protocol/pytest.ini --rootdir protocol
