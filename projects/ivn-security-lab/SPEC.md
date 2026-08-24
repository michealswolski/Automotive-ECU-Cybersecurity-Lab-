# SPEC - In-Vehicle Network Security Lab

Version 1.0. Source of truth.

---

## 1. The modeled architecture

```
   ┌─────────────┐         LIN (19.2 kbit/s, master/slave, single wire)
   │ Door Module │───┐
   └─────────────┘   │     ┌──────────────────────────────────────┐
   ┌─────────────┐   ├────▶│                                      │
   │ Seat Module │───┘     │            GATEWAY ECU               │
   └─────────────┘         │  routing table + firewall policy     │
                           │  + rate limiting + SecOC enforcement │
   ┌─────────────┐         │                                      │
   │  Brake ECU  │───┐     │                                      │
   └─────────────┘   ├────▶│                                      │
   ┌─────────────┐   │     │                                      │
   │Powertrain   │───┘     └──────┬───────────────────────────────┘
   └─────────────┘   CAN-FD       │  Automotive Ethernet (100BASE-T1 modeled)
                    (500k/2M)     │  SOME/IP-SD + DoIP
                                  ├──────▶ ┌──────────────────┐
                                  │        │ Domain Controller│  (SOME/IP services)
                                  │        └──────────────────┘
                                  └──────▶ ┌──────────────────┐
                                           │ Telematics Unit  │  (external interface)
                                           └──────────────────┘
```

Trust zones, declared explicitly in `config/zones.yaml`:
- **Zone 0 (untrusted):** telematics external interfaces, OBD-II
- **Zone 1 (comfort):** LIN sub-bus, body CAN
- **Zone 2 (critical):** powertrain/chassis CAN-FD
- **Zone 3 (management):** diagnostic and update paths

The firewall policy is expressed in terms of zones, not node names. This is the design decision worth
defending in an interview: policies written against zones survive an architecture change, policies
written against node names do not.

---

## 2. Protocol layers

### 2.1 LIN (`src/ivn/lin/`)
- Master/slave scheduling with a schedule table; frame slots at fixed offsets.
- Frame: break, sync (0x55), **protected identifier** (6 ID bits + 2 parity bits — implement the
  parity computation and unit-test it against published examples), 1..8 data bytes, checksum.
- Both **classic** (data only) and **enhanced** (data + PID) checksums, selectable per frame.
- Diagnostic frames (IDs 0x3C/0x3D) so the LIN transport layer is present.
- **Security reality to model honestly:** LIN has essentially no built-in security. Any node can
  respond to any header. The defense is not on the LIN bus — it is at the gateway. Say this in the
  README rather than inventing a LIN security feature.

### 2.2 CAN-FD (`src/ivn/can/`)
- Reuse `python-can` with the `virtual` interface for transport.
- Correct DLC-to-length mapping above 8 bytes and a bit rate switch flag.
- Optional SecOC protection per Data ID, wired to the SecOC project's approach (import it if the
  sibling repo is available; otherwise implement the minimum: AES-CMAC + freshness counter).
- ISO-TP (ISO 15765-2) segmentation for multi-frame diagnostic payloads: single frame, first frame,
  consecutive frame, flow control. This is needed for UDS and is a genuinely useful thing to have
  built once.

### 2.3 Automotive Ethernet (`src/ivn/eth/`)
- **SOME/IP**: header with service ID, method ID, client ID, session ID, protocol/interface version,
  message type, return code, plus payload serialization. Request/response and publish/subscribe.
- **SOME/IP-SD**: OfferService, FindService, SubscribeEventgroup, and their acknowledgements, over
  UDP multicast.
- **DoIP (ISO 13400)**: vehicle identification request/response, routing activation handshake,
  diagnostic message with positive/negative acknowledgement, and the alive check. DoIP tunnels UDS to
  ECUs on other segments through the gateway -- this is the bridge that makes the whole lab hang
  together.
- Use Scapy's automotive layers where they exist rather than reimplementing dissectors; verify the
  current API first.
- VLAN separation (802.1Q) between the diagnostic and service VLANs, so VLAN hopping is a real
  scenario rather than a hypothetical.

### 2.4 UDS (`src/ivn/uds/`)
A minimal but honest UDS server on the target ECUs, because it is the payload for the interesting
attacks: DiagnosticSessionControl (0x10), SecurityAccess (0x27) with a deliberately weak seed/key
algorithm, RoutineControl (0x31), RequestDownload (0x34)/TransferData (0x36)/RequestTransferExit
(0x37), ECUReset (0x11), and ReadDataByIdentifier (0x22).

The weak SecurityAccess is intentional and must be **labeled as intentionally weak in the code and
the README** — it is the vulnerability the brute-force scenario exploits, and a reviewer who thinks
you wrote it by accident will draw the wrong conclusion.

---

## 3. The gateway (`src/ivn/gateway/`)

This is the module that carries the project.

- **Routing table**: `(source_zone, protocol, identifier) -> (dest_zone, protocol, identifier)`,
  loaded from YAML, with signal translation where the payload layout differs across protocols.
- **Firewall policy**: allow/deny rules over zone pairs, message identifiers, and direction. Default
  deny. Every decision is logged with the rule that matched.
