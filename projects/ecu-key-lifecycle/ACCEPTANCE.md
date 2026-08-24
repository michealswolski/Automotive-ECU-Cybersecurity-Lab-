# ACCEPTANCE - the definition of done

## Hard gates
- [ ] `make check` green: ruff, `mypy --strict src/`, pytest ≥85% coverage on `src/ekl`.
- [ ] `ekl demo` completes in under 60 seconds on a clean machine with no network.
- [ ] Fresh clone to running demo in under five minutes.
- [ ] Alembic migration up and down both succeed on an empty database.

## Correctness gates
- [ ] Every illegal state transition is rejected, proven by an exhaustively generated matrix test.
- [ ] `REVOKED` reachable from every non-terminal state; `DESTROYED` terminal.
- [ ] Every provisioning failure reason code in SPEC §5 is individually reachable and tested.
- [ ] A provisioning package for ECU-A is rejected by ECU-B (`AAD_MISMATCH`).
- [ ] A replayed provisioning nonce is rejected (`NONCE_REPLAYED`).
- [ ] Rotation with 20% of the fleet offline produces a correct partial-state report.
- [ ] A revocation list with a lower version number than the current one is rejected.
- [ ] A key past its cryptoperiod is flagged by `policy check` and refused by `use()`, driven by the
      fake clock rather than by sleeping.
- [ ] `audit verify` detects a single-character edit and names the exact sequence number.

## Quality gates
- [ ] No code path anywhere returns private key material outside the HSM and storage modules.
      Enforced by an AST-based test, not a string grep.
- [ ] `lifecycle.py` and `policy.py` import nothing from `persistence/`.
- [ ] No key material appears in any audit line, log line, or CLI output. Enforced by test.
- [ ] Time is injected everywhere; `datetime.now()` appears only in `clock.py`.
- [ ] Every standards citation in the README was verified by search, not recalled.
- [ ] README states this is a simulation, above the fold.
