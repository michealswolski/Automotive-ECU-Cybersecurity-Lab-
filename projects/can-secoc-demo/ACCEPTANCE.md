# ACCEPTANCE - the definition of done

## Hard gates
- [ ] `make check` green: ruff, `mypy --strict src/`, pytest ≥85% coverage on `src/secoc`.
- [ ] `make demo` runs the full scenario suite on macOS/Windows with the `virtual` interface,
      no root, no kernel modules, no hardware.
- [ ] On Linux, `scripts/setup_vcan.sh` + `--interface socketcan --channel vcan0` also works.
- [ ] Fresh clone to running demo in under five minutes.

## Correctness gates
- [ ] All four RFC 4493 AES-128 CMAC vectors pass and are printable via `secoc-demo kat`.
- [ ] Truncation is bit-exact: MAC takes the most-significant bits, FV the least-significant.
      Proven by property test, not by example.
- [ ] `DataToAuthenticator` is `DataID || payload || complete FV`, big-endian, verified by a
      committed byte-level fixture in the docs.
- [ ] The receiver never transmits or receives the complete freshness value on the wire.
- [ ] Replay invariant: any accepted frame, re-injected, is rejected. Property-tested.
- [ ] `baseline` scenario **accepts** the replay; `replay` scenario **rejects** it with `FV_STALE`;
      `no-fv` **accepts** it. All three asserted in CI.
- [ ] Desync scenario shows failure, then recovery via the authenticated sync message.
- [ ] Brute-force scenario reports measured attempts alongside the analytic 2^-24 expectation.

## Quality gates
- [ ] `src/secoc/authenticator.py` and `freshness.py` do not import `can`.
- [ ] Every profile parameter is a named constant, not a literal at the call site.
- [ ] Demo keys are labeled as demo keys in the filename, the loader warning, and the README.
- [ ] README does not claim AUTOSAR conformance or certification.
- [ ] All cited standard/document identifiers were verified by search, not recalled.
