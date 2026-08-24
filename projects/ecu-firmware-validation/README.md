# `06` ECU Firmware Security Validation Pipeline

![status](https://img.shields.io/badge/status-Specified-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![language](https://img.shields.io/badge/lang-C_%2B_Python-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![phases](https://img.shields.io/badge/phases-10_%2B_1_optional-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![build order](https://img.shields.io/badge/build_order-last-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)

Real embedded C: a **FreeRTOS application on an emulated ARM Cortex-M** running a UDS diagnostic server behind an ISO-TP reassembler, with eight deliberately planted and documented vulnerabilities.

Around it, a full validation pipeline — cppcheck, clang-tidy, flawfinder, compiler warnings, ASan/UBSan/MSan, libFuzzer with a protocol dictionary, syft SBOM, CVE scanning, and a test suite where every test traces to a security requirement.

> **This is an emulated target, not silicon.** No peripheral timing, no transceiver, no electrical layer, no real flash wear. The software bugs are real bugs and the tooling findings are real findings; the hardware is not. The vulnerabilities are planted on purpose and labelled as such — **do not reuse this firmware for anything.** See [honest claims](../../docs/honest-claims.md) and [the security policy](../../SECURITY.md).

---

## The demo that lands

The **tool-comparison matrix**: every planted bug against every tool, found or missed, with time-to-first-crash for the fuzzer.

One vulnerability is chosen specifically because **no automated tool catches it** — a TOCTOU on a security-access flag across two tasks. That row is the most valuable line in the repository, because it is the one that cannot be produced by running a tutorial.

The story: *here is embedded C, here are the classes of bug that get shipped in it, here is the tooling that catches each class, and here is what each tool missed.* Anyone can run cppcheck. Knowing which bug clang-tidy caught, which one only ASan caught at runtime, and which one only the fuzzer found after 40,000 executions is what an interviewer is actually probing for.

## Same source, both targets

The parsers under test compile **both** for the emulated target and for the host. The code the fuzzer exercises is the code the firmware runs. If the fuzzer tested a different implementation than the firmware runs, the whole project would be theatre — so that constraint is a non-negotiable in the specification, not a nice-to-have.

## Every test traces to a requirement

Test IDs map to security requirement IDs from [`04` TARA Workbench](../tara-workbench). `make trace` reports zero unverified requirements and zero orphan tests.

That is what "documented test cases" means to an automotive employer, and it is the part most portfolios skip entirely.

---

## Files

| File | Purpose |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Standing constraints — read on every turn of the build |
| [`SPEC.md`](./SPEC.md) | Firmware design, the eight vulnerabilities, the pipeline, traceability format |
| [`BUILD_PLAN.md`](./BUILD_PLAN.md) | Eleven phases; phase 0 is the toolchain and it is a real gate |
| [`ACCEPTANCE.md`](./ACCEPTANCE.md) | The definition of done |
| [`prompts/kickoff.md`](./prompts/kickoff.md) | The prompt that starts the build, plus follow-ups |
| [`docs/interview-talking-points.md`](./docs/interview-talking-points.md) | How to talk about it once it exists |

## Building it

```bash
cd projects/ecu-firmware-validation
claude                 # then paste prompts/kickoff.md
```

> **Set expectations on effort.** This is the most expensive project in the lab by a wide margin. Cross-toolchain plus emulator plus FreeRTOS plus a fuzzing harness is a real weekend before you write a line of security code, and **phase 0 can genuinely fight you**. A hello-world bare-metal binary must build and print over semihosting in the emulator before anything else starts.

> **Do not plant a vulnerability you cannot explain.** For each one you must be able to say out loud how it is reached, what an attacker gains, and why a real developer would plausibly have written it.

Full workflow: [building a project](../../docs/building-a-project.md).

## Why it is last

The payoff is that it is the only project putting real compiled C and a real RTOS on the table with something to show. The cost is a fight with a toolchain before any of the interesting work starts. Do it when the other five are shipping. See [build order](../../docs/build-order.md).

## What it covers

Embedded C · FreeRTOS · static analysis · sanitizers · coverage-guided fuzzing · SBOM generation · CVE scanning · UDS · ISO-TP · documented test cases.

Four of these are rows the other five projects leave completely open. Full matrix: [capability coverage](../../docs/skills-coverage.md).

## Standards

Implements: **ISO/SAE 21434 · ISO 14229-1 · ISO 15765-2 · MISRA C:2012 · SEI CERT C · CycloneDX · SPDX · EU Cyber Resilience Act**.

Editions are pinned and dated in the [standards register](../../docs/standards-register.md). Several anchors have moved since this specification was written — read [`CORRECTIONS.md`](./CORRECTIONS.md) before writing code.

## Claim discipline

Say: *"I wrote FreeRTOS-based ECU firmware in C for an emulated Cortex-M target with a UDS/ISO-TP diagnostic stack, planted and documented eight vulnerability classes, and built a validation pipeline using static analysis, sanitizers, coverage-guided fuzzing, and SBOM/CVE scanning, with tests traced to security requirements."*

Do not say that you have production embedded firmware shipping experience, that you validated MISRA compliance, or that you did hardware bring-up.

**MISRA specifically:** MISRA is a paid standard and full rule checking needs a commercial tool. What this runs is CERT-C-oriented static analysis with open tooling. Being precise here is a signal in itself; plenty of people claim MISRA when they have run cppcheck.

**JTAG specifically:** if asked whether you have debugged over JTAG, the honest answer is what you actually did. Emulator gdbstub debugging is real skill, and naming it accurately costs you nothing while claiming JTAG you have not done costs you everything. Porting this firmware to a real Cortex-M board is how that claim becomes true — see [the bench path](../../docs/bench-path.md).
