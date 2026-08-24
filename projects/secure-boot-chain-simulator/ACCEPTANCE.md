# ACCEPTANCE — the definition of done

## Hard gates
- [ ] `make check` green: `ruff check`, `ruff format --check`, `mypy --strict src/`, `pytest` ≥85% coverage on `src/secboot`.
- [ ] `make demo` completes in <20 s on a laptop with no network access.
- [ ] Fresh clone → `make setup && make demo` works with no manual steps.
- [ ] `python -m secboot --help` and every subcommand's `--help` are accurate.

## Functional gates
- [ ] All 16 reason codes in SPEC §4 are individually reachable and tested.
- [ ] A valid signature over an old SVN is **rejected** (this is the single most important test).
- [ ] After `secboot revoke --key-id N`, an image that previously booted is rejected.
- [ ] `advance()` cannot lower a counter through any public API path.
- [ ] `secboot confirm-boot` is required before an SVN advance becomes permanent.
- [ ] `audit verify` detects a single-byte edit anywhere in the log and reports the sequence number.
- [ ] Attestation quote over the PCR bank verifies against the golden set, and diverges by exactly
      one PCR when the app image is corrupted.
- [ ] 500 random mutations of a valid image produce reason codes, never tracebacks.

## Quality gates
- [ ] No private key material is reachable outside `hsm.py` (enforced by test).
- [ ] All digest comparisons on the verification path use `hmac.compare_digest`.
- [ ] Every module docstring names the real-world component it models.
- [ ] README contains the standards table and the simulation disclaimer above the fold.
- [ ] `docs/decisions.md` records the counter-advance-timing tradeoff and at least four other ADRs.
