#!/usr/bin/env bash
# A-F1 sensitivity controls (agent 1, phase F). Copies ledger/{src,test,script,foundry.toml} into SCRATCH,
# injects ONE fault into the implementation per variant and runs the named A-F1 test there. A control
# PASSES when the faulty source makes that test FAIL: the test then depends on the implemented rule, not on
# unrelated state. Bits 6-8 are covered separately by the code-level mutants (tools/check_mutants.py).
# The checkout is never edited. Usage (repository root, forge on PATH): ledger/tools/af1_controls.sh <empty dir>
set -u
SCRATCH=${1:?usage: af1_controls.sh <empty scratch dir>}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$SCRATCH"
[ -z "$(ls -A "$SCRATCH")" ] || { echo "scratch dir must be empty: $SCRATCH" >&2; exit 2; }
cp -r "$ROOT/ledger/src" "$ROOT/ledger/test" "$ROOT/ledger/script" "$ROOT/ledger/foundry.toml" "$SCRATCH/"
for f in types/ProtocolTypes.sol TMSC.sol Governance.sol; do cp "$SCRATCH/src/$f" "$SCRATCH/src/$f.orig"; done
failures=0
control() { # name, source file (under src/), sed program, test file, test contract, test name
  F="$SCRATCH/src/$2"
  cp "$F.orig" "$F"
  sed -i "$3" "$F"
  if cmp -s "$F" "$F.orig"; then echo "CONTROL $1: ERROR sed changed nothing"; failures=$((failures + 1)); return; fi
  out=$(forge test --root "$SCRATCH" --match-path "test/$4" --match-contract "$5" --match-test "^$6" 2>&1)
  rc=$?
  cp "$F.orig" "$F"
  line=$(printf '%s\n' "$out" | grep -E '^\[(PASS|FAIL)' | head -1)
  if [ -z "$line" ]; then
    echo "CONTROL $1: ERROR no test ran (exit $rc)"; printf '%s\n' "$out" | grep -E 'Error' | head -3; failures=$((failures + 1))
  elif [ "$rc" -ne 0 ] && printf '%s' "$line" | grep -q '^\[FAIL'; then
    echo "CONTROL $1: OK (fault injected -> test fails) $line"
  else
    echo "CONTROL $1: NOT SENSITIVE (exit $rc) $line"; failures=$((failures + 1))
  fi
}
T=types/ProtocolTypes.sol
control guard-e-allows-f-bits $T 's/return p == Profile.REPAIRED_E \&\& m \& ~MUT_E_BITS == 0;/return p == Profile.REPAIRED_E;/' \
  ProfileF.t.sol ProfileFTest test_AF1_RepairedERejectsTheFBits
control isrepaired-e-only $T 's/return p == Profile.REPAIRED_E || p == Profile.REPAIRED_F;/return p == Profile.REPAIRED_E;/' \
  ProfileF.t.sol ProfileFTest test_AF1_RepairedFValidatesTheWitnessSet
M=TMSC.sol; G=Governance.t.sol; GC=GovernanceTest
control wiring-without-governance $M '/if (profile == Profile.REPAIRED_F \&\& governance == address(0)) revert/d' \
  $G $GC test_AF1G_TmscRequiresGovernanceWiringOnlyUnderF
control no-tombstone $M 's/if (isAuthority\[root\] || removedAuthority\[root\])/if (isAuthority[root])/' \
  $G $GC test_AF1G_RemovedRootCannotBeReAdded
control admin-flags-not-cleared $M '/isCaAdmin\[root\]\[list\[i\]\] = false;/d' $G $GC test_AF1G_SetCaAdminsByQuorum
control governance-no-epoch $M '/function _governanceUpdate/,/^    }/{/authEpoch += 1;/d}' \
  $G $GC test_AF1G_F28_DbcPostBarrierIsStaleState
control log-without-nonce $M 's/abi.encode(action, nonce, root, admins, msg.sender)/abi.encode(action, uint64(0), root, admins, msg.sender)/' \
  $G $GC test_AF1G_UpdateLogBindsActionNonceAndAdmins
control remove-keeps-root-listed $M '/_authorities.pop();/d' $G $GC test_AF1G_RemoveAuthorityByQuorum
control any-caller $M '/function _onlyGovernance/,/^    }/{/if (msg.sender != governance) revert/d}' \
  $G $GC test_AF1G_OnlyGovernanceMayCallTmscMutators
control any-profile $M '/function _onlyGovernance/,/^    }/{/if (profile != Profile.REPAIRED_F) revert/d}' \
  $G $GC test_AF1G_MutatorsRejectNonFProfilesAndUnsealed
V=Governance.sol
control no-set-version-check $V '/if (m.witnessSetVersion != witnessSetVersion) revert/d' \
  $G $GC test_AF1G_WrongWitnessSetVersionIsStaleStateFirst
control nine-admins $V 's/if (n > GOV_MAX_ADMINS ||/if (n > GOV_MAX_ADMINS + 1 ||/' $G $GC test_AF1G_StructuralRulesAreMalformed
control nonce-gap-allowed $V '/if (m.nonce > governanceNonce + 1) revert/d' $G $GC test_AF1G_NonceReplayAndGap
echo "controls not sensitive or broken: $failures"
[ "$failures" -eq 0 ]
