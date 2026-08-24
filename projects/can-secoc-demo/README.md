# `02` CAN Bus SecOC Demo

![status](https://img.shields.io/badge/status-Specified-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![language](https://img.shields.io/badge/lang-Python-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![phases](https://img.shields.io/badge/phases-9_%2B_1_optional-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![build order](https://img.shields.io/badge/build_order-second-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)

A working AUTOSAR **Secure Onboard Communication** implementation over a virtual CAN bus: AES-128 CMAC authenticators, all three standard profiles with truncated MAC and truncated freshness value, receiver-side freshness reconstruction with an acceptance window, resynchronisation, and an attacker node that captures and replays real frames.

> **This is a simulation.** It implements the publicly specified profiles. It is not AUTOSAR-conformant, not certified, and not a production stack. See [honest claims](../../docs/honest-claims.md).

---

## The demo that lands

The **same replay attack**, run twice.

Against an unprotected bus, the receiver actuates on a stale brake command. Against the SecOC-protected bus, the identical bytes are rejected — with the freshness window that was searched printed on screen.

Profile 2 (no freshness value) is included specifically so you can show that **a valid MAC alone does not stop it**. That is the whole argument for freshness in ninety seconds: a MAC proves *who*, a freshness value proves *when*.

The replay is a real replay. Captured frames are re-sent byte-identical, not simulated with a flag.

## Runs anywhere

macOS and Windows with no hardware and no kernel modules, via `python-can`'s in-process virtual interface. Linux `vcan0` too, and — with a USB-CAN adapter — a real bus. Interface selection is one config flag; `vcan0` is never a hard requirement for the demo.

---

## Files

| File | Purpose |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Standing constraints — read on every turn of the build |
| [`SPEC.md`](./SPEC.md) | MAC input construction, profiles, freshness model, frame layouts, scenarios |
| [`BUILD_PLAN.md`](./BUILD_PLAN.md) | Ten phases with per-phase acceptance criteria |
| [`ACCEPTANCE.md`](./ACCEPTANCE.md) | The definition of done |
| [`prompts/kickoff.md`](./prompts/kickoff.md) | The prompt that starts the build, plus follow-ups |
| [`docs/interview-talking-points.md`](./docs/interview-talking-points.md) | How to talk about it once it exists |

## Building it

```bash
cd projects/can-secoc-demo
claude                 # then paste prompts/kickoff.md
```

> **Phase 1 is a gate, not a checkpoint.** It is the RFC 4493 known-answer tests for AES-CMAC. All four vectors pass or nothing proceeds — if the CMAC is wrong, every result downstream in this project is meaningless.

Full workflow: [building a project](../../docs/building-a-project.md).

## Where it plugs in

This project is the hub of the portfolio's two most valuable connections:

- **It consumes keys from [`03` ECU Key Lifecycle Manager](../ecu-key-lifecycle)** — the per-Data-ID MAC keys come from a real provisioning ceremony rather than a constant at the top of a file.
- **It provides the authenticator to [`05` IVN Security Lab](../ivn-security-lab)** — the gateway's SecOC enforcement point reuses this code rather than reimplementing it badly.

That second connection is why the SecOC core (`authenticator.py`, `freshness.py`) is specified to have **zero dependency on `python-can`**. It operates on bytes; the bus layer is a thin adapter. That boundary is the design decision an interviewer will respect.

See [portfolio map](../../docs/portfolio-map.md).

## What it covers

CAN bus · AUTOSAR SecOC · AES · CMAC/HMAC · replay protection · freshness management.

Full matrix: [capability coverage](../../docs/skills-coverage.md).

## Claim discipline

Say: *"I implemented the AUTOSAR SecOC profiles over virtual CAN in Python: AES-128 CMAC authenticator, truncated MAC and freshness value, receiver-side freshness reconstruction with an acceptance window, freshness resynchronisation, and a replay/forgery attacker for validation. I verified the CMAC against the RFC 4493 test vectors."*

Do not say that you have production AUTOSAR development experience, that this is AUTOSAR-conformant or certified, or that you have worked on a real OEM SecOC deployment.
