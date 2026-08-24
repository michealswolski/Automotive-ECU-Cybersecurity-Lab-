# `03` ECU Key Lifecycle Manager

![status](https://img.shields.io/badge/status-Specified-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![language](https://img.shields.io/badge/lang-Python-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![phases](https://img.shields.io/badge/phases-10_%2B_1_optional-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![build order](https://img.shields.io/badge/build_order-third-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)

A CLI (plus an optional read-only dashboard) modelling the **complete cryptographic key lifecycle** for a simulated ECU fleet: generation in a backend HSM, HKDF derivation with per-generation domain separation, a challenge-response provisioning ceremony with AAD binding to a single ECU, protected on-device storage that exposes `use()` and never `get_key()`, fleet rotation with an overlap window and offline vehicles, signed revocation lists with rollback protection, cryptoperiod enforcement on an injectable clock, and a hash-chained tamper-evident audit log over every transition.

> **This is a simulation** of a key management system, not a KMS. The simulated HSM provides no hardware guarantees. See [honest claims](../../docs/honest-claims.md).

---

## The thesis

> Most engineers can name the algorithms. Far fewer can describe what happens to a key between the day it is generated and the day the vehicle is scrapped.

This project is about the second thing. It is the answer to "so you used AES-256 — then what?"

## The demo that lands

Tamper with one byte of the audit log, live, and have the tool name the exact sequence number that broke the chain. `ekl audit tamper` exists precisely so the detection can be demonstrated rather than described.

The other scenario worth showing is **partial rotation**: a fleet where a fifth of the vehicles are asleep, mid-rotation, with both key generations valid. A design where the new key becomes valid at the instant the old one dies cannot survive a real fleet, and showing the overlap window is showing that you know why.

---

## Files

| File | Purpose |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Standing constraints — read on every turn of the build |
| [`SPEC.md`](./SPEC.md) | Key hierarchy, state machine, ceremony, storage boundary, scenarios |
| [`BUILD_PLAN.md`](./BUILD_PLAN.md) | Eleven phases with per-phase acceptance criteria |
| [`ACCEPTANCE.md`](./ACCEPTANCE.md) | The definition of done |
| [`prompts/kickoff.md`](./prompts/kickoff.md) | The prompt that starts the build, plus follow-ups |
| [`docs/interview-talking-points.md`](./docs/interview-talking-points.md) | How to talk about it once it exists |

## Building it

```bash
cd projects/ecu-key-lifecycle
claude                 # then paste prompts/kickoff.md
```

> **Phase 1 is a gate.** It is the pure state machine, with no database anywhere near it. Get the transition matrix right and exhaustively tested — including a test for every illegal edge — before anything touches persistence. The state machine *is* the product; a lifecycle modelled as a status string is a CRUD app with extra steps.

Full workflow: [building a project](../../docs/building-a-project.md).

## Build the bridge

The optional final phase includes an export bridge that provisions the MAC keys [`02` CAN Bus SecOC Demo](../can-secoc-demo) consumes. It is about an hour of work and it is the highest-leverage hour in the portfolio: it turns two demos into one system.

Two repositories that plug into each other demonstrate systems thinking in a way that two unrelated repositories never will. See [portfolio map](../../docs/portfolio-map.md).

## What it covers

Key management · key derivation (HKDF) · provisioning ceremony · key rotation · revocation · cryptoperiods · tamper-evident audit logs · PKI.

Full matrix: [capability coverage](../../docs/skills-coverage.md).

## Claim discipline

Say: *"I designed and implemented a simulated ECU key lifecycle manager covering generation, derivation, a challenge-response provisioning ceremony, protected storage, fleet rotation with an overlap window, signed revocation lists with rollback protection, cryptoperiod enforcement, and a hash-chained tamper-evident audit log. I based the lifecycle model and cryptoperiod defaults on published NIST key management guidance."*

Do not say that you have production KMS or PKCS#11/HSM integration experience, that you have managed keys for a real vehicle fleet, or that this is a KMS. It is a simulation of one.
