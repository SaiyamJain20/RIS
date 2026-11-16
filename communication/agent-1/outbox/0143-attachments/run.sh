#!/usr/bin/env bash
# Agent 1 deploy dry run of the plan's ledger deployment block (item 5, deploy portion).
# Fresh Anvil pair per run on agent-1 ports; pinned deploy_local.sh from a scratch git-archive extract.
# DEPLOYER_PK is derived at runtime from the public Anvil test mnemonic and passed only via the environment.
set -u
export PATH="$HOME/.foundry/bin:$PATH"
R=/home/saiyamjain/Desktop/RIS/Project; S=/home/saiyamjain/.claude/jobs/aed51961/tmp/a1/deploy-dryrun-20261116
L=85c59f588de58a8ff5e87b9fe6f630c9d8c43642
{ forge --version | head -1; anvil --version | head -1; date -Is; } > $S/versions.txt 2>&1
DEPLOYER_PK=$(cast wallet private-key --mnemonic "test test test test test test test test test test test junk" --mnemonic-index 0); export DEPLOYER_PK
run() {  # name profile successor fast
  local name=$1 prof=$2 succ=$3 fast=$4 X=$S/$1
  rm -rf $X; mkdir -p $X; git -C $R archive $L ledger | tar -x -C $X
  anvil --port 17545 --chain-id 18545 --silent > $X/anvil-pbc.log 2>&1 & local p1=$!
  anvil --port 17546 --chain-id 28545 --silent > $X/anvil-dbc.log 2>&1 & local p2=$!
  for i in $(seq 1 50); do cast chain-id --rpc-url http://127.0.0.1:17545 >/dev/null 2>&1 && cast chain-id --rpc-url http://127.0.0.1:17546 >/dev/null 2>&1 && break; sleep 0.2; done
  ( cd $X && SUCCESSOR_EXPORT=$succ LEDGER_DEPLOY_FAST=$fast ledger/tools/deploy_local.sh http://127.0.0.1:17545 http://127.0.0.1:17546 $prof complete-details $name > $S/$name.log 2>&1; echo $? > $S/$name.exit )
  kill $p1 $p2; wait $p1 $p2 2>/dev/null
  cp -r $X/ledger/exports/deployments/$name $S/$name-manifest 2>/dev/null || true
}
run dry-repaired-f       repaired-f  0 0
run dry-repaired-f-fast  repaired-f  0 1
run dry-mutant-f-q2      mutant-f-q2 0 0
run dry-repaired-e-succ  repaired-e  1 0
unset DEPLOYER_PK
echo DONE
