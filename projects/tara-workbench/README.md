# `04` ISO/SAE 21434 TARA Workbench

![status](https://img.shields.io/badge/status-Specified-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![language](https://img.shields.io/badge/lang-Python-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![phases](https://img.shields.io/badge/phases-9_%2B_1_optional-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![build order](https://img.shields.io/badge/build_order-fourth-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)

Two things, and the second one matters more.

A **tool** that runs the ISO/SAE 21434 Clause 15 TARA workflow as version-controlled structured data rather than a spreadsheet — item definition through risk treatment, with computed risk determination, a thirteen-rule linter, and bidirectional traceability from any requirement back to the asset it protects.

And a **completed, worked TARA** for an OTA-capable telematics gateway ECU, committed to the repository, passing its own linter in CI, with requirements that link to test cases in the other projects.

> **ISO/SAE 21434 is a paid standard.** This reproduces none of its text or tables. The scoring thresholds are documented project conventions, not the standard's. See [honest claims](../../docs/honest-claims.md).

---

## The demo that lands

`tara trace REQ-014` prints the full chain: requirement → cybersecurity goal → risk → threat scenario → damage scenario → asset. `tara orphans` finds anything unlinked.

Bidirectional traceability is what auditors actually check and what most portfolio TARAs completely lack. Being able to take any requirement and walk it back to the thing it protects — in one command, from version-controlled YAML that diffs cleanly — is the difference between an artefact and a schema.

## Why the worked example is the deliverable

The tool without the analysis is a data model. The analysis is what a hiring manager reads.

The example item is an **OTA-capable telematics/gateway ECU**, chosen because it touches every interesting boundary: cellular modem, Wi-Fi and Bluetooth, CAN and CAN-FD to the in-vehicle network, Ethernet to domain controllers, OBD-II adjacency, a firmware update path, a secure boot chain, and stored cryptographic keys. That gives real attack paths across every other project in this lab rather than a toy analysis of a door module.

## Risk is computed, never typed

Impact and attack feasibility go in; the risk value comes out of the matrix. There is no code path that sets a risk value directly. A TARA where an analyst hand-writes "risk = 4" is a spreadsheet with extra steps.

Attack feasibility uses the **attack-potential method** with all five factors scored explicitly — elapsed time, specialist expertise, knowledge of the item, window of opportunity, equipment — each carrying a written justification. An unjustified score is a defect the linter flags.

---

## Files

| File | Purpose |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Standing constraints — read on every turn of the build |
| [`SPEC.md`](./SPEC.md) | Domain model, the eight stages, linter rules, worked-example scope |
| [`BUILD_PLAN.md`](./BUILD_PLAN.md) | Ten phases; phase 7 is the analysis itself and is the real work |
| [`ACCEPTANCE.md`](./ACCEPTANCE.md) | The definition of done |
| [`prompts/kickoff.md`](./prompts/kickoff.md) | The prompt that starts the build, plus follow-ups |
| [`docs/interview-talking-points.md`](./docs/interview-talking-points.md) | How to talk about it once it exists |

## Building it

```bash
cd projects/tara-workbench
claude                 # then paste prompts/kickoff.md
```

> **Stop before phase 7.** The kickoff prompt makes the build check in before the worked analysis, and that check-in should be kept. Phase 7 is the analysis, and sixty threat scenarios generated unsupervised is filler you cannot defend at a table. **Fifteen scenarios you argued through beat sixty you didn't.**

Full workflow: [building a project](../../docs/building-a-project.md).

## Where it plugs in

This project is the connective tissue for the whole lab. The cybersecurity requirements it produces are what the other projects satisfy, and the trace command proves it — the firmware validation pipeline maps its test IDs directly to requirement IDs from here.

See [portfolio map](../../docs/portfolio-map.md).

## What it covers

ISO/SAE 21434 · TARA · threat modelling · attack feasibility rating · risk determination · cybersecurity requirements · requirement traceability · UN R155 evidence.

Full matrix: [capability coverage](../../docs/skills-coverage.md).

## Claim discipline

Say: *"I implemented the publicly described ISO/SAE 21434 TARA workflow as a tool with enforced traceability, and produced a complete worked threat analysis for a telematics gateway ECU."*

Do not say that you have performed TARA in a professional CSMS context, that the analysis is conformant, or that you were part of a type-approval process. And be upfront that the scoring thresholds are documented project conventions — that honesty reads as maturity, not as a gap.

Get the vocabulary exactly right. Calling a damage scenario a "threat" is the tell that someone has read a blog post rather than thought about the method. The terms are defined in the [glossary](../../docs/glossary.md).
