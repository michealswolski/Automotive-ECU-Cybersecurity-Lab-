"""Load and model ``lab.toml``.

The manifest is deliberately the only place a project's title, summary, status
and skill coverage are written down. Everything a reader sees — README tables,
the docs status page, the landing site — is rendered from here, so the repo
cannot end up describing itself two different ways in two different files.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

VALID_STATUSES = ("specified", "building", "built")

#: Files a project directory must contain to count as a complete build kit.
REQUIRED_PROJECT_FILES = (
    "README.md",
    "SPEC.md",
    "BUILD_PLAN.md",
    "ACCEPTANCE.md",
    "CLAUDE.md",
    "prompts/kickoff.md",
    "docs/interview-talking-points.md",
)


class ManifestError(ValueError):
    """Raised when ``lab.toml`` is malformed in a way that is not worth
    limping past — a missing key, an unknown status, a duplicate id."""


@dataclass(frozen=True)
class Skill:
    """One capability the portfolio either demonstrates or explicitly does not.

    ``bench_only`` skills are the ones no simulation can honestly claim. They
    are listed so the gap is visible on purpose rather than by omission.
    """

    id: str
    label: str
    group: str
    bench_only: bool = False


@dataclass(frozen=True)
class Project:
    id: str
    number: int
    order: int
    title: str
    status: str
    language: str
    effort: str
    summary: str
    centerpiece: str
    covers: tuple[str, ...] = ()
    consumes: tuple[str, ...] = ()
    provides: tuple[str, ...] = ()

    @property
    def path(self) -> str:
        return f"projects/{self.id}"

    @property
    def label(self) -> str:
        """``01 · Secure Boot Chain Simulator`` — used wherever a project needs
        a stable, sortable display name."""
        return f"{self.number:02d} · {self.title}"


@dataclass(frozen=True)
class Lab:
    name: str
    owner: str
    repo: str
    tagline: str
    projects: tuple[Project, ...] = ()
    skills: tuple[Skill, ...] = ()
    root: Path = field(default=Path("."), compare=False)

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"

    def by_order(self) -> list[Project]:
        return sorted(self.projects, key=lambda p: p.order)

    def by_number(self) -> list[Project]:
        return sorted(self.projects, key=lambda p: p.number)

    def project(self, project_id: str) -> Project:
        for project in self.projects:
            if project.id == project_id:
                return project
        raise KeyError(project_id)

    def skill(self, skill_id: str) -> Skill:
        for skill in self.skills:
            if skill.id == skill_id:
                return skill
        raise KeyError(skill_id)

    def skill_groups(self) -> dict[str, list[Skill]]:
        """Skills bucketed by group, preserving manifest order within a group."""
        groups: dict[str, list[Skill]] = {}
        for skill in self.skills:
            groups.setdefault(skill.group, []).append(skill)
        return groups

    def covering(self, skill_id: str) -> list[Project]:
        """Projects that claim a given skill, in display order."""
        return [p for p in self.by_number() if skill_id in p.covers]


def _require(table: dict, key: str, where: str) -> object:
    if key not in table:
        raise ManifestError(f"{where}: missing required key {key!r}")
    return table[key]


def _clean(text: str) -> str:
    """Collapse a TOML multi-line string into one paragraph.

    The manifest wraps prose with trailing backslashes for readability; readers
    of the rendered output want a single flowing sentence.
    """
    return " ".join(text.split())


def load(root: Path | str = ".") -> Lab:
    """Parse ``lab.toml`` under *root* into a :class:`Lab`.

    Structural problems raise :class:`ManifestError` here. Cross-cutting
    consistency rules (unresolvable skill ids, an uncovered skill, a project
    claiming ``built`` with unchecked acceptance boxes) belong to
    :mod:`labctl.validate`, which needs the filesystem as well as the manifest.
    """
    root = Path(root).resolve()
    path = root / "lab.toml"
    if not path.exists():
        raise ManifestError(f"no lab.toml at {path}")

    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    lab_table = raw.get("lab")
    if not isinstance(lab_table, dict):
        raise ManifestError("lab.toml: missing [lab] table")

    projects: list[Project] = []
    for index, entry in enumerate(raw.get("project", [])):
        where = f"lab.toml [[project]] #{index + 1}"
        status = str(_require(entry, "status", where))
        if status not in VALID_STATUSES:
            raise ManifestError(
                f"{where}: status {status!r} is not one of {', '.join(VALID_STATUSES)}"
            )
        projects.append(
            Project(
                id=str(_require(entry, "id", where)),
                number=int(_require(entry, "number", where)),
                order=int(_require(entry, "order", where)),
                title=str(_require(entry, "title", where)),
                status=status,
                language=str(_require(entry, "language", where)),
                effort=str(_require(entry, "effort", where)),
                summary=_clean(str(_require(entry, "summary", where))),
                centerpiece=_clean(str(_require(entry, "centerpiece", where))),
                covers=tuple(entry.get("covers", ())),
                consumes=tuple(entry.get("consumes", ())),
                provides=tuple(entry.get("provides", ())),
            )
        )

    skills: list[Skill] = []
    for index, entry in enumerate(raw.get("skill", [])):
        where = f"lab.toml [[skill]] #{index + 1}"
        skills.append(
            Skill(
                id=str(_require(entry, "id", where)),
                label=str(_require(entry, "label", where)),
                group=str(_require(entry, "group", where)),
                bench_only=bool(entry.get("bench_only", False)),
            )
        )

    _reject_duplicates([p.id for p in projects], "project id")
    _reject_duplicates([p.number for p in projects], "project number")
    _reject_duplicates([p.order for p in projects], "project order")
    _reject_duplicates([s.id for s in skills], "skill id")

    return Lab(
        name=str(_require(lab_table, "name", "lab.toml [lab]")),
        owner=str(_require(lab_table, "owner", "lab.toml [lab]")),
        repo=str(_require(lab_table, "repo", "lab.toml [lab]")),
        tagline=str(_require(lab_table, "tagline", "lab.toml [lab]")),
        projects=tuple(projects),
        skills=tuple(skills),
        root=root,
    )


def _reject_duplicates(values: list, what: str) -> None:
    seen: set = set()
    for value in values:
        if value in seen:
            raise ManifestError(f"lab.toml: duplicate {what} {value!r}")
        seen.add(value)
