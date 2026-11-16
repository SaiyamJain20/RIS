#!/usr/bin/env bash
# Fresh M1/M1b/M1c reproduction on clean archives of ledger 85c59f5; raw logs retained.
export PATH="$HOME/.foundry/bin:$PATH"
R=/home/saiyamjain/Desktop/RIS/Project; S=/home/saiyamjain/.claude/jobs/aed51961/tmp/a1/gaslogs-20261115
L=85c59f588de58a8ff5e87b9fe6f630c9d8c43642
{ forge --version; echo "solc per ledger/foundry.toml"; date -Is; } > $S/versions.txt 2>&1
mk() { rm -rf "$S/$1"; mkdir -p "$S/$1"; git -C $R archive $L ledger | tar -x -C "$S/$1"; }
mk sizes; (cd $S/sizes && forge build --root ledger --sizes > $S/sizes.log 2>&1; echo $? > $S/sizes.exit)
mk m1;  git -C $R show 70a8bfe:evaluation/measurements/CertBench.t.sol > $S/m1/ledger/test/CertBench.t.sol
(cd $S/m1 && forge test --root ledger --match-path 'test/CertBench*.t.sol' -vvvv > $S/m1.log 2>&1; echo $? > $S/m1.exit)
mk m1b; git -C $R show 8152bcc:evaluation/measurements/CertBench.t.sol > $S/m1b/ledger/test/CertBench.t.sol
(cd $S/m1b && forge test --root ledger --match-path test/CertBench.t.sol -vvvv > $S/m1b.log 2>&1; echo $? > $S/m1b.exit)
mk m1c; git -C $R show 674511f:evaluation/measurements/CertBenchGov.t.sol > $S/m1c/ledger/test/CertBenchGov.t.sol
(cd $S/m1c && forge test --root ledger --match-path test/CertBenchGov.t.sol --match-test test_gov_ -vvvv > $S/m1c.log 2>&1; echo $? > $S/m1c.exit)
sha256sum $S/m1/ledger/test/CertBench.t.sol $S/m1b/ledger/test/CertBench.t.sol $S/m1c/ledger/test/CertBenchGov.t.sol > $S/harness-sha256.txt
echo DONE
