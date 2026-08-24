"""Read the on-disk state of a project directory.

The manifest says what a project *is*; this module says how far along it
actually is, by parsing the two files that define progress:

* ``BUILD_PLAN.md`` — one ``## Phase N`` heading per phase, some marked
  optional.
* ``ACCEPTANCE.md`` — a checklist. Unchecked boxes are the remaining work.

Nothing here guesses. If a file is missing, the corresponding counts are zero
and :func:`labctl.validate` reports the missing file rather than papering over
it with an estimate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .manifest import REQUIRED_PROJECT_FILES, Project

#: ``## Phase 3 — Fuses, counters, policy`` / ``## Phase 9 (optional) - Extras``
_PHASE_RE = re.compile(r"^##\s+Phase\s+(\d+)\s*(.*)$", re.MULTILINE)
#: Leading punctuation between the phase number and its title.
_TITLE_TRIM_RE = re.compile(r"^[\s—–:-]+")
_CHECKED_RE = re.compile(r"^\s*[-*]\s+\[[xX]\]", re.MULTILINE)
_UNCHECKED_RE = re.compile(r"^\s*[-*]\s+\[ \]", re.MULTILINE)


@dataclass(frozen=True)
class Phase:
    number: int
    title: str
    optional: bool


@dataclass(frozen=True)
class ProjectState:
    """What is actually on disk for one project."""

    project_id: str
    exists: bool
    missing_files: tuple[str, ...]
    phases: tuple[Phase, ...]
    acceptance_total: int
    acceptance_done: int
    has_source: bool

    @property
    def core_phases(self) -> int:
        return sum(1 for phase in self.phases if not phase.optional)

    @property
    def optional_phases(self) -> int:
        return sum(1 for phase in self.phases if phase.optional)

    @property
    def acceptance_pct(self) -> int:
        if not self.acceptance_total:
            return 0
        return round(100 * self.acceptance_done / self.acceptance_total)

    @property
    def complete(self) -> bool:
        """True only when there is at least one acceptance criterion and every
        one of them is checked off. An empty checklist is never 'done'."""
        return self.acceptance_total > 0 and self.acceptance_done == self.acceptance_total


def parse_phases(text: str) -> tuple[Phase, ...]:
    """Extract phases from a BUILD_PLAN body.

    The six kits do not use one heading style — some use an em dash, some a
    hyphen, some append a time estimate or ``(optional, high value)``. Rather
    than normalise the kits, the parser tolerates all of it and keys 'optional'
    off the word appearing anywhere in the heading tail.
    """
    phases: list[Phase] = []
    for match in _PHASE_RE.finditer(text):
        number = int(match.group(1))
        tail = match.group(2).strip()
        optional = "optional" in tail.lower()
        title = _TITLE_TRIM_RE.sub("", tail)
        # Drop a leading parenthetical such as "(optional, high value)".
        if title.startswith("("):
            closing = title.find(")")
            if closing != -1:
                title = _TITLE_TRIM_RE.sub("", title[closing + 1 :])
        phases.append(
            Phase(
                number=number,
                title=title.strip() or f"Phase {number}",
                optional=optional,
            )
        )
    return tuple(phases)


def parse_checklist(text: str) -> tuple[int, int]:
    """Return ``(total, done)`` for a Markdown task list."""
    done = len(_CHECKED_RE.findall(text))
    todo = len(_UNCHECKED_RE.findall(text))
    return done + todo, done


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _has_source(directory: Path) -> bool:
    """Whether someone has started building, rather than only specifying.

    Either a ``src/`` tree exists, or ``tests/`` holds something beyond the
    ``.gitkeep`` placeholder every kit ships with.
    """
    if (directory / "src").is_dir():
        return True
    tests = directory / "tests"
    if not tests.is_dir():
        return False
    return any(child.name != ".gitkeep" for child in tests.iterdir())


def inspect_project(root: Path, project: Project) -> ProjectState:
    """Gather the on-disk facts for one project."""
    directory = root / project.path
    if not directory.is_dir():
        return ProjectState(
            project_id=project.id,
            exists=False,
            missing_files=REQUIRED_PROJECT_FILES,
            phases=(),
            acceptance_total=0,
            acceptance_done=0,
            has_source=False,
        )

    missing = tuple(name for name in REQUIRED_PROJECT_FILES if not (directory / name).is_file())
    phases = parse_phases(_read(directory / "BUILD_PLAN.md"))
    total, done = parse_checklist(_read(directory / "ACCEPTANCE.md"))

    has_source = _has_source(directory)

    return ProjectState(
        project_id=project.id,
        exists=True,
        missing_files=missing,
        phases=phases,
        acceptance_total=total,
        acceptance_done=done,
        has_source=has_source,
    )


def inspect_all(root: Path, projects: tuple[Project, ...]) -> dict[str, ProjectState]:
    return {project.id: inspect_project(root, project) for project in projects}
