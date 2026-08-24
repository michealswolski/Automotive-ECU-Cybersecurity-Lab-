# SPEC - ISO/SAE 21434 TARA Workbench

Version 1.0. Source of truth.

---

## 1. Purpose

Run the ISO/SAE 21434 Clause 15 threat analysis and risk assessment as structured, traceable,
version-controlled data, and produce one complete worked TARA for an OTA-capable telematics gateway
ECU that can stand as a portfolio piece.

Out of scope: reproducing the text or tables of the standard (it is copyrighted and paid), claiming
conformance, and multi-user workflow.

---

## 2. Domain model

Each entity is a pydantic model with a stable ID prefix. Everything lives in `tara/model/`.

| Entity | ID | Key fields |
|---|---|---|
| `Item` | `ITEM-nn` | name, boundary, operational environment, assumptions, interfaces, external dependencies |
| `Asset` | `AST-nnn` | name, type (function/data/interface/hardware), cybersecurity properties at stake (C/I/A/authenticity), owning item |
| `DamageScenario` | `DMG-nnn` | asset ref, description of adverse consequence to road users, impact ratings |
| `ThreatScenario` | `THR-nnn` | damage scenario refs, STRIDE category, description in the form "compromise of <property> of <asset> leading to <damage>" |
| `AttackPath` | `ATP-nnn` | threat scenario ref, ordered steps, entry point, feasibility factors |
| `Risk` | `RSK-nnn` | threat scenario ref, aggregated impact, aggregated feasibility, computed value 1-5 |
| `TreatmentDecision` | `TRT-nnn` | risk ref, option (avoid/reduce/share/retain), rationale, residual risk |
| `CybersecurityGoal` | `GOL-nnn` | threat scenario refs, statement |
| `CybersecurityRequirement` | `REQ-nnn` | goal ref, statement, verification method, verification criteria, allocation (SW/HW/process) |
| `Claim` | `CLM-nnn` | requirement ref, evidence link (a file path, a test ID, a repo URL) |

`Claim` is what lets you point a requirement at a test in one of your other repos. Use it: a
requirement that says "the ECU shall reject firmware images with a security version number below the
stored monotonic counter" should link to the secure boot project's `test_rollback.py`. That link is
the single most impressive thing this repo can contain.

---

## 3. The TARA workflow

Implement as discrete, resumable stages. `tara status` shows which stages are complete for the item.

### Stage 1 - Item definition
Boundary, interfaces, operational environment, assumptions, and preliminary architecture. Store the
architecture as a component/interface graph so attack paths can be validated against it -- an attack
path that traverses an interface not in the item definition is a defect the linter flags.

### Stage 2 - Asset identification and damage scenarios
For each asset, name the cybersecurity properties whose loss matters, and write the damage scenario
as a consequence **to road users**, not to the company. "Attacker reads the log file" is not a damage
scenario; "vehicle occupant's location history is disclosed" is.

### Stage 3 - Impact rating
Four categories, each rated `negligible | moderate | major | severe`:
- **Safety** — potential for physical harm. Reference ISO 26262 severity reasoning where relevant.
- **Financial** — economic loss to road users.
- **Operational** — loss or degradation of vehicle function.
- **Privacy** — exposure of personal data.

Overall impact for a damage scenario is the **maximum** across the four. Each rating requires a
written justification string; the linter rejects an empty one.

### Stage 4 - Threat scenario identification
Derive threat scenarios from damage scenarios using STRIDE per element over the architecture graph.
`tara threats suggest --asset AST-007` walks the graph and proposes candidate threat scenarios per
STRIDE category for analyst review. Suggestions are **proposals requiring explicit acceptance** —
never auto-accepted into the analysis. Record who accepted and why.

### Stage 5 - Attack path analysis
Attack paths as ordered step lists, each step naming the interface or component traversed, validated
against the architecture graph. Render as attack trees (Graphviz DOT + Mermaid). Support multiple
paths per threat scenario.

### Stage 6 - Attack feasibility rating
Attack-potential method. Five factors scored per path with justifications:
`elapsed_time`, `specialist_expertise`, `knowledge_of_item`, `window_of_opportunity`, `equipment`.

Sum the factor scores and map the total to `high | medium | low | very low` feasibility. **Publish
your scoring table in `docs/method.md` as a documented project convention**, cite the publicly
available descriptions of the attack-potential approach, and do not present the table as a
reproduction of the standard.

Where a threat scenario has several attack paths, the scenario takes the **highest** feasibility
among them — an attacker uses the easiest route.

