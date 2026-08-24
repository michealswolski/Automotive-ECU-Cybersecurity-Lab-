# Contributing

This is a personal portfolio repository, so the main audience for this document is future me — but issues and pull requests are welcome, particularly corrections.

## The most useful contribution

**Tell me where a claim is wrong.** If a protocol detail is inaccurate, a standard is misdescribed, a threat scenario does not hold up, or a piece of terminology is used loosely, open an issue. Precision is the point of this repository, and a correction is worth more than a feature.

That goes double for anything in [`docs/honest-claims.md`](./docs/honest-claims.md). If something here reads as claiming more than it delivers, that is a bug of the most serious kind.

## Before opening a pull request

```bash
make check
```

That runs every consistency rule, verifies the generated documentation blocks are current, verifies the SVG assets match their generator, and runs the tooling's test suite. It needs nothing but Python 3.11+ — and `pytest` plus `ruff` if you touched the tooling (`make dev` installs them).

## Ground rules

**Do not edit generated content by hand.** Anything between `<!-- labctl:begin … -->` and `<!-- labctl:end … -->` is rendered from `lab.toml`. Change the manifest and run `make render`. Same for `assets/*.svg` — change `tools/assets/render_assets.py` and run `make assets`. CI checks both.

**Do not add a capability claim without a project that backs it.** Every id in a project's `covers` list must resolve to a declared `[[skill]]`, every declared skill must be covered by some project, and no project may claim a skill marked `bench_only`. `labctl validate` enforces all three. See [tooling](./docs/tooling.md).

**Do not fabricate a clause number, a table, or a threshold.** ISO/SAE 21434 and MISRA C are paid standards; this repository reproduces neither. Cite by document name where a clause cannot be verified, and mark any threshold you chose yourself as a project convention.

**No hand-rolled cryptography.** Use `cryptography` (pyca) primitives throughout. The projects are about how cryptography is deployed, not about reimplementing AES.

**Keep the simulation boundary explicit.** If a change makes a project look more like hardware than it is, it needs a sentence saying what is still modelled.

## Adding a project

1. Create `projects/<id>/` with all seven required files — `README.md`, `SPEC.md`, `BUILD_PLAN.md`, `ACCEPTANCE.md`, `CLAUDE.md`, `prompts/kickoff.md`, `docs/interview-talking-points.md`.
2. Add a `[[project]]` entry to `lab.toml` with a unique `id`, `number` and `order`.
3. `make render`, then `make check`.

## Commit style

One commit per build phase when implementing a project. The commit history is part of the artefact — a reviewer who can see a project assembled phase by phase, each with its acceptance criteria met, is reading evidence.

Conventional-commit prefixes (`feat:`, `fix:`, `docs:`, `chore:`) where they fit naturally. Not enforced.

## Code style

Python 3.11+, `ruff` for lint and format (line length 100). Type annotations on anything public. The repository tooling is deliberately zero-dependency; the projects themselves may take dependencies, pinned in their own `pyproject.toml`.
