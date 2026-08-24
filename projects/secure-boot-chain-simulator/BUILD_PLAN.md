# BUILD_PLAN — phase order

Work one phase at a time. Run `make check` at the end of each. Commit per phase with a
conventional-commit message. Do not start phase N+1 until phase N's acceptance criteria pass.

## Phase 0 — Scaffold (30 min)
- `pyproject.toml` (name `secboot`, Python ≥3.12, deps: `cryptography`, `typer`, `rich`;
  dev: `pytest`, `pytest-cov`, `ruff`, `mypy`).
- `Makefile`: `setup`, `check` (ruff + mypy --strict + pytest), `demo`, `clean`.
- `src/secboot/reasons.py` with the full `ReasonCode` StrEnum from SPEC §4.
- CI workflow running `make check` on Linux + macOS, Python 3.12 and 3.13.
**Accept:** `make check` passes on an empty test suite; `python -m secboot --help` prints.

## Phase 1 — Image container
- `image.py`: `ImageHeader` dataclass, `pack()`, `unpack()`, exact byte layout from SPEC §3.
- Property test: pack→unpack round-trips for random valid headers.
- Mutation test: for 500 random single-byte mutations of a valid image, `unpack()` either returns a
  valid structure or a `ReasonCode` — it never raises.
**Accept:** `test_image_roundtrip.py` and `test_malformed_images.py` green.

## Phase 2 — HSM + key management
- `hsm.py` per SPEC §7, encrypted keystore, ECDSA P-256 and Ed25519 backends.
- `secboot keygen`, `secboot hsm slots`.
- `test_hsm_isolation.py`: asserts no module outside `hsm.py` references private-key attributes
  (implement as an AST scan of `src/`, not a regex over strings).
**Accept:** keys survive a process restart; private bytes never appear in any public return value.

## Phase 3 — Fuses, counters, policy
- `fuses.py` (§5) with the monotonic-only API, `pending_svn` + confirm flow, exhaustion handling.
- `policy.py`: algorithm allowlist, lifecycle state, revocation bitmap.
- `secboot fuses init|show`, `secboot revoke`, `secboot confirm-boot`.
**Accept:** `test_rollback.py` proves `advance()` to an equal or lower value is impossible through
the public API, and that a factory-reset is refused in PRODUCTION lifecycle state.

## Phase 4 — Verification + boot orchestration
- `verify.py` implementing SPEC §4 **in the specified order**, returning `VerifyResult`.
- `machine.py`: ROM→SBL→APP orchestration, halts on first REJECT, never transfers control after one.
- `test_verify_order.py`: for each reason code, craft an image that trips exactly that code and
  assert no later check ran (assert on the audit event sequence, which makes ordering observable).
**Accept:** all 16 reason codes reachable and individually tested.

## Phase 5 — Measure, audit, attest
- `measure.py` PCR bank, `audit.py` hash-chained JSONL, `secboot attest`, `secboot audit verify|tamper`.
**Accept:** `audit verify` identifies the tampered sequence number exactly; a corrupted app produces
a PCR2 that differs from the golden quote.

## Phase 6 — Attacker CLI + demo
- `attack_cli.py` with all five attacks from SPEC §9.
- `secboot demo` running the eight scenarios from SPEC §10 with `rich` narration.
- `test_demo_golden.py`: `--seed 1337` output matches `tests/golden/demo.txt`.
**Accept:** `make demo` runs end to end in under 20 seconds and every scenario's outcome matches
the table in SPEC §10.

## Phase 7 — Documentation
- `README.md`: 60-second pitch, architecture diagram (ASCII, committed — not an image dependency),
  one-command quickstart, the eight scenarios with real captured output, standards table, an
  explicit "this is a simulation" disclaimer, and a "how to extend" section.
- `docs/threat-model.md`: assets, threat actors, attack tree from a compromised OTA server and from
  physical flash access, and which control in this repo addresses each leaf. Use a STRIDE table.
- `docs/reason-codes.md`, `docs/standards-references.md`, `docs/verified-vs-measured-boot.md`,
  `docs/decisions.md` (ADR-style, one entry per non-obvious choice).
- Record an `asciinema` cast of `make demo` and link it. If asciinema is unavailable, commit the
  captured text output to `docs/demo-output.md`.
**Accept:** a reader who knows nothing about secure boot can explain rollback protection after
reading the README.

## Phase 8 (optional) — C reference verifier
Per SPEC §11. Only start this if Phases 0–7 are complete and green.

## Phase 9 (optional) — PQ signature backend
Probe for ML-DSA support (see CLAUDE.md). Add `--algo ml-dsa-65` as an optional extra, plus a
`docs/post-quantum.md` explaining why firmware signing is the *first* migration target
(CNSA 2.0 names it as such) and why stateful hash-based schemes (LMS/XMSS, SP 800-208) are the
conservative choice for a 20-year vehicle lifetime while ML-DSA is the general-purpose one.
