# ACCEPTANCE - the definition of done

## Hard gates
- [ ] `make check` green: ruff, `mypy --strict src/`, pytest ≥85% on `src/ivn`.
- [ ] `make demo` runs all ten scenarios on a laptop with no hardware, no root, in under two minutes.
- [ ] Works on macOS and Linux. (Windows: LIN and Ethernet segments must work; note any CAN limitation.)

## Protocol correctness gates
- [ ] LIN PID parity tested against published example values, source cited in the test.
- [ ] Both LIN checksum variants tested against published examples.
- [ ] The complete CAN-FD DLC-to-length table is tested, including all values above 8.
- [ ] ISO-TP multi-frame round-trip with flow control, including a payload requiring block-size handling.
- [ ] A captured SOME/IP packet dissects correctly in Wireshark.
- [ ] DoIP routing activation follows the specified request/response sequence.
- [ ] `docs/verification-sources.md` cites where each of the above was verified.

## Gateway gates
- [ ] Default deny. A frame with no matching allow rule does not cross a zone boundary.
- [ ] Every routing and firewall decision is logged with the rule that matched.
- [ ] Rate limiting is per-identifier and a flood on one segment does not starve another.
- [ ] The SecOC enforcement point rejects an unauthenticated frame at a Zone 1 → Zone 2 transition
      that would be accepted within Zone 1.

## Scenario gates
- [ ] All ten attacks succeed against the undefended configuration.
- [ ] All ten are stopped, or explicitly documented as partially mitigated, when hardened.
- [ ] Both outcomes are asserted in CI.
- [ ] The anomaly detector reports measured detection and false-positive rates, not aspirational ones.

## Honesty gates
- [ ] README states this is a simulation and names what is not modeled (physical layer, bus
      arbitration, real timing).
- [ ] The weak UDS SecurityAccess is labeled as intentional in both code and README.
- [ ] LIN's lack of native security is stated rather than papered over.
- [ ] Partial mitigations are labeled partial.
