"""``labctl`` — the repository's own command line.

Five verbs:

* ``status``    — what is specified, what is being built, what is done
* ``validate``  — every consistency rule, exit non-zero on any finding
* ``render``    — regenerate the documentation blocks from ``lab.toml``
* ``standards`` — the standards register and what needs re-checking
* ``show``      — everything known about one project

No third-party dependencies. Colour is emitted only when stdout is a TTY, so
piping into a file or a CI log stays clean.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .inspect import inspect_all
from .manifest import Lab, ManifestError, load
from .render import EFFORT_LABEL, STANDARD_ICON, STATUS_ICON, STATUS_LABEL, render
from .validate import run_all, stale_standards

_ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
}


def _colour_enabled(stream) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


class Printer:
    def __init__(self, stream=None) -> None:
        self.stream = stream or sys.stdout
        self.colour = _colour_enabled(self.stream)

    def paint(self, text: str, *styles: str) -> str:
        if not self.colour:
            return text
        return "".join(_ANSI[s] for s in styles) + text + _ANSI["reset"]

    def line(self, text: str = "") -> None:
        print(text, file=self.stream)


def _find_root(start: Path) -> Path:
    """Walk up from *start* looking for lab.toml so the CLI works from any
    subdirectory, the way git does."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "lab.toml").is_file():
            return candidate
    return current


def cmd_status(lab: Lab, args: argparse.Namespace, out: Printer) -> int:
    states = inspect_all(lab.root, lab.projects)
    out.line(out.paint(lab.name, "bold"))
    out.line(out.paint(lab.tagline, "dim"))
    out.line()

    width = max(len(p.title) for p in lab.projects)
    header = (
        f"  {'#':>2}  {'PROJECT'.ljust(width)}  {'STATUS':<10}  "
        f"{'PHASES':>7}  {'ACCEPT':>8}  EFFORT"
    )
    out.line(out.paint(header, "dim"))
    for project in lab.by_number():
        state = states[project.id]
        phases = f"{state.core_phases}"
        if state.optional_phases:
            phases += f"+{state.optional_phases}"
        accept = f"{state.acceptance_done}/{state.acceptance_total}"
        style = {"specified": "dim", "building": "yellow", "built": "green"}[project.status]
        status = f"{STATUS_ICON[project.status]} {STATUS_LABEL[project.status]}"
        out.line(
            f"  {project.number:>2}  {project.title.ljust(width)}  "
            f"{out.paint(status.ljust(10), style)}  {phases:>7}  {accept:>8}  "
            f"{EFFORT_LABEL.get(project.effort, project.effort)}"
        )

    core = sum(states[p.id].core_phases for p in lab.projects)
    optional = sum(states[p.id].optional_phases for p in lab.projects)
    total = sum(states[p.id].acceptance_total for p in lab.projects)
    done = sum(states[p.id].acceptance_done for p in lab.projects)
    out.line()
    out.line(
        out.paint(
            f"  {len(lab.projects)} projects · {core} core phases (+{optional} optional) · "
            f"{done}/{total} acceptance criteria met",
            "cyan",
        )
    )
    bench = [s for s in lab.skills if s.bench_only]
    if bench:
        out.line(
            out.paint(
                f"  {len(bench)} capabilities deliberately not claimed here — "
                f"see docs/bench-path.md",
                "dim",
            )
        )
    return 0


def cmd_validate(lab: Lab, args: argparse.Namespace, out: Printer) -> int:
    findings = run_all(lab)
    if not findings:
        out.line(out.paint("✓ all checks passed", "green"))
        return 0
    for finding in findings:
        out.line(out.paint(f"✗ {finding}", "red"))
    out.line()
    out.line(out.paint(f"{len(findings)} finding(s)", "red", "bold"))
    return 1


def cmd_render(lab: Lab, args: argparse.Namespace, out: Printer) -> int:
    results = render(lab, check=args.check)
    if not results:
        out.line(out.paint("✓ generated blocks are up to date", "green"))
        return 0
    if args.check:
        for result in results:
            out.line(out.paint(f"✗ stale: {result.path.relative_to(lab.root)}", "red"))
        out.line()
        out.line("Run: make render")
        return 1
    for result in results:
        out.line(f"updated {result.path.relative_to(lab.root)}")
    return 0


def _fit(text: str, width: int) -> str:
    """Pad or ellipsise *text* to exactly *width* so terminal columns line up."""
    if len(text) <= width:
        return text.ljust(width)
    return text[: width - 1] + "…"


