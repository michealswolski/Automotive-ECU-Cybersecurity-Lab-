# BUILD_PLAN - phase order

One phase at a time. `make check` after each. Do not advance until acceptance criteria pass.

## Phase 0 - Scaffold
`pyproject.toml` (deps: `cryptography`, `typer`, `rich`, `sqlalchemy`, `alembic`, `pydantic`;
optional `fastapi`+`uvicorn` extra; dev: `pytest`, `pytest-cov`, `hypothesis`, `ruff`, `mypy`).
`Makefile` (`setup|check|demo|clean`). `reasons.py` with the full ReasonCode enum from SPEC §5.
`clock.py` with a real and a fake time source. CI on Linux + macOS.
**Accept:** `make check` green; `ekl --help` prints.

## Phase 1 - Lifecycle state machine (do this before any persistence)
`lifecycle.py`: states, the transition table, `transition(state, event) -> Result`. Pure, no I/O,
no database.
`test_lifecycle_transitions.py`: every legal edge asserted, and **every illegal edge** asserted to
return `IllegalTransition`. Generate the illegal set programmatically as
`all_pairs - legal_pairs` so no edge is missed by hand.
**Accept:** the full transition matrix is covered; REVOKED reachable from all non-terminal states;
DESTROYED terminal.

## Phase 2 - Simulated HSM and derivation
`authority/hsm.py` (non-exportable key custody, Ed25519 + ECDSA P-256 + AES-256, encrypted keystore
at rest via Scrypt-derived KEK). `authority/derive.py` (HKDF-SHA256 with domain-separated info
strings including `generation`).
**Accept:** derivation is deterministic for identical inputs and diverges on any single input change,
including generation; no API returns private key bytes.

## Phase 3 - Persistence
`persistence/models.py` (SQLAlchemy 2.x typed models), `repo.py` (repository interface consumed by
the domain), Alembic initial migration.
**Accept:** `lifecycle.py` and `policy.py` import nothing from `persistence/` (assert this with an
AST-based test); a full up/down migration cycle succeeds.

## Phase 4 - ECU side
`ecu/device.py` (device identity keygen on-device, CSR/attestation), `ecu/storage.py` (protected
storage, `use()` with no `get_key()`, slot limits, zeroize), `ecu/agent.py` (the ECU's half of the
ceremony).
**Accept:** `test_storage_boundary.py` proves no code path returns key material; slot exhaustion
returns `NO_FREE_SLOT`.

## Phase 5 - Provisioning ceremony
`authority/provision.py` implementing all nine steps of SPEC §5, with AAD binding.
`test_provisioning.py`: one test per failure reason code, plus the cross-ECU replay test.
**Accept:** every reason code in SPEC §5 is individually reachable; a package for ECU-A is rejected
by ECU-B with `AAD_MISMATCH`; a replayed nonce is rejected.

## Phase 6 - Audit
`audit.py` hash-chained JSONL, `ekl audit verify|tail|tamper|export`.
`test_audit_chain.py` and `test_no_key_material_in_logs.py`.
**Accept:** a single-character edit anywhere in the log is detected and the sequence number named;
no key material appears in any emitted line.

## Phase 7 - Rotation, revocation, policy
`rotate` with overlap window and `--simulate-offline`; `crl.py` signed versioned revocation list with
rollback protection; `policy.py` cryptoperiod checks driven by the injectable clock.
**Accept:** partial rotation state is correctly reported; an older CRL version is rejected; a key past
its cryptoperiod is flagged by `policy check` and refused by `use()`.

## Phase 8 - Demo and rendering
`render.py` rich views (key inventory, per-key lifecycle timeline, fleet generation dashboard).
`ekl demo` running all eight scenarios from SPEC §11. `attack.py` for the adversarial scenarios.
**Accept:** `ekl demo` completes in under 60 seconds, every scenario's outcome matches SPEC §11, and
`test_scenarios.py` asserts them.

## Phase 9 - Documentation
- `README.md`: the pitch (most people know the algorithms, not the lifecycle), the state-machine
  diagram in ASCII, quickstart, the eight scenarios with real captured output, the standards table,
  and the simulation disclaimer.
- `docs/lifecycle.md`: each state, what it means physically on a vehicle, and what can go wrong there.
- `docs/threat-model.md`: STRIDE over the KA, the transport, and the ECU. Be explicit about what this
  design does *not* stop (a compromised KA, a physically extracted device key).
- `docs/policy-basis.md`: where the default cryptoperiods came from, with verified citations.
- `docs/standards-references.md`, `docs/decisions.md` (ADRs: derivation vs storage, overlap window
  length, CRL fail-open vs fail-closed, why device keys are generated on-device).
**Accept:** a reader can explain the difference between key *distribution* and key *provisioning*
after reading the README.

## Phase 10 (optional, in value order)
1. `ekl serve` -- read-only FastAPI dashboard: fleet generation heatmap, keys expiring soon,
   audit chain status. This is the piece that photographs well.
2. Interoperate with the CAN SecOC project: export a provisioned `secoc-mac` key in that project's
   key file format so the two repos demonstrably compose. **Two projects that plug into each other is
   worth more in an interview than either alone.**
3. PQ readiness: a `--algo ml-dsa-65` option for the signing keys, gated on library availability,
   plus `docs/post-quantum.md` on crypto-agility in a fleet that stays on the road for twenty years.
