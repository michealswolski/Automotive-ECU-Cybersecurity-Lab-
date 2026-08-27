"""Invariants about the repository's own build, checked against the real tree.

These exist because of a specific failure: `make check` was documented as
"everything CI runs" but omitted the lint step, so a tree that reported green
locally was rejected by CI. A local gate that is narrower than the remote one
is worse than no local gate — it produces confident, wrong pushes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

#: `run: <command>` inside a workflow step, single-line form only. Block
#: scalars (`run: |`) are deliberately not matched: the only one in this
#: workflow is the reporting job's summary, which is not a check, and its body
#: lines do not start with `run:` so they are skipped with it.
_RUN_RE = re.compile(r"^[ \t]*-?[ \t]*run:[ \t]+(?![|>])(\S.*?)[ \t]*$", re.MULTILINE)
#: `$(VAR)` references in a Makefile recipe.
_MAKE_VAR_RE = re.compile(r"\$\(([A-Z_]+)\)")
#: `NAME ?= value` / `NAME := value` / `NAME = value` at the top of a Makefile.
_MAKE_ASSIGN_RE = re.compile(r"^([A-Z_]+)\s*[:?]?=\s*(.*?)\s*$", re.MULTILINE)

#: Steps that set the environment up rather than checking anything.
_SETUP_MARKERS = ("pip install", "pip3 install")
#: Tokens carrying no signal when comparing a CI command to a Makefile recipe.
_NOISE = {
    "make",
    "python",
    "python3",
    "-m",
    "--no-print-directory",
    "@",
    "",
}


def _makefile_variables(text: str) -> dict[str, str]:
    return {name: value for name, value in _MAKE_ASSIGN_RE.findall(text)}


def _expand(text: str, variables: dict[str, str]) -> str:
    """Substitute `$(VAR)` twice, which is enough for this Makefile's one level
    of indirection (LABCTL refers to LABCTL_DIR and PYTHON)."""
    for _ in range(2):
        text = _MAKE_VAR_RE.sub(lambda m: variables.get(m.group(1), m.group(0)), text)
    return text


def _target_block(makefile: str, target: str) -> str:
    """The target line plus its recipe, up to the next target or blank line."""
    lines = makefile.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(f"{target}:"):
            block = [line]
            for following in lines[index + 1 :]:
                if following and not following.startswith(("\t", " ")):
                    break
                block.append(following)
            return "\n".join(block)
    raise AssertionError(f"no target {target!r} in Makefile")


def _salient(command: str) -> set[str]:
    """Tokens that identify what a command actually does.

    Drops interpreter and make boilerplate, and environment assignments, so
    `PYTHONPATH=x python -m labctl render --check` and
    `$(LABCTL) render --check` reduce to comparable sets.
    """
    tokens = set()
    for token in command.replace("\t", " ").split():
        if "=" in token and not token.startswith("-"):
            continue  # env assignment such as PYTHONPATH=tools/labctl
        if token in _NOISE:
            continue
        tokens.add(token.lstrip("@"))
    return tokens


def _ci_check_commands(workflow: str) -> list[str]:
    """Every checking command in the workflow, setup steps excluded."""
    return [
        command
        for command in _RUN_RE.findall(workflow)
        if not any(marker in command for marker in _SETUP_MARKERS)
    ]


@pytest.fixture
def makefile(repo_root: Path) -> str:
    text = (repo_root / "Makefile").read_text(encoding="utf-8")
    return _expand(text, _makefile_variables(text))


@pytest.fixture
def workflow(repo_root: Path) -> str:
    return (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def test_make_check_covers_every_command_ci_runs(makefile: str, workflow: str) -> None:
    """The regression this file exists for.

    `make check` reaches `validate`, `lint` and `test` through prerequisites and
    sub-makes, so the comparison is against those targets' recipes as well as
    check's own.
    """
    reachable = "\n".join(
        _target_block(makefile, name) for name in ("check", "validate", "lint", "test", "render")
    )
    covered = _salient(reachable)

    missing: list[tuple[str, set[str]]] = []
    for command in _ci_check_commands(workflow):
        wanted = _salient(command)
        if not wanted <= covered:
            missing.append((command, wanted - covered))

    assert not missing, "CI runs commands `make check` does not: " + "; ".join(
        f"{command!r} (missing {sorted(gap)})" for command, gap in missing
    )


def test_make_check_runs_lint(makefile: str) -> None:
    """Named explicitly because this is the step that was missing."""
    assert "lint" in _target_block(makefile, "check")


def test_ci_runs_lint(workflow: str) -> None:
    assert any("lint" in command for command in _ci_check_commands(workflow))


def test_every_ci_check_command_is_recognised(workflow: str) -> None:
    """Guards the parser itself: if the workflow stops using single-line `run:`
    steps this test fails rather than silently comparing an empty set."""
    commands = _ci_check_commands(workflow)
    assert len(commands) >= 5, commands


def test_every_project_workflow_is_covered_by_that_project_s_makefile(repo_root: Path) -> None:
    """The same guard, applied to the per-project workflows.

    `ci.yml` runs the zero-dependency repository checks and `make check` covers
    it. A project with its own dependencies gets its own workflow, and the same
    rule has to hold there: whatever that workflow runs, the project's own
    `make check` has to reach, or a contributor's local green means nothing.
    """
    for workflow_path in sorted((repo_root / ".github" / "workflows").glob("*.yml")):
        if workflow_path.name == "ci.yml":
            continue
        workflow = workflow_path.read_text(encoding="utf-8")
        directory = re.search(r"working-directory:\s*(projects/\S+)", workflow)
        if directory is None:
            # A workflow with no project working-directory is repo-level
            # (deployment, reporting) and has no project Makefile to compare
            # against. `ci.yml` is the repo-level one this rule does cover.
            continue
        makefile_path = repo_root / directory.group(1) / "Makefile"
        assert makefile_path.exists(), (
            f"{workflow_path.name} points at a directory with no Makefile"
        )

        makefile = makefile_path.read_text(encoding="utf-8")
        makefile = _expand(makefile, _makefile_variables(makefile))
        targets = re.findall(r"^([a-z-]+):", makefile, re.MULTILINE)
        reachable = "\n".join(_target_block(makefile, name) for name in targets)
        covered = _salient(reachable) | {t for t in targets}

        for command in _ci_check_commands(workflow):
            wanted = _salient(command)
            assert wanted <= covered, (
                f"{workflow_path.name} runs {command!r}, which "
                f"{makefile_path} does not: {sorted(wanted - covered)}"
            )


def test_readme_documents_the_make_targets(repo_root: Path, makefile: str) -> None:
    """A target the README advertises has to exist."""
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    for target in re.findall(r"`make ([a-z]+)`", readme):
        _target_block(makefile, target)