### Stage 7 - Risk determination
`risk = matrix[impact][feasibility]`, values 1 (lowest) to 5 (highest). The matrix is a data file
(`config/risk_matrix.yaml`), not code, so it can be swapped for an OEM-specific one. Computed only —
`tara risk set` does not exist.

### Stage 8 - Risk treatment
One of avoid / reduce / share / retain, with rationale. Reduction produces cybersecurity goals, which
produce requirements, which get verification methods and criteria, which get evidence claims.
Residual risk is recorded after treatment.

---

## 4. Linting (the feature that makes this credible)

`tara lint` runs a rule set and exits nonzero on findings. Every rule has an ID and appears in
`docs/rules.md`.

| Rule | Checks |
|---|---|
| `L001` | Every asset has at least one damage scenario |
| `L002` | Every damage scenario has all four impact ratings with justifications |
| `L003` | Every threat scenario traces to at least one damage scenario |
| `L004` | Every threat scenario has at least one attack path |
| `L005` | Every attack path step traverses an interface present in the item definition |
| `L006` | Every feasibility factor has a justification |
| `L007` | Every risk ≥ a configurable threshold has a treatment decision |
| `L008` | Every "reduce" decision produces at least one goal |
| `L009` | Every goal produces at least one requirement |
| `L010` | Every requirement has a verification method and verification criteria |
| `L011` | No orphans: nothing unreferenced anywhere in the chain |
| `L012` | No dangling references to nonexistent IDs |
| `L013` | Damage scenarios describe consequences to road users, not to the organization (heuristic warning) |

Run `tara lint` in CI over the worked example. A repo whose own analysis passes its own linter is a
different quality signal than a folder of markdown.

---

## 5. Outputs

```
tara report --format md|html|xlsx     # full TARA document, audit-style
tara matrix                            # risk heatmap: threat scenarios by impact x feasibility
tara trace REQ-014                     # bidirectional chain for one requirement
tara trace --from AST-007              # everything downstream of an asset
tara tree THR-012 --format mermaid     # attack tree
tara diff <git-ref>                    # what changed in the analysis between two commits
tara stats                             # counts by stage, risk distribution, coverage
```

`tara diff` matters more than it looks: TARA is explicitly a living activity revisited across the
lifecycle, and being able to show what changed between two revisions of an analysis is a real
capability.

---

## 6. The worked example (this is the actual deliverable)

`examples/telematics-gateway/` — a complete TARA for an OTA-capable telematics/gateway ECU.

Minimum scope, and do not pad it:
- 1 item definition with a real architecture graph (modem, app processor, HSM, CAN-FD controller,
  Ethernet switch, OBD-II adjacency, flash, debug port)
- ≥12 assets across functions, data, interfaces, and hardware
- ≥15 damage scenarios with all four impact dimensions justified
- ≥20 threat scenarios covering all six STRIDE categories
- ≥25 attack paths, including at least three multi-step chains crossing a trust boundary
  (e.g. cellular → app processor → CAN-FD → brake domain)
- Full risk determination and treatment for every threat scenario
- ≥30 cybersecurity requirements with verification methods
- **≥5 requirements with `Claim` evidence links pointing at the secure boot, SecOC, and key
  lifecycle repos**

Depth beats breadth. Fifteen thoroughly justified threat scenarios read as engineering; sixty
one-line entries read as generated filler, and an interviewer can tell in thirty seconds which one
they are holding.

---

## 7. Repository layout

```
tara-workbench/
├── README.md  pyproject.toml  Makefile
├── config/risk_matrix.yaml  config/feasibility_scoring.yaml
├── src/tara/
│   ├── model/     item.py assets.py threats.py paths.py risk.py treatment.py requirements.py
│   ├── workflow/  stages.py stride.py feasibility.py determination.py
│   ├── lint/      rules.py runner.py
│   ├── render/    markdown.py html.py xlsx.py graphviz.py mermaid.py
│   ├── store.py   # YAML load/save, ID allocation, referential integrity
│   └── cli.py
├── examples/telematics-gateway/*.yaml
├── tests/  docs/  .github/workflows/ci.yml    # CI runs `tara lint` on the example
```

---

## 8. Honesty requirements

- The README states: this is an independent implementation of the publicly described TARA workflow,
  built for learning and demonstration. It is not conformant, not certified, and not a substitute
  for a TARA performed under an organizational cybersecurity management system.
- The scoring tables are project conventions documented in `docs/method.md`, informed by publicly
  available descriptions of the attack-potential approach.
- No text, table, or figure from the paid standard is reproduced.