- **Rate limiting**: per-identifier token bucket. A flood on one segment must not starve another.
- **SecOC enforcement point**: the gateway can require authenticated frames for a zone transition and
  reject unauthenticated ones — a frame may be legal on Zone 1 and inadmissible into Zone 2.
- **Diagnostic firewall**: routing activation and security access state tracked per source; a
  DoIP-originated UDS request into Zone 2 requires an authenticated diagnostic session.
- **Anomaly detection** (keep it simple and honest): per-identifier cycle-time deviation, and
  identifiers appearing from a segment where they have never been observed. Report detection rate and
  false-positive rate on a captured baseline. Do not call it machine learning; it is a threshold
  detector and calling it what it is will earn you more credibility than a buzzword.

Every gateway decision emits a structured event: timestamp, source zone, destination zone, protocol,
identifier, verdict, matched rule, and reason.

---

## 4. Attack and defense scenarios

Each scenario runs the attack against an undefended gateway config, then against the hardened one.
Both outcomes are shown side by side. `ivn run --scenario <name>`.

| Scenario | Attack | Defense that stops it |
|---|---|---|
| `lin-spoof` | Rogue node answers a LIN header before the real slave | Gateway rejects the value on plausibility and cycle-time; the LIN bus itself cannot stop it and the README says so |
| `lin-to-can-pivot` | Comfort-zone compromise injects toward Zone 2 | Zone firewall default-deny on Zone 1 → Zone 2 |
| `can-fd-inject` | Forged brake message on the backbone | SecOC enforcement at the zone boundary |
| `can-flood` | Bus flood from a compromised node | Per-identifier rate limiting; show the rate limiter's effect on the victim segment |
| `someip-sd-hijack` | Attacker offers a service already offered by the legitimate server and steals subscribers | SD offer validation: source address binding and an offer allowlist |
| `someip-mitm` | Attacker de-associates a subscriber and reroutes events | Same, plus the honest note that link-layer security alone does not stop this |
| `doip-unauth-diag` | DoIP routing activation from an untrusted source, then UDS into Zone 2 | Routing activation authentication and the diagnostic firewall |
| `uds-seedkey-brute` | Brute-force the weak SecurityAccess | Attempt limiting with a delay timer, and the note that the real fix is a proper challenge-response |
| `vlan-hop` | Tagged frame crosses from the service VLAN into the diagnostic VLAN | Ingress tag filtering at the switch model |
| `flash-unauth` | RequestDownload/TransferData without authorization | Secure boot rejects the resulting image — links to the secure boot project |

The last row matters: it is the scenario that connects this repo to your secure boot repo. Build it.

---

## 5. CLI

```
ivn run --scenario <name> [--hardened|--undefended]  # default runs both and diffs them
ivn run --scenario all
ivn topology                       # render the architecture and zones (Mermaid + rich)
ivn gateway rules [--zone-pair 1,2]  # show the effective policy
ivn monitor [--segment lin|can|eth]  # live traffic view, protocol-decoded
ivn capture --out capture.jsonl      # record a baseline for the anomaly detector
ivn detect --baseline capture.jsonl --report   # detection rate and false positives
ivn report                           # markdown + charts for all scenarios
```

---

## 6. Repository layout

```
ivn-security-lab/
├── README.md  pyproject.toml  Makefile
├── config/  zones.yaml  routing.yaml  firewall.yaml  services.yaml
├── src/ivn/
│   ├── frame.py            # common frame abstraction at the gateway boundary
│   ├── lin/    bus.py  frame.py  schedule.py  nodes.py
│   ├── can/    bus.py  fd.py  isotp.py  secoc.py  nodes.py
│   ├── eth/    someip.py  someip_sd.py  doip.py  switch.py  nodes.py
│   ├── uds/    server.py  client.py  services.py
│   ├── gateway/ router.py  firewall.py  ratelimit.py  diagfw.py  anomaly.py
│   ├── attack/ lin.py  can.py  someip.py  doip.py  uds.py
│   ├── scenarios.py  cli.py  render.py
├── tests/
│   ├── test_lin_parity.py         # published PID parity values
│   ├── test_lin_checksum.py       # classic vs enhanced, published examples
│   ├── test_canfd_dlc.py          # the full DLC table
│   ├── test_someip_header.py      test_doip_handshake.py
│   ├── test_isotp.py              # multi-frame round-trip, flow control
│   ├── test_gateway_policy.py     # default deny, rule matching, zone transitions
│   └── test_scenarios.py          # every scenario's outcome asserted both ways
└── docs/  .github/workflows/ci.yml
```

---

## 7. Honesty requirements

- LIN has no meaningful native security. Do not invent one. The lesson of the LIN scenarios is that
  the defense lives at the gateway, and that is a better lesson anyway.
- The weak UDS SecurityAccess is deliberately weak and is labeled as such in code and README.
- This is a simulation. 100BASE-T1 timing, real bus arbitration, and physical-layer behavior are not
  modeled. State that plainly rather than letting a reviewer discover it.
- Where a defense is partial (SOME/IP MITM), say it is partial and say what the real mitigation is.
