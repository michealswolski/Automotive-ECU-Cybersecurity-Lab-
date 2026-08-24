# Tooling

A portfolio that describes itself in six places will eventually describe itself six different ways. `labctl` exists so that cannot happen: one manifest, and every table a reader sees is rendered from it.

Zero third-party dependencies. `tomllib` has been in the standard library since Python 3.11 and everything else the tool does is string handling, so a reviewer can clone the repository and run it immediately — no virtualenv, no install step, no dependency resolution.

---

## Commands

| Make target | Underneath | What it does |
|---|---|---|
| `make status` | `labctl status` | Per-project phases, acceptance progress, effort |
| `make validate` | `labctl validate` | Every consistency rule; exits non-zero on any finding |
| `make standards` | `labctl standards` | The standards register, and which rows need re-checking |
| `make render` | `labctl render` | Regenerate every generated block from the manifest |
| `make test` | `pytest` | The tool's own test suite |
| `make lint` | `ruff` | Lint and format check |
| `make assets` | `render_assets.py` | Regenerate every SVG in both themes |
| `make show PROJECT=…` | `labctl show` | Phases, capabilities and bridges for one project |
| `make check` | all of the above in `--check` mode | Exactly what CI runs |

`labctl` finds the repository root by walking up for `lab.toml`, so it works from any subdirectory the way `git` does.

---

## The manifest

`lab.toml` is the single source of truth. It holds three things:

**`[lab]`** — the repository's name, owner and tagline.

**`[[project]]`** — one entry per project: id, display number, build order, title, status, language, effort, a summary, the centerpiece demo, the capabilities it covers, and the bridges it consumes and provides.

**`[[skill]]`** — every capability the portfolio either demonstrates or explicitly does not. Bench-only skills carry `bench_only = true`.

**`[[standard]]`** — the standards register: the edition each project should cite, its status, when it was last checked (`verified`) and against what (`source`: `web` for a source consulted on that date, `report` for a row taken from the 2026 spec-validation report). See [standards register](./standards-register.md).

Status values are `specified`, `building`, `built`, and they mean exactly what the validation rules enforce — see below.

---

## Generated blocks

Files containing generated content mark it with a comment pair:

```markdown
<!-- labctl:begin BLOCK-NAME -->
...generated — do not edit by hand...
<!-- labctl:end BLOCK-NAME -->
```

`labctl render` rewrites the span. `labctl render --check` fails if what is on disk differs from what would be written, which is the form CI runs — so a manifest change nobody propagated into the README is caught in review rather than shipping as a contradiction.

| Block | Renders |
|---|---|
| `readme-projects` | The two-column project card grid |
| `readme-status` | The one-row-per-project progress table |
| `build-order` | The recommended sequence with reasons |
| `coverage-matrix` | Capability by project, grouped by domain |
| `bench-gaps` | The capabilities deliberately not claimed |
| `standards-register` | The full standards register, grouped |
| `standards-notes` | Each register row's engineering guidance |
| `standards-watchlist` | Rows under active revision |
| `project-standards` | Which documents each project implements |
| `totals` | The projects / phases / acceptance-criteria summary line |

Blocks containing project links are rendered path-aware: the same block emits `./projects/…` in the root README and `../projects/…` in `docs/`, so the link checker passes in both.

---

## Validation rules

`labctl validate` runs all of these. Each exists because breaking it would make the repository say something untrue about itself.

| Rule | Fails when |
|---|---|
| `project-dir` | A manifest project has no directory under `projects/` |
| `orphan-project` | A directory under `projects/` has no manifest entry |
| `project-files` | A project is missing one of the eight required files — `README.md`, `SPEC.md`, `BUILD_PLAN.md`, `ACCEPTANCE.md`, `CLAUDE.md`, `CORRECTIONS.md`, `prompts/kickoff.md`, `docs/interview-talking-points.md` |
| `build-plan` | A `BUILD_PLAN.md` has no parseable `## Phase N` headings |
| `acceptance` | An `ACCEPTANCE.md` has no checklist items |
| `status` | A project is marked `built` with acceptance criteria still unchecked, or marked `specified` after work has visibly started |
| `skill-ref` | A project claims a capability id that is not declared |
| `uncovered-skill` | A declared capability is covered by no project and is not marked `bench_only` |
| `bench-claim` | **A project claims a capability that requires hardware** |
| `standard-ref` | A project cites a standard that is not declared in the register |
| `superseded-standard` | **A project cites an edition marked superseded** |
| `orphan-standard` | A register row is cited by no project |
| `no-standard` | A project cites no standard at all |
| `standard-verified` | A register row's `verified` value is not an ISO date |
| `bridge` | A project consumes a bridge nothing provides |
| `dead-link` | A relative Markdown link does not resolve |

Two rules are worth pointing at. `superseded-standard` makes "cite the current edition" a property of the build rather than a hope — mark a row superseded and every project still citing it fails until it is updated. And `bench-claim` It is the repository's [claim-discipline policy](./honest-claims.md) expressed as an executable rule instead of a paragraph of good intentions — a policy that fails the build is a policy that survives a deadline.

External links are not followed. CI runs offline, and a network check would make the build flaky for no benefit.

---

## Assets

`tools/assets/render_assets.py` generates every SVG in `assets/` from one geometry description and two palettes. Running it with `--check` fails if `assets/` has drifted from the generator, which is what stops a hand-edit to the dark hero from silently never reaching the light one.

The palettes are role-based — `panel`, `accent`, `danger`, `muted` — so the light theme reassigns hues without any drawing code needing to know which theme it is rendering. Every animation is wrapped in a `prefers-reduced-motion` guard, and every graphic renders correctly with all animation disabled.

---

## Testing

The test suite lives in `tools/labctl/tests/` and runs against a synthetic repository built in a temporary directory, so it asserts on behaviour rather than on whatever the manifest happens to say today. Two tests are the exception: they run `status` and `validate` against the real repository, and they fail if this repository stops satisfying its own rules.

```bash
make test               # pytest
make lint               # ruff check + format check
make check              # everything CI runs
```

---

## Adding a project

1. Create `projects/<id>/` with all eight required files.
2. Add a `[[project]]` entry to `lab.toml` with a unique `id`, `number` and `order`.
3. Make sure every id in its `covers` list is declared as a `[[skill]]`, and every id in its `standards` list as a `[[standard]]`.
4. `make render` — the README tables update themselves.
5. `make check` — confirm nothing broke.

If step 5 fails, the message names the rule and the file. That is the whole point.
