# BUILD_PLAN - phase order

This is the largest of the kits. Build it after the SecOC project so you can reuse that work.

## Phase 0 - Scaffold
`pyproject.toml` (deps: `python-can`, `scapy`, `cryptography`, `typer`, `rich`, `pydantic`,
`pyyaml`, `matplotlib`; dev: `pytest`, `hypothesis`, `ruff`, `mypy`). `Makefile`. Common `frame.py`
abstraction. `config/zones.yaml`.
**Accept:** `make check` green; `ivn --help` prints; `ivn topology` renders the zone diagram.

## Phase 1 - LIN
Frame encoding, PID with parity, classic and enhanced checksums, master schedule table, slave nodes.
**Accept:** `test_lin_parity.py` and `test_lin_checksum.py` pass against published example values --
find them and cite the source in the test docstring. Two slaves respond on schedule.

## Phase 2 - CAN-FD + ISO-TP
python-can virtual transport, correct DLC mapping above 8 bytes, BRS flag, ISO-TP segmentation with
flow control.
**Accept:** the full DLC table is tested; a 200-byte ISO-TP payload round-trips with correct
first/consecutive frame sequencing and flow control.

## Phase 3 - Automotive Ethernet
SOME/IP header and serialization, SOME/IP-SD offer/find/subscribe over UDP multicast, DoIP vehicle
identification and routing activation, a switch model with 802.1Q VLAN separation.
**Accept:** a SOME/IP request/response and a publish/subscribe both work between two nodes; a DoIP
routing activation handshake completes; Wireshark can dissect a captured SOME/IP packet (verify this
-- it is a strong correctness signal and a good screenshot).

## Phase 4 - UDS
Server on the target ECUs with the services from SPEC §2.4, including the deliberately weak
SecurityAccess (labeled). Client for the attack scripts.
**Accept:** a full session flow works: session control, security access, request download, transfer
data, transfer exit.

## Phase 5 - The gateway
Routing table with signal translation, zone firewall with default deny, rate limiting, SecOC
enforcement point, diagnostic firewall, structured decision logging.
**Accept:** `test_gateway_policy.py` proves default-deny, correct rule precedence, and that a Zone 1
frame cannot reach Zone 2 without an explicit rule. Every decision is logged with the matched rule.

## Phase 6 - Attacks
All ten attacks from SPEC §4, each against the undefended configuration first.
**Accept:** every attack succeeds against the undefended gateway. If an attack does not work, the
attack is wrong -- fix it rather than weakening the model.

## Phase 7 - Defenses
Harden the configuration. Each attack now fails, or is explicitly documented as only partially
mitigated.
**Accept:** `ivn run --scenario all` shows undefended and hardened side by side; `test_scenarios.py`
asserts both outcomes for all ten.

## Phase 8 - Anomaly detection
Cycle-time deviation and unexpected-source detection. `ivn capture` for a baseline, `ivn detect` for
a report with detection rate and false-positive rate.
**Accept:** real measured numbers on a real baseline. Report the false positives honestly -- a
detector with a 30% false-positive rate that you can explain is worth more than a claimed 99%.

## Phase 9 - Documentation
- `README.md`: the architecture diagram, the zone model, the ten scenarios with captured output, the
  gateway policy explanation, and the simulation disclaimer.
- `docs/protocols.md`: what you implemented for each protocol and, explicitly, what you did not.
- `docs/gateway-design.md`: why the policy is zone-based, rule precedence, and the SecOC enforcement
  point.
- `docs/threat-model.md`: the pivot paths through the gateway, and which are mitigated.
- `docs/verification-sources.md`: for each protocol detail (LIN parity, DLC table, SOME/IP header,
  DoIP payload types), where you verified it. This is the file that proves you did not guess.
**Accept:** a reader understands why the gateway, not the bus, is where in-vehicle network security
is enforced.

## Phase 10 (optional)
1. Bridge to real hardware: run the CAN segment over a USB-CAN adapter on Linux `can0`. This is the
   cheapest possible path to a genuine hardware claim -- see `docs/bench-path.md` in the kit bundle.
2. Export captures in a format Wireshark can open, for screenshots.
3. Wire the `flash-unauth` scenario to actually hand its image to the secure boot project's verifier.