def cmd_standards(lab: Lab, args: argparse.Namespace, out: Printer) -> int:
    """The register, grouped, with the re-check list at the end."""
    out.line(out.paint("Standards register", "bold"))
    out.line(
        out.paint("The edition each project should cite, and when it was last checked.", "dim")
    )

    style = {"current": "green", "imminent": "yellow", "draft": "yellow", "superseded": "red"}
    # One name column across every group so the register reads as one table,
    # and a fixed edition column so the trailing columns stay aligned.
    name_width = max(len(s.name) for s in lab.standards)
    for group, standards in lab.standard_groups().items():
        out.line()
        out.line(out.paint(f"  {group.upper()}", "cyan"))
        for standard in standards:
            citing = " ".join(f"{p.number:02d}" for p in lab.citing(standard.id)) or "--"
            out.line(
                f"  {STANDARD_ICON[standard.status]} {standard.name.ljust(name_width)}  "
                f"{out.paint(_fit(standard.edition, 32), style[standard.status])}  "
                f"{citing:<14}  {out.paint(standard.verified + ' ' + standard.source, 'dim')}"
            )

    moving = stale_standards(lab)
    out.line()
    if moving:
        out.line(out.paint("  Re-check before quoting:", "yellow"))
        for standard in moving:
            out.line(f"    · {standard.name} — {standard.edition}")
    else:
        out.line(out.paint("  Nothing in the register needs re-checking.", "green"))
    return 0


def cmd_show(lab: Lab, args: argparse.Namespace, out: Printer) -> int:
    try:
        project = lab.project(args.project)
    except KeyError:
        out.line(out.paint(f"unknown project {args.project!r}", "red"))
        out.line("known: " + ", ".join(p.id for p in lab.by_number()))
        return 2

    state = inspect_all(lab.root, (project,))[project.id]
    out.line(out.paint(f"{project.number:02d} · {project.title}", "bold"))
    out.line(out.paint(project.path + "/", "dim"))
    out.line()
    out.line(project.summary)
    out.line()
    out.line(out.paint("The demo that lands", "cyan"))
    out.line(f"  {project.centerpiece}")
    out.line()
    out.line(out.paint("Build phases", "cyan"))
    for phase in state.phases:
        tag = out.paint(" (optional)", "dim") if phase.optional else ""
        out.line(f"  {phase.number:>2}. {phase.title}{tag}")
    out.line()
    out.line(out.paint("Covers", "cyan"))
    for skill_id in project.covers:
        out.line(f"  · {lab.skill(skill_id).label}")
    if project.standards:
        out.line()
        out.line(out.paint("Implements", "cyan"))
        for standard_id in project.standards:
            standard = lab.standard(standard_id)
            out.line(f"  · {standard.name} — {standard.edition}")
    if project.consumes or project.provides:
        out.line()
        out.line(out.paint("Bridges", "cyan"))
        for name in project.provides:
            out.line(f"  provides  {name}")
        for name in project.consumes:
            out.line(f"  consumes  {name}")
    out.line()
    out.line(
        out.paint(
            f"status: {STATUS_LABEL[project.status]} · "
            f"acceptance {state.acceptance_done}/{state.acceptance_total}",
            "dim",
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labctl", description=__doc__.splitlines()[0])
    parser.add_argument(
        "-C",
        "--root",
        type=Path,
        default=None,
        help="repository root (default: nearest ancestor containing lab.toml)",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="show what is specified, building and built")
    sub.add_parser("validate", help="run every repository consistency check")
    sub.add_parser("standards", help="the standards register and what needs re-checking")

    render_parser = sub.add_parser("render", help="regenerate documentation blocks")
    render_parser.add_argument(
        "--check", action="store_true", help="fail if any block is stale instead of rewriting"
    )

    show_parser = sub.add_parser("show", help="everything known about one project")
    show_parser.add_argument("project", help="project id, e.g. can-secoc-demo")

    return parser


COMMANDS = {
    "status": cmd_status,
    "validate": cmd_validate,
    "standards": cmd_standards,
    "render": cmd_render,
    "show": cmd_show,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    out = Printer()
    root = args.root or _find_root(Path.cwd())
    try:
        lab = load(root)
    except ManifestError as exc:
        out.line(out.paint(f"✗ {exc}", "red"))
        return 2

    return COMMANDS[args.command](lab, args, out)


if __name__ == "__main__":
    raise SystemExit(main())
