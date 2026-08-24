# `01` Secure Boot Chain Simulator

![status](https://img.shields.io/badge/status-Specified-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![language](https://img.shields.io/badge/lang-Python-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![phases](https://img.shields.io/badge/phases-8_%2B_2_optional-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![build order](https://img.shields.io/badge/build_order-first-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)

A simulated multi-stage automotive secure boot chain — **BootROM → SBL → Application** — where every stage cryptographically verifies the next before transferring control.

Hardware root of trust in OTP fuses, a simulated HSM that never releases private keys, monotonic anti-rollback counters, measured boot with a PCR bank and attestation quote, key revocation, and a hash-chained tamper-evident audit log.

> **This is a simulation.** It models hardware behaviour; it does not touch hardware. The HSM is a Python object and the fuses are a file. Nothing here is production-grade, certified, or independently reviewed. See [honest claims](../../docs/honest-claims.md).

---

## The demo that lands

An image carrying a **valid signature from the legitimate signing key** that the chain still refuses to boot, because its security version number sits behind the monotonic counter.

That is rollback protection, and it is the thing most people cannot demonstrate. Anyone can show a bad signature being rejected. Showing a *good* signature being rejected — and explaining why that is correct — is a different conversation.

The whole demo runs end to end in under twenty seconds, with one command and no setup beyond installing dependencies.

## Negative paths are the features

Corrupted image, downgrade attempt, unknown key ID, revoked key ID, truncated image, SVN rollback. Each has a dedicated demo scenario *and* a dedicated test, and each REJECT prints its reason code, the expected versus actual value, and the rule it enforces.

Sixteen reason codes, all individually reachable and individually tested.

---

## Files

| File | Purpose |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Standing constraints — read on every turn of the build |
| [`SPEC.md`](./SPEC.md) | The source of truth: byte layouts, verification order, reason codes |
| [`BUILD_PLAN.md`](./BUILD_PLAN.md) | Nine phases, each with its own acceptance criteria |
| [`ACCEPTANCE.md`](./ACCEPTANCE.md) | The definition of done |
| [`prompts/kickoff.md`](./prompts/kickoff.md) | The prompt that starts the build, plus follow-ups |
| [`docs/interview-talking-points.md`](./docs/interview-talking-points.md) | How to talk about it once it exists |

## Building it

```bash
cd projects/secure-boot-chain-simulator
claude                 # then paste prompts/kickoff.md
```

Build one phase at a time and run the demo yourself after each one. If you cannot explain a file, ask for an explanation of that file before moving on — an interviewer will ask about the code, not the spec.

Full workflow: [building a project](../../docs/building-a-project.md).

## Why this one is first

Highest credibility per hour of any project in the lab, and it depends on nothing else. Secure boot is the topic most likely to come up in an automotive product-security interview, the rollback demo is genuinely uncommon in portfolios, and the project is self-contained — no protocol simulation, no emulator, no cross-toolchain.

Reasoning for the whole sequence: [build order](../../docs/build-order.md).

## What it covers

Secure boot · chain of trust · HSM and root of trust · anti-rollback · measured boot and attestation · PKI · ECDSA/Ed25519 · tamper-evident audit logs.

Full matrix: [capability coverage](../../docs/skills-coverage.md).

## Standards

Implements: **SAE J3101 · NIST SP 800-193 · NIST SP 800-208 · NSA CNSA 2.0 · FIPS 204 · UN ECE R156 · ISO 24089**.

Editions are pinned and dated in the [standards register](../../docs/standards-register.md). Several anchors have moved since this specification was written — read [`CORRECTIONS.md`](./CORRECTIONS.md) before writing code.

## Claim discipline

Say: *"I designed and implemented a simulated secure boot chain in Python: a signed image container format, staged signature verification, monotonic anti-rollback counters, key revocation, measured boot with a PCR model, and a hash-chained audit log."*

Do not say that you shipped secure boot on a production ECU, that you have hands-on experience with a vendor HSM you have not used, or that the cryptography has been independently reviewed.

If asked whether it is real hardware, lead with the answer: it is a simulation, and here is precisely which parts map to hardware and which do not.
