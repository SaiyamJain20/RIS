#!/usr/bin/env bash
# F0 sensitivity controls for ledger/test/F0Powers.t.sol (agent 1, F0 planning; no production change).
# Copies ledger/{src,test,script,foundry.toml} into SCRATCH, removes one injected fault per variant and
# runs the matching repaired-e test there. A control PASSES when the fault-free variant FAILS: the
# characterization test then depends on the fault, not on unrelated state. The checkout is never edited.
# Usage (repository root, forge on PATH): ledger/tools/f0_controls.sh <empty scratch dir>
set -u
SCRATCH=${1:?usage: f0_controls.sh <empty scratch dir>}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$SCRATCH"
[ -z "$(ls -A "$SCRATCH")" ] || { echo "scratch dir must be empty: $SCRATCH" >&2; exit 2; }
cp -r "$ROOT/ledger/src" "$ROOT/ledger/test" "$ROOT/ledger/script" "$ROOT/ledger/foundry.toml" "$SCRATCH/"
T="$SCRATCH/test/F0Powers.t.sol"
cp "$T" "$T.orig"
failures=0
control() { # name, sed program, test name
  cp "$T.orig" "$T"
  sed -i "$2" "$T"
  if cmp -s "$T" "$T.orig"; then echo "CONTROL $1: ERROR sed changed nothing"; failures=$((failures + 1)); return; fi
  out=$(forge test --root "$SCRATCH" --match-path test/F0Powers.t.sol --match-contract F0PowersRepairedTest \
    --match-test "^$3" 2>&1)
  rc=$?
  line=$(printf '%s\n' "$out" | grep -E '^\[(PASS|FAIL)' | head -1)
  if [ -z "$line" ]; then
    echo "CONTROL $1: ERROR no test ran (exit $rc)"; failures=$((failures + 1))
  elif [ "$rc" -ne 0 ] && printf '%s' "$line" | grep -q '^\[FAIL'; then
    echo "CONTROL $1: OK (fault removed -> test fails) $line"
  else
    echo "CONTROL $1: NOT SENSITIVE (exit $rc) $line"; failures=$((failures + 1))
  fi
}
control unrelated-authority-update \
  '/publishCrl(h3, h3Pk, h3Admin, 1, new uint64\[\](0));$/d; /publishCrl(h4, h4Pk, h4Admin, 1, new uint64\[\](0));$/d' \
  test_F0_UnrelatedAuthorityUpdateInvalidatesOtherUsersRequests
control poison-sequence '/poison.sequence = type(uint64).max;/d' test_F0_PoisonCheckpointSequenceBlocksTheDbc
control poison-authepoch '/poison.authEpoch = tmsc.authEpoch() + 1_000_000;/d' test_F0_PoisonCheckpointAuthEpochBlocksTheDbc
control poison-policyversion '/poison.policyVersion = POLICY_VERSION + 1;/d' test_F0_PoisonCheckpointPolicyVersionBlocksTheDbc
control unrevoke-by-omission '/publishCrl(h1, h1Pk, h1Admin, 3, new uint64\[\](0));/d' test_F0_AuthorityUnrevokesBySerialOmission
control fabricated-records \
  's/certify(decisionFor(r, RESULT_ALLOW, fake, cp), witnessPk);/certify(decisionFor(r, RESULT_ALLOW, verifiedRecords(bob, bobBundle()), cp), witnessPk);/; s/acsc.consumeDecision(r, c, fake);/acsc.consumeDecision(r, c, verifiedRecords(bob, bobBundle()));/' \
  test_F0_SingleWitnessAttestsFabricatedRecords
control one-authority-own-gid \
  's/publishAcl(onDutyAcl(h3, 1, one(mallory)), h3Pk, h3Admin);/publishAcl(onDutyAcl(h3, 1, one(alice)), h3Pk, h3Admin);/' \
  test_F0_OneAuthorityAloneAuthorizesItsOwnGidForAnotherHospitalsRecord
cp "$T.orig" "$T"
echo "controls not sensitive or broken: $failures"
[ "$failures" -eq 0 ]
