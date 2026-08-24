# Honest claims

The policy that governs what this repository — and its author — says about this work.

Every project here is a simulation. That is not a weakness to be minimised; it is a fact to be stated first, precisely, and without being asked. This document is the rule that decides how each claim gets worded.

---

## The rule

> **Describe the artefact, not the aspiration.**

"I implemented the AUTOSAR SecOC profiles over a virtual CAN bus in Python" is a description of an artefact. Someone can open it and check. "I have AUTOSAR SecOC experience" is an aspiration wearing the artefact's clothes — technically adjacent to true, and it will not survive two follow-up questions from anyone who has shipped a production stack.

The difference costs nothing to get right and everything to get wrong.

---

## Say this / not that

| Say | Do not say |
|---|---|
| "I implemented a simulated secure boot chain: signed image container, staged verification, monotonic anti-rollback, key revocation, measured boot with a PCR model, hash-chained audit log." | "I shipped secure boot on a production ECU." |
| "I implemented the AUTOSAR SecOC profiles over virtual CAN and verified my CMAC against the RFC 4493 test vectors." | "This is AUTOSAR-conformant." / "I worked on an OEM SecOC deployment." |
| "I designed a simulated ECU key lifecycle manager covering generation, provisioning, rotation with overlap, revocation and cryptoperiod enforcement." | "I have production KMS or PKCS#11 HSM integration experience." |
| "I implemented the publicly described ISO/SAE 21434 TARA workflow as a tool and produced a worked analysis for a telematics gateway." | "I have performed TARA in a professional CSMS context." / "The analysis is conformant." |
| "I built a simulated multi-protocol in-vehicle network and validated it with ten attack scenarios run permissive versus hardened." | "I have production experience with these protocols on vehicle hardware." |
| "I ran CERT-C-oriented static analysis with open tooling." | "I validated MISRA compliance." |
| "I debugged the firmware over the emulator's gdbstub." | "I debugged over JTAG." |

The right-hand column is not a list of lies anyone set out to tell. Each one is what the left-hand column decays into when someone is tired, or nervous, or writing a résumé bullet at 1am. Writing them down is how you notice yourself reaching for one.

---

## The three phrases that carry the most weight

**"That's a simulation — here's precisely what maps to hardware and what doesn't."** Say it before you are asked. It converts the single biggest weakness of the portfolio into evidence that you understand the boundary, which is a more senior thing to demonstrate than the project itself.

**"I don't know, but here's how I'd find out."** The alternative is inventing a clause number, and automotive interviewers ask about standards specifically because the invented answers are easy to spot.

**"Here's what the tooling missed."** A tool-comparison matrix with an empty row is not an embarrassment. It is the only part of the firmware validation project that cannot be produced by running a tutorial.

---

## Standards and citations

ISO/SAE 21434 is a paid standard. So is MISRA C. So, in practice, is a Vector CANoe licence.

- **Never reproduce the text or tables of a paid standard.** The TARA workbench reproduces none of ISO/SAE 21434's content; its scoring thresholds are a documented project convention, and its own `docs/method.md` says so.
- **Never assert a clause number that has not been verified.** Cite by document name when the clause cannot be confirmed. A wrong clause number is worse than no clause number, because it signals that the rest of the citations are decorative too.
- **Never claim compliance with a standard whose conformance test you have not run.** "CERT-C-oriented static analysis using open tooling" is true and defensible. "MISRA compliant" requires a commercial checker and a compliance matrix.

---

## The bench line

Four capabilities appear on almost every automotive security résumé and cannot be earned by writing software: driving a logic analyzer, debugging over JTAG, reading a bus on an oscilloscope, and operating CANoe. A fifth — running traffic over a real CAN transceiver — is close behind.

This repository claims none of them. `lab.toml` marks each one `bench_only = true`, and `labctl validate` **fails the build** if any project's capability list claims one. The policy is executable rather than aspirational, which is the only version of a policy that survives contact with a deadline.

What it costs to close each gap honestly is in [bench-path.md](./bench-path.md). Roughly $100 and a Saturday converts most of them from an overstated line into a defensible one.

---

## Where this lands per project

Every project carries its own version of this section:

| Project | Its specific limit |
|---|---|
| [`01` Secure Boot Chain Simulator](../projects/secure-boot-chain-simulator) | Models hardware behaviour; does not touch hardware. The HSM is an object, the fuses are a file. |
| [`02` CAN Bus SecOC Demo](../projects/can-secoc-demo) | Implements the publicly specified profiles. Not AUTOSAR-conformant, not certified, not a production stack. |
| [`03` ECU Key Lifecycle Manager](../projects/ecu-key-lifecycle) | A simulation of a key management system, not a KMS. The simulated HSM provides no hardware guarantees. |
| [`04` TARA Workbench](../projects/tara-workbench) | Reproduces none of ISO/SAE 21434's text. Scoring thresholds are documented conventions. One person's analysis is one person's opinion, structured. |
| [`05` IVN Security Lab](../projects/ivn-security-lab) | No physical layer, no real arbitration, no real timing. LIN genuinely has no native security and the repo says so rather than inventing one. |
| [`06` Firmware Validation Pipeline](../projects/ecu-firmware-validation) | Emulated target, not silicon. Vulnerabilities planted on purpose and labelled as such. Emulator gdbstub debugging is not JTAG. |

---

## Why bother

Because the alternative gets found out, and because the discipline is itself the qualification.

Automotive product security is a field where the consequence of an overstated claim is not embarrassment — it is a safety case built on something that was never verified. An engineer who is rigorous about the boundary between "modelled" and "measured" in their own portfolio is demonstrating exactly the habit the job requires. That is worth more than any single project in this repository.
