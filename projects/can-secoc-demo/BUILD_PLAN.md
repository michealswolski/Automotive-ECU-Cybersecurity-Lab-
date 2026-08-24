# BUILD_PLAN - phase order

One phase at a time. `make check` at the end of each. Do not advance until acceptance criteria pass.

## Phase 0 - Scaffold
`pyproject.toml` (deps: `python-can`, `cryptography`, `typer`, `rich`, `pydantic`, `pyyaml`,
`matplotlib`; dev: `pytest`, `hypothesis`, `ruff`, `mypy`, `pytest-cov`). `Makefile` with
`setup|check|demo|clean`. `reasons.py` with the full ReasonCode enum. CI on Linux + macOS + Windows.
**Accept:** `make check` green on an empty suite; `secoc-demo --help` prints.

## Phase 1 - AES-CMAC and the known-answer tests
`cmac.py` wrapping `cryptography.hazmat.primitives.cmac`. `test_cmac_kat.py` with the four RFC 4493
AES-128 vectors. `secoc-demo kat` prints them.
**Accept:** all four vectors pass. Nothing else proceeds until they do.

## Phase 2 - Profiles, truncation, framing
`profiles.py` (frozen dataclasses for profiles 1/2/3 + full-cmac), `framing.py` (pack/unpack secured
PDU, classic CAN and CAN FD). Hypothesis property tests for MSB/LSB truncation correctness and
round-tripping.
**Accept:** `test_framing_property.py` green; `secoc-demo overhead --profile all` prints the table.

## Phase 3 - Authenticator core
`authenticator.py`: `DataToAuthenticator` construction (Data ID || payload || complete FV,
big-endian), `generate()`, `verify()`. No python-can import anywhere in this module.
**Accept:** `test_authenticator.py` green; `test_no_can_import.py` green.

## Phase 4 - Freshness management
`freshness.py`: complete FV composition, truncation, receiver-side window reconstruction with a
capped attempt count, monotonic acceptance, NVM persistence, sync message handling.
**Accept:** replay invariant property test green over 200 random frames; window boundary tests green.

## Phase 5 - Bus adapter and nodes
`bus.py` (virtual + socketcan, selected by config), `nodes.py` (SenderECU, ReceiverECU,
AttackerNode with a real capture buffer and byte-identical replay). `scripts/setup_vcan.sh` for Linux.
**Accept:** sender and receiver exchange authenticated frames on the `virtual` interface on this
machine, and on `vcan0` if you are on Linux.

## Phase 6 - Scenarios
`scenarios.py` implementing all eight scenarios from SPEC §6, each writing `results/<name>.jsonl`.
`test_scenarios.py` asserting each verdict.
**Accept:** `secoc-demo run --scenario all` completes and every verdict matches the SPEC table.
Specifically: `baseline` accepts the replay, `replay` rejects it, `no-fv` accepts it.

## Phase 7 - Presentation
`render.py` rich live view; `secoc-demo report` producing markdown + matplotlib charts;
`secoc-demo bench` measuring MAC generate/verify latency and the resulting frame-rate ceiling.
**Accept:** report renders with real captured data; bench prints microseconds per operation from an
actual measurement on this machine.

## Phase 8 - Documentation
- `README.md`: the two-minute pitch, an ASCII bus diagram, quickstart, the scenario table with real
  captured output, the overhead table, the charts, the standards mapping, and the
  "this is a demonstration, not a certified stack" disclaimer.
- `docs/how-secoc-works.md`: explain freshness, truncation, and the MSB/LSB trap, with worked
  byte-level examples from your own implementation.
- `docs/threat-model.md`: what SecOC does and does not address on a CAN bus (it addresses forgery
  and replay; it does not address DoS, suppression, or a compromised-but-legitimate ECU).
- `docs/decisions.md`: ADRs -- why per-Data-ID keys, why counter-based rather than timestamp
  freshness, why the core is bus-agnostic.
- `docs/deploying-on-hardware.md`: what changes with a real CAN interface and a real HSM.
**Accept:** someone unfamiliar with SecOC can explain, after reading the README, why a MAC alone
does not stop a replay.

## Phase 9 (optional) - Extras, in value order
1. A DBC file and `cantools` decode so signals render with real names and units.
2. `--profile full-cmac` on CAN FD with a latency comparison against truncated profiles.
3. An `asciinema` recording of `baseline` then `replay` back to back -- this is the single most
   shareable artifact the project can produce.
