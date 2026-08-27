"""Render generated documentation blocks from the manifest.

Files that contain generated content mark it with a pair of comments::

    <!-- labctl:begin readme-projects -->
    ...generated, do not edit by hand...
    <!-- labctl:end readme-projects -->

``labctl render`` rewrites the span between the markers; ``labctl render
--check`` fails if the file on disk differs from what would be written. CI runs
the second form, so a manifest change that nobody propagated into the README
is caught in review instead of shipping as a contradiction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .inspect import ProjectState, inspect_all
from .manifest import Lab, Project

STATUS_LABEL = {
    "specified": "Specified",
    "building": "Building",
    "built": "Built",
}

#: Shields.io accent, matching the palette used by the SVG assets. The badge
#: background stays dark in every state — status is carried by the glyph and
#: the word, not by a colour that would put white text on a pale fill.
BADGE_BG = "0A1526"
BADGE_FG = "0F1F35"

STATUS_ICON = {
    "specified": "◻",
    "building": "◐",
    "built": "◼",
}

EFFORT_LABEL = {
    "S": "a weekend",
    "M": "a long weekend",
    "L": "a week of evenings",
    "XL": "two weeks of evenings",
}


class RenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class BlockResult:
    path: Path
    name: str
    changed: bool


def _marker(name: str) -> tuple[str, str]:
    return f"<!-- labctl:begin {name} -->", f"<!-- labctl:end {name} -->"


def apply_block(text: str, name: str, body: str) -> str:
    """Replace the span between the markers for *name* with *body*."""
    begin, end = _marker(name)
    pattern = re.compile(
        rf"({re.escape(begin)}\n).*?(\n{re.escape(end)})",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise RenderError(f"no labctl block named {name!r} found")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text, count=1)


def has_block(text: str, name: str) -> bool:
    begin, _ = _marker(name)
    return begin in text


# ---------------------------------------------------------------------------
# Block generators
# ---------------------------------------------------------------------------


def _badge(label: str, message: str) -> str:
    """A shields.io URL in the palette used across the profile and this repo."""
    return (
        f"https://img.shields.io/badge/{_slug(label)}-{_slug(message)}-{BADGE_BG}"
        f"?style=flat-square&labelColor={BADGE_BG}&color={BADGE_FG}"
    )


def _slug(text: str) -> str:
    """Escape a badge segment: shields reads ``_`` as a space and ``--`` as a
    literal dash, so both have to be encoded before the string goes in a URL."""
    return text.replace("-", "--").replace("_", "__").replace(" ", "_").replace("+", "%2B")


def _status_badge(project: Project, state: ProjectState) -> str:
    label = STATUS_LABEL[project.status]
    if project.status == "building" and state.acceptance_total:
        label = f"Building {state.acceptance_pct}%"
    return _badge("status", label)


def readme_projects(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """A two-column card grid of every project, in build order."""
    cards: list[str] = []
    for project in lab.by_order():
        state = states[project.id]
        phases = f"{state.core_phases} phases"
        if state.optional_phases:
            phases += f" + {state.optional_phases} optional"
        links = [f'<a href="{prefix}{project.path}/SPEC.md">spec</a>']
        if project.status == "built":
            # A finished project leads with its own README; the build plan is
            # history at that point.
            links.insert(0, f'<a href="{prefix}{project.path}">readme</a>')
        else:
            links.append(f'<a href="{prefix}{project.path}/BUILD_PLAN.md">build plan</a>')
        links.append(
            f'<a href="{prefix}{project.path}/docs/interview-talking-points.md">talking points</a>'
        )
        docs = " · ".join(links)
        run = (
            f"\n**Run it.** `{project.run}`\n" if project.status == "built" and project.run else ""
        )
        cards.append(
            f"""<td width="50%" valign="top">

### `{project.number:02d}` [{project.title}]({prefix}{project.path})

![status]({_status_badge(project, state)})
![language]({_badge("lang", project.language)})
![effort]({_badge("effort", EFFORT_LABEL.get(project.effort, project.effort))})

{project.summary}

**The demo that lands.** {project.centerpiece}
{run}
<sub>{phases} · {state.acceptance_total} acceptance criteria · {docs}</sub>

