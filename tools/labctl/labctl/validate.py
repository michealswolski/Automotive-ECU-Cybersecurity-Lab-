"""Consistency rules for the repository.

Each rule exists because breaking it would make the repo say something untrue
about itself — a project marked built with work outstanding, a skill claimed by
nothing, a README link into a file that was renamed. CI runs all of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .inspect import ProjectState, inspect_all
from .manifest import Lab

#: Inline Markdown links, excluding image embeds (which start with `!`).
_LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
#: Directories not worth walking when checking links.
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache"}


@dataclass(frozen=True)
class Finding:
    rule: str
    message: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.message}"


def check_project_dirs(lab: Lab, states: dict[str, ProjectState]) -> list[Finding]:
    """Every manifest project has a directory, and vice versa."""
    findings: list[Finding] = []
    for project in lab.by_number():
        state = states[project.id]
        if not state.exists:
            findings.append(
                Finding("project-dir", f"{project.id}: no directory at {project.path}/")
            )
            continue
        for name in state.missing_files:
            findings.append(Finding("project-files", f"{project.id}: missing {name}"))

    declared = {project.id for project in lab.projects}
    projects_dir = lab.root / "projects"
    if projects_dir.is_dir():
        for child in sorted(projects_dir.iterdir()):
            if child.is_dir() and child.name not in declared:
                findings.append(
                    Finding(
                        "orphan-project",
                        f"projects/{child.name}/ exists but has no [[project]] entry in lab.toml",
                    )
                )
    return findings


def check_build_plans(lab: Lab, states: dict[str, ProjectState]) -> list[Finding]:
    """A build plan with no parseable phases is a build plan nobody can follow."""
    findings: list[Finding] = []
    for project in lab.by_number():
        state = states[project.id]
        if state.exists and not state.phases:
            findings.append(
                Finding("build-plan", f"{project.id}: BUILD_PLAN.md has no '## Phase N' headings")
            )
        if state.exists and state.acceptance_total == 0:
            findings.append(
                Finding("acceptance", f"{project.id}: ACCEPTANCE.md has no checklist items")
            )
    return findings


def check_status(lab: Lab, states: dict[str, ProjectState]) -> list[Finding]:
    """`built` requires a finished acceptance checklist. This is the rule that
    stops the README claiming a project is done before it is."""
    findings: list[Finding] = []
    for project in lab.by_number():
        state = states[project.id]
        if not state.exists:
            continue
        if project.status == "built" and not state.complete:
            outstanding = state.acceptance_total - state.acceptance_done
            findings.append(
                Finding(
                    "status",
                    f"{project.id}: status is 'built' but {outstanding} acceptance "
                    f"criteria are still unchecked",
                )
            )
        if project.status == "specified" and state.acceptance_done:
            findings.append(
                Finding(
                    "status",
                    f"{project.id}: status is 'specified' but {state.acceptance_done} "
                    f"acceptance criteria are checked — bump it to 'building'",
                )
            )
    return findings


def check_skills(lab: Lab) -> list[Finding]:
    """Skill ids resolve, non-bench skills are covered, bench skills are not."""
    findings: list[Finding] = []
    known = {skill.id for skill in lab.skills}

    for project in lab.by_number():
        for skill_id in project.covers:
            if skill_id not in known:
                findings.append(
                    Finding("skill-ref", f"{project.id}: covers unknown skill {skill_id!r}")
                )

    for skill in lab.skills:
        covering = lab.covering(skill.id)
        if skill.bench_only and covering:
            names = ", ".join(project.id for project in covering)
            findings.append(
                Finding(
                    "bench-claim",
                    f"skill {skill.id!r} is bench-only but claimed by {names}. "
                    f"No simulation makes a bench skill true — see docs/bench-path.md",
                )
            )
        if not skill.bench_only and not covering:
            findings.append(
                Finding(
                    "uncovered-skill",
                    f"skill {skill.id!r} is claimed by no project — either cover it "
                    f"or mark it bench_only",
                )
            )
    return findings


def check_bridges(lab: Lab) -> list[Finding]:
    """Every `consumes` entry is produced by some project's `provides`."""
    findings: list[Finding] = []
    provided = {name for project in lab.projects for name in project.provides}
    for project in lab.by_number():
        for name in project.consumes:
            if name not in provided:
                findings.append(
                    Finding(
                        "bridge",
                        f"{project.id}: consumes {name!r}, which no project provides",
                    )
                )
    return findings


def check_links(lab: Lab) -> list[Finding]:
    """Relative Markdown links point at files that exist.

    External links are left alone — this runs offline in CI and a network check
    would make the build flaky for no benefit.
    """
    findings: list[Finding] = []
    for path in _markdown_files(lab.root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in _LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            bare = target.split("#", 1)[0].split("?", 1)[0]
            if not bare:
                continue
            resolved = (path.parent / bare).resolve()
            if not resolved.exists():
                rel = path.relative_to(lab.root)
                findings.append(Finding("dead-link", f"{rel}: link to {target!r} does not resolve"))
    return findings


def _markdown_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        out.append(path)
    return out


def run_all(lab: Lab) -> list[Finding]:
    """Every rule, in the order a reader would want them reported."""
    states = inspect_all(lab.root, lab.projects)
    findings: list[Finding] = []
    findings += check_project_dirs(lab, states)
    findings += check_build_plans(lab, states)
    findings += check_status(lab, states)
    findings += check_skills(lab)
    findings += check_bridges(lab)
    findings += check_links(lab)
    return findings
