# Corrections — ECU Firmware Security Validation Pipeline

Apply these while building. Full reasoning and provenance: [`docs/spec-corrections.md`](../../docs/spec-corrections.md). Editions to cite: [`docs/standards-register.md`](../../docs/standards-register.md).

## Must fix

- [ ] **FreeRTOS LTS is at 202604.00-LTS** (released 29 April 2026), also distributed as a CMSIS Pack, with security and critical fixes until April 2028. Kernel v11.3.0 adds hardware ports, security hardening and expanded MPU support. Update from any older LTS.
- [ ] **libFuzzer is in maintenance-only mode** (since late 2022). Use **AFL++** as the primary fuzzer (active, multi-core, persistent mode, QEMU mode for binary-only targets); keep a libFuzzer `LLVMFuzzerTestOneInput` harness for portability; and **state the maintenance status explicitly.** That nuance signals current awareness — calling libFuzzer state-of-the-art signals the opposite.
- [ ] **MISRA:** current edition is **MISRA C:2023**, consolidating MISRA C:2012 AMD1–AMD4. cppcheck has a MISRA add-on (`--addon=misra`) covering a subset; **clang-tidy does not check MISRA at all.** Say *"cppcheck's MISRA add-on covers many rules; full MISRA compliance requires a commercial tool."* Never "proves MISRA compliance".
- [ ] **Static analysis:** cppcheck and clang-tidy are actively maintained — use the `bugprone-*`, `cert-*`, `clang-analyzer-*` and `misc-*` check sets. flawfinder is lightly maintained and pattern-matching only: keep it, do not overrate it.
- [ ] **SBOM is mandated by the EU Cyber Resilience Act**, not by UN R155 or ISO/SAE 21434. Reporting obligations from 11 September 2026; full application 11 December 2027. **Type-approved whole vehicles are exempt** under Art. 2(2)(c) — components, diagnostic and development tools and aftermarket devices are in scope. Do not imply the CRA covers whole vehicles.

## Choose deliberately

- [ ] **QEMU vs Renode.** Renode is the better fit for a security validation lab: it models multi-node systems, peripherals and sensor buses (CAN/UART/I2C/SPI) deterministically and scriptably, which suits fault injection and protocol testing. QEMU is lighter and excellent for single-MCU FreeRTOS demos and CI smoke tests. Suggested split: Renode for the integrated lab, QEMU for quick CI smoke tests. Name the working targets rather than leaving the choice abstract.

## Add — the cheapest credibility available

- [ ] **Tie the pipeline to ISO/SAE 21434 Clause 11** (verification and validation), where fuzz testing and penetration testing are expected and CAL scales the rigour. Cite **Clause 15** for the TARA that justifies *which* parsers to fuzz. Naming the clause costs nothing and changes how the project reads.
- [ ] **Map the eight planted vulnerabilities to specific CWEs** — e.g. CWE-787 out-of-bounds write, CWE-125 out-of-bounds read, CWE-190 integer overflow, CWE-476 NULL dereference, CWE-457 uninitialised, CWE-134 format string, CWE-20 improper input validation, CWE-416 use-after-free. There is no official "automotive CWE view"; CWE Top 25 + MISRA + CERT C is the pragmatic embedded-C set.
- [ ] **Lead with the CycloneDX SBOM and the CRA framing.** Neither R155 nor 21434 explicitly mandates an SBOM, but it is a de-facto requirement for their vulnerability management, and OEMs are flowing SBOM delivery down to Tier-1 suppliers contractually at scale. Explaining that regulatory and supply-chain nuance demonstrates business awareness, not just tooling.
- [ ] Note honestly that **firmware SBOMs are harder than application SBOMs** — vendored source and copied headers do not announce themselves to a scanner.

## Soften

- [ ] Do not claim the pipeline proves MISRA compliance.
- [ ] Do not call libFuzzer state-of-the-art.
- [ ] Do not imply the CRA applies to whole vehicles.

## Cite

ISO/SAE 21434 Clauses 11 and 15 · ISO 14229-1:2020 · ISO 15765-2:2024 · MISRA C:2023 (AMD1–4) · SEI CERT C · CycloneDX / SPDX · Regulation (EU) 2024/2847
