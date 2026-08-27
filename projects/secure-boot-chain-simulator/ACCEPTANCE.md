# ACCEPTANCE — the definition of done

## Hard gates
- [x] `make check` green: `ruff check`, `ruff format --check`, `mypy --strict src/`, `pytest` ≥85% coverage on `src/secboot` (currently 97%).
- [x] `make demo` completes in <20 s on a laptop with no network access (≈3 s).
- [x] Fresh clone → `make setup && make demo` works with no manual steps.
- [x] `python -m secboot --help` and every subcommand's `--help` are accurate.

## Functional gates
- [x] All 16 reason codes in SPEC §4 are individually reachable and tested, each asserting that no later check ran.
- [x] A valid signature over an old SVN is **rejected** (this is the single most important test).
- [x] After `secboot revoke --key-id N`, an image that previously booted is rejected.
- [x] `advance()` cannot lower a counter through any public API path.
- [x] `secboot confirm-boot` is required before an SVN advance becomes permanent.
- [x] `audit verify` detects a single-byte edit anywhere in the log and reports the sequence number.
- [x] Attestation quote over the PCR bank verifies against the golden set, and diverges by exactly
      one PCR when the app image is corrupted.
- [x] 500 random mutations of a valid image produce reason codes, never tracebacks.

## Quality gates
- [x] No private key material is reachable outside `hsm.py` (enforced by test).
- [x] All digest comparisons on the verification path use `hmac.compare_digest`.
- [x] Every module docstring names the real-world component it models.
- [x] README contains the standards table and the simulation disclaimer above the fold.
- [x] `docs/decisions.md` records the counter-advance-timing tradeoff and at least four other ADRs.

---

## Notes against the gates

Every box above is ticked and enforced by something that fails the build, not by
inspection. Where the implementation differs from `SPEC.md`, the difference is
recorded as an ADR rather than left implicit:

- **Python 3.11, not 3.12** — ADR-0001. Nothing here needs a 3.12 feature and the
  repository's floor is 3.11.
- **`docs/decisions.md` holds ten ADRs**, not five. The counter-advance timing
  tradeoff is ADR-0002.
- **Container digest stays SHA-256** while signature hashes follow `algo_id` —
  ADR-0005, which is the honest half-answer to the SHA-384 suggestion in
  `CORRECTIONS.md`.
- **Coverage is 97%** against an 85% floor; the floor is enforced in `make test`
  so it cannot drift downward unnoticed.
- **The project workflow is `.github/workflows/secboot.yml`** at the repository
  root, not inside the project — GitHub only runs workflows from the root. A
  test in `tools/labctl` fails if that workflow ever runs a command
  `make check` here does not reach.
