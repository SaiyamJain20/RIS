#!/usr/bin/env bash
# Fresh deploy (fast mode) of repaired-f and mutant-f-q2, then read threshold() on chain and compare with the manifest.
set -u
export PATH="$HOME/.foundry/bin:$PATH"
R=/home/saiyamjain/Desktop/RIS/Project; S=/home/saiyamjain/.claude/jobs/aed51961/tmp/a1/deploy-dryrun-20261116
L=85c59f588de58a8ff5e87b9fe6f630c9d8c43642
DEPLOYER_PK=$(cast wallet private-key --mnemonic "test test test test test test test test test test test junk" --mnemonic-index 0); export DEPLOYER_PK
for prof in repaired-f mutant-f-q2; do
  name=rb-$prof; X=$S/$name; rm -rf $X; mkdir -p $X; git -C $R archive $L ledger | tar -x -C $X
  anvil --port 17545 --chain-id 18545 --silent >/dev/null 2>&1 & p1=$!
  anvil --port 17546 --chain-id 28545 --silent >/dev/null 2>&1 & p2=$!
  for i in $(seq 1 50); do cast chain-id --rpc-url http://127.0.0.1:17545 >/dev/null 2>&1 && cast chain-id --rpc-url http://127.0.0.1:17546 >/dev/null 2>&1 && break; sleep 0.2; done
  ( cd $X && LEDGER_DEPLOY_FAST=1 ledger/tools/deploy_local.sh http://127.0.0.1:17545 http://127.0.0.1:17546 $prof complete-details $name > $S/$name.log 2>&1; echo "deploy exit $?" )
  M=$X/ledger/exports/deployments/$name/deployment.json
  mt=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["fixture"]["witnessSet"]["threshold"])' $M)
  for c in pbc:PSC pbc:Governance dbc:KSSC; do ch=${c%%:*}; n=${c##*:}; port=$([ $ch = pbc ] && echo 17545 || echo 17546)
    a=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["chains"][sys.argv[2]]["contracts"][sys.argv[3]])' $M $ch $n 2>/dev/null)
    echo "$prof $ch.$n manifest-threshold=$mt onchain-threshold=$(cast call --rpc-url http://127.0.0.1:$port $a 'threshold()(uint256)' 2>&1)"
  done
  kill $p1 $p2; wait $p1 $p2 2>/dev/null
done
unset DEPLOYER_PK
