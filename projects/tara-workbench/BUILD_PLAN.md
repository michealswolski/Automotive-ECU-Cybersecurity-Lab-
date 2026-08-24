# BUILD_PLAN - phase order

## Phase 0 - Scaffold
`pyproject.toml` (deps: `pydantic`, `typer`, `rich`, `pyyaml`, `jinja2`, `openpyxl`, `graphviz`;
dev: `pytest`, `ruff`, `mypy`, `pytest-cov`). `Makefile` (`setup|check|lint-example|report|clean`).
**Accept:** `make check` green; `tara --help` prints.

## Phase 1 - Domain model
Every entity from SPEC §2 as a pydantic v2 model with ID validation and typed cross-references.
`store.py` for YAML load/save, ID allocation, and referential integrity on load.
**Accept:** round-trip YAML load/save is lossless; a dangling reference fails validation at load time
with a message naming both IDs.

## Phase 2 - Workflow stages 1-3
Item definition with architecture graph, assets, damage scenarios, impact rating with justifications.
`tara item|asset|damage` CRUD commands.
**Accept:** you can build an item and three assets end to end from the CLI; missing justifications
are rejected.

## Phase 3 - Stages 4-5
STRIDE-per-element suggestion over the architecture graph (proposals only, explicit acceptance
required), attack paths validated against the graph, attack tree rendering.
**Accept:** an attack path referencing an interface absent from the item definition is rejected;
Mermaid and DOT trees render.

## Phase 4 - Stages 6-8
Attack-potential feasibility scoring from `config/feasibility_scoring.yaml`, risk determination from
`config/risk_matrix.yaml`, treatment decisions, goals, requirements, claims.
**Accept:** risk values are computed and there is no code path that sets one directly; changing the
matrix file changes the results with no code change.

## Phase 5 - Linter
All thirteen rules from SPEC §4, `docs/rules.md`, nonzero exit on findings.
**Accept:** each rule has a test that constructs a violating analysis and asserts the finding.

## Phase 6 - Reporting
Markdown, HTML, and XLSX reports; risk heatmap; `tara trace` both directions; `tara diff`; `tara stats`.
**Accept:** the HTML report is readable standalone; `tara trace REQ-nnn` prints the full chain from
requirement to asset.

## Phase 7 - THE WORKED EXAMPLE
Build the complete telematics gateway TARA to the scope in SPEC §6. This is the phase that takes the
longest and matters the most. Work asset by asset. Do not generate all twenty threat scenarios in one
pass -- write five, review them critically for whether they would survive a reviewer, then continue.
**Accept:** `tara lint examples/telematics-gateway` passes clean in CI; the generated HTML report is
something you would attach to a job application; at least five requirements carry evidence claims
pointing at your other repos.

## Phase 8 - Documentation
- `README.md`: what a TARA is and why it exists, the eight stages, a screenshot of the risk heatmap,
  the worked example linked prominently, the honesty statement, and the traceability demo
  (`tara trace REQ-014` output pasted in full).
- `docs/method.md`: the scoring conventions, where they came from, and what is a project decision
  versus what is publicly documented method.
- `docs/rules.md`, `docs/decisions.md`.
- `docs/how-this-connects.md`: the map from requirements in this TARA to implementations and tests in
  the secure boot, SecOC, and key lifecycle repos.
**Accept:** a reader who has never heard of ISO 21434 understands, from the README alone, what a TARA
produces and why traceability is the hard part.

## Phase 9 (optional)
1. `tara serve` — a read-only web view of the analysis with clickable traceability.
2. Import/export to a generic spreadsheet format so the analysis can be handed to someone using Excel.
3. A second, smaller worked example (a body control module) to show the method generalizes.
