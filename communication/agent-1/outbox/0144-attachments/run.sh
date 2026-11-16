#!/usr/bin/env bash
# Agent 1 check of the two ledger owner-baseline commands in A3-0162's DRAFT recipe, on a clean 85c59f5 extract.
export PATH="$HOME/.foundry/bin:$PATH"; S=/home/saiyamjain/.claude/jobs/aed51961/tmp/a1/baseline-check-20261116; cd $S
forge --version | head -1 > versions.txt; python3 --version >> versions.txt
forge test --root ledger --offline --use "$HOME/.svm/0.8.37/solc-0.8.37" > ledger-tests.txt 2>&1; echo $? > ledger-tests.exit
python3 -I ledger/tools/check_mutants.py > ledger-mutants.txt 2>&1; echo $? > ledger-mutants.exit
echo DONE
