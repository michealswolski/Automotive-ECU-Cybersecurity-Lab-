"""Terminal output.

An engineer demoing to another engineer, not a product page. Every rejection
prints three things: the reason code, the expected and actual values that
produced it, and the one-line explanation of the control that fired. A reader
should be able to follow the chain without having read the source.

All output goes through a caller-supplied `Console`, which is what lets the
golden test capture the demo with colour disabled and a fixed width.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .fuses import Fuses
from .hsm import SlotInfo
from .machine import BootResult, StageResult
from .reasons import EXPLANATION, ReasonCode

PASS = "[green]PASS[/green]"
FAIL = "[red]FAIL[/red]"


def console(*, no_color: bool = False, width: int | None = None) -> Console:
    return Console(no_color=no_color, width=width, highlight=False, soft_wrap=False)


def rule(con: Console, title: str) -> None:
    con.rule(f"[bold]{title}[/bold]")


def boot_tree(con: Console, result: BootResult) -> None:
    """The chain, one line per stage, with the reason a stage failed."""
    con.print("  [dim]power on[/dim]")
    con.print("  [dim]│[/dim]")
    con.print("  [dim]├─[/dim] BootROM [dim](immutable, trusted by axiom)[/dim]")
    for index, stage in enumerate(result.stages):
        last = index == len(result.stages) - 1
        elbow = "└─" if last and not result.booted else "├─"
        glyph = "[green]✓[/green]" if stage.verify.ok and stage.loaded else "[red]✗[/red]"
        con.print(f"  [dim]{elbow}[/dim] {glyph} {stage.stage_name}  {_stage_summary(stage)}")
        if not (stage.verify.ok and stage.loaded):
            _reject_detail(con, stage)
    if result.booted:
        con.print("  [dim]└─[/dim] [green]✓[/green] application running")
    else:
        con.print("  [dim]   [/dim] [red]control was never transferred[/red]")


def _stage_summary(stage: StageResult) -> str:
    if not stage.verify.ok:
        return f"[red]{stage.verify.reason}[/red]"
    parts = [f"svn={stage.verify.detail.get('svn')}", f"algo={stage.verify.detail.get('algo')}"]
    if stage.measurement:
        parts.append(f"measured={stage.measurement[:12]}…")
    if stage.staged_svn is not None:
        parts.append(f"[yellow]svn advance staged → {stage.staged_svn}[/yellow]")
    return "[dim]" + "  ".join(parts) + "[/dim]"


def _reject_detail(con: Console, stage: StageResult) -> None:
    reason = stage.verify.reason
    con.print(f"       [dim]why:[/dim] {EXPLANATION.get(reason, '')}")
    for key, value in sorted(stage.verify.detail.items()):
        con.print(f"       [dim]{key}:[/dim] {value}")
    con.print(f"       [dim]checks that ran:[/dim] {len(stage.verify.checks_run)} of 16")


def reason_line(con: Console, reason: ReasonCode) -> None:
    con.print(f"  [bold]{reason}[/bold] — {EXPLANATION.get(reason, '')}")


def fuse_table(con: Console, fuses: Fuses) -> None:
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("fuse / counter")
    table.add_column("value")
    table.add_column("note", style="dim")
    root = fuses.root_key_hash or "[dim]unburned[/dim]"
    table.add_row("root_key_hash", root[:32] + ("…" if fuses.root_key_hash else ""), "write-once")
    table.add_row("secure_boot_enable", str(fuses.secure_boot_enable), "write-once")
    table.add_row("lifecycle", str(fuses.lifecycle), "forward only")
    table.add_row("revoked_key_ids", f"0x{fuses.revoked_key_ids:016x}", "one bit per key ID")
    for name, counter in fuses.counters.items():
        pending = "" if counter.pending is None else f"  pending → {counter.pending}"
        table.add_row(
            name,
            f"{counter.value}{pending}",
            f"{counter.substrate}, {counter.headroom()} advances left",
        )
    con.print(table)


def slot_table(con: Console, slots: list[SlotInfo]) -> None:
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    for column in ("slot", "algorithm", "usage", "exportable", "revoked", "public key"):
        table.add_column(column)
    for info in slots:
        table.add_row(
            str(info.slot),
            info.algo_name,
            info.usage.name or "NONE",
            Text("False", style="green"),
            Text("yes", style="red") if info.revoked else "no",
            info.public_key.hex()[:24] + "…",
        )
    con.print(table)


def quote_table(con: Console, quote: dict[str, Any]) -> None:
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("register")
    table.add_column("value")
    table.add_column("records", style="dim")
    for name, value in quote["pcrs"].items():
        table.add_row(name, value[:32] + "…", quote["purposes"][name])
    con.print(table)


def audit_rows(con: Console, records: list[dict[str, Any]]) -> None:
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    for column in ("seq", "stage", "event", "decision", "reason"):
        table.add_column(column)
    for record in records:
        decision = str(record.get("decision"))
        style = {"REJECT": "red", "HALT": "red", "ACCEPT": "green"}.get(decision, "")
        table.add_row(
            str(record.get("seq")),
            str(record.get("stage")),
            str(record.get("event")),
            Text(decision, style=style),
            str(record.get("reason") or ""),
        )
    con.print(table)
