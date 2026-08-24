# CLAUDE.md - ISO/SAE 21434 TARA Workbench

You are building this project from scratch. Read `SPEC.md` (source of truth) and `BUILD_PLAN.md`
before writing code.

## What this is

Two things, and the second one matters more:

1. A **tool** that runs the ISO/SAE 21434 Clause 15 TARA workflow as structured data rather than as
   a spreadsheet: item definition, asset identification with damage scenarios, threat scenario
   identification, impact rating, attack path analysis, attack feasibility rating, risk
   determination, and risk treatment producing traceable cybersecurity goals and requirements.
2. A **completed, worked TARA** for one real ECU, committed to the repo as the flagship example.

The tool without the worked example is a schema. The worked example is the artifact a hiring manager
reads. Budget your effort accordingly: the analysis is the deliverable, the tool is what makes the
analysis reproducible and traceable.

## The example item

Use an **OTA-capable telematics/gateway ECU** as the worked example. It is the right choice because
it touches every interesting boundary: cellular modem, Wi-Fi/Bluetooth, CAN and CAN-FD to the
in-vehicle network, Ethernet to the domain controllers, OBD-II adjacency, a firmware update path, a
secure boot chain, and stored cryptographic keys. That gives you real attack paths across every other
project in this portfolio rather than a toy analysis of a door module.

## Non-negotiables

1. **The risk determination is computed, never typed.** Impact and attack feasibility go in; the risk
   value comes out of the matrix. A TARA where an analyst hand-writes "risk = 4" is a spreadsheet
   with extra steps.
2. **Full traceability, both directions.** Every cybersecurity requirement traces up to a goal, to a
   risk, to a threat scenario, to a damage scenario, to an asset. `tara trace REQ-014` prints that
   chain. `tara orphans` finds anything unlinked. This bidirectional traceability is what auditors
   actually check and what most portfolio TARAs completely lack.
3. **Attack feasibility uses the attack-potential method** with its five factors scored explicitly:
   elapsed time, specialist expertise, knowledge of the item, window of opportunity, and equipment.
   Each score carries a written justification. An unjustified score is a defect the linter flags.
4. **The analysis is version-controlled YAML**, not a binary. Diffs are reviewable.
5. **Do not fabricate clause numbers, tables, or thresholds.** ISO/SAE 21434 is a paid standard. Use
   what is publicly documented, cite by document name where you cannot verify a clause, and mark any
   scoring threshold you chose yourself as a project convention in `docs/method.md`. Say plainly in
   the README that the scoring tables are a documented interpretation, not a reproduction of the
   standard's text.

## Verify before coding

Web-search to confirm, rather than recalling: the TARA workflow step names and ordering in Clause 15,
the four impact categories (safety, financial, operational, privacy) and their rating scale, the
attack-potential factors, the risk matrix shape, and the risk treatment options. Publicly available
summaries agree on the structure; get the vocabulary exactly right, because using the wrong term for
a step is the tell that someone has read a blog post and not thought about the method.

## Engineering standards

Python 3.12+, `pydantic` v2 models for every TARA entity, `typer` CLI, `mypy --strict`, `ruff`,
`pytest` ≥85%. The domain model is pure; rendering (Markdown, HTML, XLSX) is a separate layer.
