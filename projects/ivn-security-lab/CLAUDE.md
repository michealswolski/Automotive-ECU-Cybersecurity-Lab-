# CLAUDE.md - In-Vehicle Network Security Lab (LIN / CAN-FD / Automotive Ethernet)

You are building this project from scratch. Read `SPEC.md` and `BUILD_PLAN.md` first.

## What this is

A simulated multi-protocol vehicle network -- LIN sub-bus, CAN-FD backbone, and an Automotive
Ethernet segment carrying SOME/IP-SD and DoIP -- with a **central gateway** routing between them, an
attacker node on each segment, and a defense layer. The point is not any single protocol; the point
is the **gateway**, because that is where real vehicle architectures actually get compromised: an
attacker reaches a low-assurance segment and pivots through routing into a high-assurance one.

## Non-negotiables

1. **All three protocols run in one process with no hardware.** LIN and CAN-FD are simulated
   transports written for this project; Ethernet uses real loopback sockets. A reviewer must be able
   to `make demo` on a laptop.
2. **The gateway is the centerpiece.** Every scenario ends at the question "should this frame have
   crossed this boundary?" Implement a real routing table and a real firewall policy, not a switch
   statement.
3. **Protocol behavior must be correct where it matters for security.** LIN's PID parity and its
   classic/enhanced checksum, CAN-FD's DLC-to-length mapping and BRS, SOME/IP's message ID / request
   ID / message type / return code fields, DoIP's routing activation handshake. These are the details
   an interviewer will poke at. Get them right and cite where you verified each.
4. **Every attack has a paired defense**, and the demo shows both. An attack demo alone is a party
   trick; attack-then-mitigate is engineering.
5. **Do not hand-roll cryptography.** Reuse `cryptography`, and where SecOC applies, reuse the
   approach from the SecOC project rather than reimplementing it badly.

## Verify before coding

Web-search rather than recall:
- Scapy's automotive layers -- it ships SOME/IP and DoIP support; confirm the current module paths
  and class names before using them. `python -c "import scapy; print(scapy.__version__)"`.
- The SOME/IP-SD entry/option format and the DoIP routing activation sequence and payload types.
- The LIN frame structure (break, sync, PID with two parity bits, data, checksum) and the difference
  between classic and enhanced checksum.
- The CAN-FD DLC encoding above 8 bytes (it is not linear -- 9..15 map to 12/16/20/24/32/48/64).

Getting the DLC table or the LIN parity wrong is exactly the kind of thing that turns a good demo
into an embarrassing one. Verify, then write a unit test with published values.

## Engineering standards

Python 3.12+, `mypy --strict`, `ruff`, `pytest` ≥85%. Each protocol lives in its own module with a
common `Frame` abstraction at the gateway boundary. `hypothesis` for the bit-level encoders.