</td>"""
        )

    rows: list[str] = []
    for index in range(0, len(cards), 2):
        pair = cards[index : index + 2]
        if len(pair) == 1:
            pair.append('<td width="50%" valign="top"></td>')
        rows.append("<tr>\n" + "\n".join(pair) + "\n</tr>")
    return "\n<table>\n" + "\n".join(rows) + "\n</table>\n"


def readme_status(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """A compact one-row-per-project progress table."""
    lines = [
        "| # | Project | Status | Phases | Acceptance | Language |",
        "|---|---|---|---|---|---|",
    ]
    for project in lab.by_number():
        state = states[project.id]
        phases = f"{state.core_phases}"
        if state.optional_phases:
            phases += f" (+{state.optional_phases})"
        acceptance = f"{state.acceptance_done}/{state.acceptance_total}"
        lines.append(
            f"| `{project.number:02d}` "
            f"| [{project.title}]({prefix}{project.path}) "
            f"| {STATUS_ICON[project.status]} {STATUS_LABEL[project.status]} "
            f"| {phases} "
            f"| {acceptance} "
            f"| {project.language} |"
        )
    return "\n" + "\n".join(lines) + "\n"


def coverage_matrix(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """Skill by project, grouped, with bench-only skills called out separately."""
    numbered = lab.by_number()
    header = "| Capability | " + " | ".join(f"`{p.number:02d}`" for p in numbered) + " |"
    divider = "|---|" + "|".join([":---:"] * len(numbered)) + "|"

    out: list[str] = []
    for group, skills in lab.skill_groups().items():
        covered = [s for s in skills if not s.bench_only]
        if not covered:
            continue
        out.append(f"**{group}**")
        out.append("")
        out.append(header)
        out.append(divider)
        for skill in covered:
            marks = ["●" if skill.id in p.covers else "·" for p in numbered]
            out.append(f"| {skill.label} | " + " | ".join(marks) + " |")
        out.append("")
    return "\n" + "\n".join(out).rstrip() + "\n"


def bench_gaps(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """The capabilities this repo deliberately does not claim."""
    rows = [s for s in lab.skills if s.bench_only]
    if not rows:
        return "\nNone declared.\n"
    lines = ["| Capability | Claimed here? |", "|---|---|"]
    for skill in rows:
        lines.append(f"| {skill.label} | No — requires hardware |")
    return "\n" + "\n".join(lines) + "\n"


STANDARD_ICON = {
    "current": "●",
    "imminent": "◐",
    "draft": "◐",
    "superseded": "✕",
}

STANDARD_STATUS = {
    "current": "Current",
    "imminent": "Publication imminent",
    "draft": "Revision in draft",
    "superseded": "Superseded",
}


def standards_register(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """The full register, grouped, with the edition to cite and who cites it."""
    out: list[str] = []
    for group, standards in lab.standard_groups().items():
        out.append(f"### {group}")
        out.append("")
        out.append("| Standard | Edition to cite | Status | Cited by | Checked |")
        out.append("|---|---|---|:---:|---|")
        for standard in standards:
            citing = " ".join(f"`{p.number:02d}`" for p in lab.citing(standard.id)) or "—"
            checked = f"{standard.verified} · {standard.source}"
            out.append(
                f"| **{standard.name}** — {standard.title} "
                f"| {standard.edition} "
                f"| {STANDARD_ICON[standard.status]} {STANDARD_STATUS[standard.status]} "
                f"| {citing} "
                f"| {checked} |"
            )
        out.append("")
    return "\n" + "\n".join(out).rstrip() + "\n"


def standards_notes(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """Every register row's note, which is where the actual engineering
    guidance lives."""
    out: list[str] = []
    for group, standards in lab.standard_groups().items():
        out.append(f"### {group}")
        out.append("")
        for standard in standards:
            if not standard.note:
                continue
            out.append(f"**{standard.name} — {standard.edition}**")
            out.append("")
            out.append(standard.note)
            out.append("")
    return "\n" + "\n".join(out).rstrip() + "\n"


def standards_watchlist(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """Rows under active revision — the ones to re-check before quoting."""
    moving = [s for s in lab.standards if s.moving]
    if not moving:
        return "\nNothing in the register is under active revision.\n"
    lines = [
        "| Standard | Cite this today | Where it stands | Affects |",
        "|---|---|---|:---:|",
    ]
    for standard in moving:
        citing = " ".join(f"`{p.number:02d}`" for p in lab.citing(standard.id)) or "—"
        lines.append(
            f"| **{standard.name}** | {standard.edition} "
            f"| {STANDARD_STATUS[standard.status]} | {citing} |"
        )
    return "\n" + "\n".join(lines) + "\n"


def project_standards(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """One row per project naming the documents it implements."""
    lines = ["| # | Project | Implements |", "|---|---|---|"]
    for project in lab.by_number():
        names = ", ".join(lab.standard(s).name for s in project.standards) or "—"
        lines.append(
            f"| `{project.number:02d}` | [{project.title}]({prefix}{project.path}) | {names} |"
        )
    return "\n" + "\n".join(lines) + "\n"


def build_order(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """Recommended order, with the reason each position is where it is."""
    reasons = {
        "secure-boot-chain-simulator": "Highest credibility per hour, and it stands alone.",
        "can-secoc-demo": "The most memorable demo; the authenticator is reused twice later.",
        "ecu-key-lifecycle": "Provisions the MAC keys project 02 consumes — build the bridge.",
        "tara-workbench": "Needs real requirements to point at, so it wants the first three built.",
        "ivn-security-lab": "Reuses the SecOC enforcement point; building CAN-FD twice is waste.",
        "ecu-firmware-validation": "The most expensive by far. Do it when the rest are shipping.",
    }
    lines = ["| Order | Project | Why here | Effort |", "|:---:|---|---|---|"]
    for project in lab.by_order():
        lines.append(
            f"| {project.order} "
            f"| [{project.title}]({prefix}{project.path}) "
            f"| {reasons.get(project.id, '')} "
            f"| {EFFORT_LABEL.get(project.effort, project.effort)} |"
        )
    return "\n" + "\n".join(lines) + "\n"


def totals(lab: Lab, states: dict[str, ProjectState], prefix: str = "./") -> str:
    """One-line summary used in a couple of places."""
    core = sum(states[p.id].core_phases for p in lab.projects)
    optional = sum(states[p.id].optional_phases for p in lab.projects)
    criteria = sum(states[p.id].acceptance_total for p in lab.projects)
    done = sum(states[p.id].acceptance_done for p in lab.projects)
    return (
        f"\n**{len(lab.projects)} projects · {core} core build phases "
        f"({optional} optional) · {criteria} acceptance criteria · "
        f"{done} met so far.**\n"
    )


GENERATORS = {
    "readme-projects": readme_projects,
    "readme-status": readme_status,
    "coverage-matrix": coverage_matrix,
    "bench-gaps": bench_gaps,
    "build-order": build_order,
    "standards-register": standards_register,
    "standards-notes": standards_notes,
    "standards-watchlist": standards_watchlist,
    "project-standards": project_standards,
    "totals": totals,
}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def link_prefix(path: Path, root: Path) -> str:
    """The relative prefix that reaches the repo root from *path*'s directory.

    Blocks containing project links are rendered into both ``README.md`` and
    files under ``docs/``; without this the docs copies would point at
    ``docs/projects/...`` and the link checker would (rightly) fail them.
    """
    depth = len(path.parent.resolve().relative_to(root.resolve()).parts)
    return "./" if depth == 0 else "../" * depth


def render(lab: Lab, check: bool = False) -> list[BlockResult]:
    """Rewrite (or verify) every labctl block in every tracked Markdown file."""
    states = inspect_all(lab.root, lab.projects)
    results: list[BlockResult] = []

    for path in _target_files(lab.root):
        original = path.read_text(encoding="utf-8")
        updated = original
        prefix = link_prefix(path, lab.root)
        for name, generator in GENERATORS.items():
            if has_block(updated, name):
                updated = apply_block(updated, name, generator(lab, states, prefix))
        if updated == original:
            continue
        results.append(BlockResult(path=path, name="", changed=True))
        if not check:
            path.write_text(updated, encoding="utf-8")
    return results


def _target_files(root: Path) -> list[Path]:
    candidates = [root / "README.md", *sorted((root / "docs").glob("*.md"))]
    return [path for path in candidates if path.is_file()]
