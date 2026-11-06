# Scoped findings and refuted controls

Classification: tested reconstruction behavior / local configuration robustness.
Not a paper vulnerability, remote exploit or incorrect authorization finding.

- `protocol/hmbc_protocol/adapter_v2_main.py:108/113`: strict JSON parsing accepts numeric `1e999` as infinity; int(chainId) raises uncaught OverflowError. CLI exits1 with a traceback. Validate canonical chainId before conversion (or narrowly map overflow) and test both chain sides; refuse with one MALFORMED object, exit2, no state. Valid published chain IDs are decimal strings; the corrupt fixture violates that rule.
- `protocol/hmbc_protocol/adapter_v2_main.py:70-77/117-124`: `_schema` returns any parsed JSON. A matching-hash array reaches Context._validate_against and raises uncaught AttributeError. Require a JSON object and required published schema structure before the startup path; test arrays and null with their supplied matching hashes. Null reaches an unavailable ledger in this run; it has not been tested through a successful native startup. The configured hash is caller input; this requires corrupt operator config, not an alteration under the real frozen schema hash.

No state path was created by any of the four diagnostics. With the actual
published schema: valid result accepted, uint64 overflow result refused. Seven
ABI hashes load; an altered byte refuses. Old/current worker comparison preserves
all tested E profiles and repairs the valid profile3 case while refusing bad
recipients. This is not full E integration parity.

A2-0072 answers A3-0095 exactly: ordinary skips recover with current+1; saturated
uint64 does not. Six focused owner characterization cases pass; the previous
ledger experiment is not rerun here. No ledger/interface patch requested.

Owner live/fullsuite/mutation results and default bare-library schema-helper
checks are not independently adopted. Four unwired CLI witness handlers and
missing complete runtime READY remain explicit. No ACK or gate follows.
