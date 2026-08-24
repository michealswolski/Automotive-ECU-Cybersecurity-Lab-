# CLAUDE.md - CAN Bus SecOC Demo

You are building this project from scratch. Read `SPEC.md` (source of truth) and `BUILD_PLAN.md`
(phase order) before writing code.

## What this is

A working AUTOSAR Secure Onboard Communication (SecOC) implementation over a virtual CAN bus, with a
side-by-side replay attack: the same attack **succeeds** against an unprotected bus and **fails**
against the SecOC-protected bus, with the rejection reason printed.

Audience: an automotive cybersecurity interviewer. The deliverable is a two-minute terminal demo
plus a repo that survives someone reading `secoc/authenticator.py` closely.

## Non-negotiables

1. **Cross-platform by default.** The demo must run on macOS and Windows using python-can's
   in-process `virtual` interface, and on Linux additionally over real SocketCAN `vcan0`. Interface
   selection is one config flag. Never make `vcan0` a hard requirement for the demo.
2. **Spec-faithful MAC input.** `DataToAuthenticator = SecOCDataID || authentic_payload ||
   complete_freshness_value`, big-endian throughout. Do not invent your own concatenation order.
3. **RFC 4493 known-answer tests for AES-CMAC before anything else.** If the KATs do not pass, no
   other result in this repo means anything. Phase 1 is the KATs.
4. **The receiver reconstructs the full freshness value** from its local counter plus the truncated
   bits on the wire. Do not transmit the full FV -- transmitting it would defeat the entire point of
   the truncation design and would be the first thing a reviewer notices.
5. **The replay attack must actually be replayed** -- captured frames re-sent byte-identical, not
   simulated with a flag.
6. **No hand-rolled cryptography.** AES-CMAC comes from `cryptography` (`hazmat.primitives.cmac`).

## Verify current facts before coding

```bash
python -c "import can; print(can.__version__)"
python -c "import cryptography; print(cryptography.__version__)"
```

`python-can` API notes that trip up stale training data:
- The constructor kwarg is `interface=`, not the older `bustype=`.
- `can.Bus(...)` supports the context-manager protocol; use `with` so `shutdown()` always runs.
- Two `VirtualBus` instances on the same channel exchange messages **only within one Python
  process**. If you need cross-process, use the `udp_multicast` interface -- check the current docs
  before choosing.

Web-search rather than guess for: current python-can release and API, the current AUTOSAR release
number for the SecOC specification, and any clause/requirement ID you plan to cite.

## Engineering standards

- Python 3.12+, `mypy --strict` clean, `ruff` lint + format, `pytest` with ≥85% coverage on `src/secoc`.
- Bit-level code (truncation, packing) gets property-based tests via `hypothesis`.
- The SecOC core (`authenticator.py`, `freshness.py`) has **zero dependency on python-can**. It
  operates on bytes. The bus layer is a thin adapter. This makes the core testable and reusable, and
  it is the design decision an interviewer will respect.
- Every magic number is a named constant traceable to a profile definition.

## Style of the output the user sees

`rich` live table: a candump-style scrolling frame view on the left, per-node counters and
accept/reject tallies on the right. Rejections print the reason and the FV window that was searched.
