#!/usr/bin/env bash
# F0 sensitivity controls for ledger/test/F0Powers.t.sol and F0Quorum.t.sol (agent 1, F0 planning; no
# production change). Copies ledger/{src,test,script,foundry.toml} into SCRATCH, removes one injected fault
# per variant and runs the matching repaired-e test there. A control PASSES when the fault-free variant
# FAILS: the characterization test then depends on the fault, not on unrelated state. The checkout is never
# edited. Usage (repository root, forge on PATH): ledger/tools/f0_controls.sh <empty scratch dir>
set -u
SCRATCH=${1:?usage: f0_controls.sh <empty scratch dir>}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$SCRATCH"
[ -z "$(ls -A "$SCRATCH")" ] || { echo "scratch dir must be empty: $SCRATCH" >&2; exit 2; }
cp -r "$ROOT/ledger/src" "$ROOT/ledger/test" "$ROOT/ledger/script" "$ROOT/ledger/foundry.toml" "$SCRATCH/"
for f in F0Powers.t.sol F0Quorum.t.sol; do cp "$SCRATCH/test/$f" "$SCRATCH/test/$f.orig"; done
failures=0
control() { # name, test file, contract, sed program, test name
  T="$SCRATCH/test/$2"
  cp "$T.orig" "$T"
  sed -i "$4" "$T"
  if cmp -s "$T" "$T.orig"; then echo "CONTROL $1: ERROR sed changed nothing"; failures=$((failures + 1)); return; fi
  out=$(forge test --root "$SCRATCH" --match-path "test/$2" --match-contract "$3" --match-test "^$5" 2>&1)
  rc=$?
  cp "$T.orig" "$T"
  line=$(printf '%s\n' "$out" | grep -E '^\[(PASS|FAIL)' | head -1)
  if [ -z "$line" ]; then
    echo "CONTROL $1: ERROR no test ran (exit $rc)"; failures=$((failures + 1))
  elif [ "$rc" -ne 0 ] && printf '%s' "$line" | grep -q '^\[FAIL'; then
    echo "CONTROL $1: OK (fault removed -> test fails) $line"
  else
    echo "CONTROL $1: NOT SENSITIVE (exit $rc) $line"; failures=$((failures + 1))
  fi
}
P=F0Powers.t.sol; PC=F0PowersRepairedTest
control unrelated-authority-update $P $PC \
  '/publishCrl(h3, h3Pk, h3Admin, 1, new uint64\[\](0));$/d; /publishCrl(h4, h4Pk, h4Admin, 1, new uint64\[\](0));$/d' \
  test_F0_UnrelatedAuthorityUpdateInvalidatesOtherUsersRequests
control poison-sequence $P $PC '/poison.sequence = type(uint64).max;/d' test_F0_PoisonCheckpointSequenceBlocksTheDbc
control poison-authepoch $P $PC '/poison.authEpoch = tmsc.authEpoch() + 1_000_000;/d' \
  test_F0_PoisonCheckpointAuthEpochBlocksTheDbc
control poison-policyversion $P $PC '/poison.policyVersion = POLICY_VERSION + 1;/d' \
  test_F0_PoisonCheckpointPolicyVersionBlocksTheDbc
control unrevoke-by-omission $P $PC '/publishCrl(h1, h1Pk, h1Admin, 3, new uint64\[\](0));/d' \
  test_F0_AuthorityUnrevokesBySerialOmission
control fabricated-records $P $PC \
  's/certify(decisionFor(r, RESULT_ALLOW, fake, cp), witnessPk);/certify(decisionFor(r, RESULT_ALLOW, verifiedRecords(bob, bobBundle()), cp), witnessPk);/; s/acsc.consumeDecision(r, c, fake);/acsc.consumeDecision(r, c, verifiedRecords(bob, bobBundle()));/' \
  test_F0_SingleWitnessAttestsFabricatedRecords
control one-authority-own-gid $P $PC \
  's/publishAcl(onDutyAcl(h3, 1, one(mallory)), h3Pk, h3Admin);/publishAcl(onDutyAcl(h3, 1, one(alice)), h3Pk, h3Admin);/' \
  test_F0_OneAuthorityAloneAuthorizesItsOwnGidForAnotherHospitalsRecord
Q=F0Quorum.t.sol; QC=F0QuorumRepairedTest
control q-two-of-four $Q $QC 's/bytes\[\] memory s = signWith(cp, sorted(ids(0, 1)));/bytes[] memory s = signWith(cp, sorted(ids(0, 1, 2)));/' \
  test_F0Q_TwoOfFourInsufficient
control q-duplicate-signer $Q $QC 's/(pks\[0\], pks\[1\], pks\[2\]) = (two\[0\], two\[1\], two\[1\]);/pks = sorted(ids(0, 1, 2));/' \
  test_F0Q_DuplicateSignerRejected
control q-unknown-signer $Q $QC \
  's/uint256\[\] memory pks = new uint256\[\](4);/uint256[] memory pks = new uint256[](3);/; s/(pks\[0\], pks\[1\], pks\[2\], pks\[3\]) = (three\[0\], three\[1\], three\[2\], malloryPk);/(pks[0], pks[1], pks[2]) = (three[0], three[1], three[2]);/' \
  test_F0Q_UnknownSignerRejectsWholeCertificate
control q-other-set-version $Q $QC '/cp.witnessSetVersion = WITNESS_SET_VERSION + 1;/d' test_F0Q_OtherWitnessSetVersionRejected
control poison-sourceblocknumber $Q F0SourceBlockPoisonRepairedTest '/poison.sourceBlockNumber = type(uint256).max;/d' \
  test_F0_PoisonCheckpointSourceBlockNumberBlocksTheDbc
echo "controls not sensitive or broken: $failures"
[ "$failures" -eq 0 ]
