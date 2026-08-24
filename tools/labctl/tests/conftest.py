"""Shared fixtures.

Most tests run against a synthetic repository built in a tmp dir rather than
against the real one, so they assert on behaviour instead of on whatever the
manifest happens to say today. A handful of tests do point at the real
repository — those are the ones that would catch a genuine regression in the
repo's own consistency, and they are marked ``repo``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[3]


MINIMAL_MANIFEST = """
[lab]
name = "Test Lab"
owner = "someone"
repo = "test-lab"
tagline = "A tagline."

[[project]]
id = "alpha"
number = 1
order = 1
title = "Alpha"
status = "specified"
language = "Python"
effort = "M"
summary = "Alpha summary."
centerpiece = "Alpha centerpiece."
covers = ["thing"]
standards = ["spec-one"]
provides = ["alpha:widget"]

[[project]]
id = "beta"
number = 2
order = 2
title = "Beta"
status = "specified"
language = "C"
effort = "L"
summary = "Beta summary."
centerpiece = "Beta centerpiece."
covers = ["other"]
standards = ["spec-one", "spec-two"]
consumes = ["alpha:widget"]

[[skill]]
id = "thing"
label = "Thing"
group = "Group A"

[[skill]]
id = "other"
label = "Other"
group = "Group A"

[[skill]]
id = "bench-thing"
label = "Bench Thing"
group = "Bench"
bench_only = true

[[standard]]
id = "spec-one"
name = "SPEC ONE"
title = "The first specification"
edition = "2024"
status = "current"
group = "Group S"
verified = "2026-08-24"
source = "web"
note = "A note about spec one."

[[standard]]
id = "spec-two"
name = "SPEC TWO"
title = "The second specification"
edition = "draft"
status = "imminent"
group = "Group S"
verified = "2026-08-24"
source = "report"
"""

BUILD_PLAN = """# Build plan

## Phase 0 - Scaffold
Do the scaffold.
**Accept:** it builds.

## Phase 1 — Real work
**Accept:** it works.

## Phase 2 (optional) - Extras
**Accept:** nothing.
"""

# The baseline fixture must itself satisfy every validation rule, so a
# `specified` project starts with nothing checked off.
ACCEPTANCE = """# Acceptance

- [ ] First thing
- [ ] Second thing
- [ ] Third thing
"""


def write_project(root: Path, project_id: str) -> Path:
    """Create a project directory containing every required kit file."""
    directory = root / "projects" / project_id
    (directory / "prompts").mkdir(parents=True, exist_ok=True)
    (directory / "docs").mkdir(parents=True, exist_ok=True)
    (directory / "README.md").write_text(f"# {project_id}\n", encoding="utf-8")
    (directory / "SPEC.md").write_text("# Spec\n", encoding="utf-8")
    (directory / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
    (directory / "BUILD_PLAN.md").write_text(BUILD_PLAN, encoding="utf-8")
    (directory / "ACCEPTANCE.md").write_text(ACCEPTANCE, encoding="utf-8")
    (directory / "CORRECTIONS.md").write_text("# Corrections\n", encoding="utf-8")
    (directory / "prompts" / "kickoff.md").write_text("# Kickoff\n", encoding="utf-8")
    (directory / "docs" / "interview-talking-points.md").write_text("# Points\n", encoding="utf-8")
    return directory


@pytest.fixture
def lab_root(tmp_path: Path) -> Path:
    """A synthetic repository that passes every validation rule."""
    (tmp_path / "lab.toml").write_text(MINIMAL_MANIFEST, encoding="utf-8")
    write_project(tmp_path, "alpha")
    write_project(tmp_path, "beta")
    return tmp_path


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT
