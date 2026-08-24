# `05` In-Vehicle Network Security Lab

![status](https://img.shields.io/badge/status-Specified-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![language](https://img.shields.io/badge/lang-Python-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![phases](https://img.shields.io/badge/phases-10_%2B_1_optional-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![build order](https://img.shields.io/badge/build_order-fifth-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)

A simulated vehicle network spanning three protocols — **LIN sub-bus, CAN-FD backbone, and Automotive Ethernet** carrying SOME/IP-SD and DoIP — joined by a gateway ECU with a zone-based firewall, routing table, rate limiting, SecOC enforcement point, diagnostic firewall, and a threshold anomaly detector.

Ten attacks, each run against a permissive gateway and a hardened one, side by side.

> **This is a simulation.** No physical layer, no real bus arbitration, no real timing, no actual 100BASE-T1 behaviour. LIN genuinely has no native security and this repository says so rather than inventing one. See [honest claims](../../docs/honest-claims.md).

---

## The demo that lands

**The pivot.** Compromise a door module on the LIN bus and try to reach the brake ECU.

Without zone policy: all the way. With it: you stop at the gateway.

That is how vehicle networks actually get attacked — an attacker reaches a low-assurance segment and pivots through routing into a high-assurance one — and the gateway is where it gets stopped.

## The gateway is the point

Not any single protocol. Every scenario ends at the same question: *should this frame have crossed this boundary?* So the gateway implements a real routing table and a real firewall policy, not a switch statement.

**Zones, not node lists.** A policy that says "nothing from the comfort zone reaches the chassis zone without authentication" survives a supplier swapping a door module. A policy that names the module does not.

**Every attack has a paired defence**, and the demo shows both. An attack demo alone is a party trick; attack-then-mitigate is engineering.

---

## Files

| File | Purpose |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Standing constraints — read on every turn of the build |
| [`SPEC.md`](./SPEC.md) | Architecture, zones, all four protocol layers, the gateway, ten scenarios |
| [`BUILD_PLAN.md`](./BUILD_PLAN.md) | Eleven phases with per-phase acceptance criteria |
| [`ACCEPTANCE.md`](./ACCEPTANCE.md) | The definition of done |
| [`prompts/kickoff.md`](./prompts/kickoff.md) | The prompt that starts the build, plus follow-ups |
| [`docs/interview-talking-points.md`](./docs/interview-talking-points.md) | How to talk about it once it exists |

## Building it

```bash
cd projects/ivn-security-lab
claude                 # then paste prompts/kickoff.md
```

> **Verify the protocol details before writing any code.** LIN's PID parity and both checksum variants, the CAN-FD DLC-to-length mapping above 8 bytes (it is *not* linear — 9–15 map to 12/16/20/24/32/48/64), the SOME/IP header layout, and the DoIP routing activation handshake. The kickoff prompt makes the build record its sources in `docs/verification-sources.md`. Keep that. Getting the DLC table wrong is exactly the kind of error an automotive interviewer spots instantly.

Full workflow: [building a project](../../docs/building-a-project.md).

## Build this after SecOC

The gateway's SecOC enforcement point reuses [`02` CAN Bus SecOC Demo](../can-secoc-demo), and building CAN-FD twice is a wasted week. See [build order](../../docs/build-order.md) and [portfolio map](../../docs/portfolio-map.md).

The optional final phase runs the CAN segment over a real USB-CAN adapter. That becomes a separate, true, and much stronger claim — see [the bench path](../../docs/bench-path.md).

## What it covers

LIN · CAN-FD · Automotive Ethernet · SOME/IP + SD · DoIP · UDS · ISO-TP · zone-based segmentation · anomaly detection.

Full matrix: [capability coverage](../../docs/skills-coverage.md).

## Claim discipline

Say: *"I built a simulated multi-protocol in-vehicle network — LIN, CAN-FD, and Automotive Ethernet with SOME/IP and DoIP — with a zone-based gateway firewall, and validated it with ten attack scenarios run against both permissive and hardened configurations."*

Do not say that you have production experience with these protocols on real vehicle hardware, or name commercial tooling you have not driven.

On the anomaly detector, have the real false-positive number and say what it means: cycle-time detection catches injection that does not match a periodic pattern and misses an attacker patient enough to match it. It is a layer, not a solution.
