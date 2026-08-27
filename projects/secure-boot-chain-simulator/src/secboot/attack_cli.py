"""`secboot-attack` — producing malicious images.

A separate binary from `secboot` so the intent is never ambiguous: nothing an
operator runs can generate a hostile image by accident, and a reader looking at
the entry points can see at a glance which half of the project is the attacker.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import attacks, render
from .algo import Algo
from .builder import algo_from_name
from .machine import Machine

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Produce malicious boot images, to prove the verifier catches them.",
)

DEFAULT_STATE = Path("state")
StateOption = Annotated[Path, typer.Option("--state", help="Directory holding the ECU state")]
InOption = Annotated[Path, typer.Option("--in", help="Input image")]
OutOption = Annotated[Path, typer.Option("--out", help="Output image")]


def _write(out: Path, data: bytes, note: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    render.console().print(f"  {out}  [dim]{note}[/dim]")


@app.command()
def corrupt(
    in_path: InOption,
    out: OutOption,
    byte_offset: Annotated[int, typer.Option("--byte-offset")] = 200,
    bit: Annotated[int, typer.Option("--bit")] = 3,
) -> None:
    """Flip one bit. Caught by the payload digest in the signed header."""
    _write(
        out,
        attacks.corrupt(in_path.read_bytes(), byte_offset, bit),
        f"bit {bit} of byte {byte_offset} flipped",
    )


@app.command()
def downgrade(
    in_path: InOption,
    out: OutOption,
    svn: Annotated[int, typer.Option("--svn", help="The older security version")],
    slot: Annotated[int, typer.Option("--slot", help="The legitimate signing slot")] = 1,
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Re-sign an older SVN with the legitimate key. Only the counter refuses it."""
    machine = Machine(state)
    _write(
        out,
        attacks.downgrade(machine.hsm, in_path.read_bytes(), slot=slot, svn=svn),
        f"validly signed, svn lowered to {svn}",
    )


@app.command("strip-sig")
def strip_sig(in_path: InOption, out: OutOption) -> None:
    """Remove the signature and declare it zero-length."""
    _write(out, attacks.strip_signature(in_path.read_bytes()), "signature removed, sig_len=0")


@app.command("swap-stage")
def swap_stage(in_path: InOption, out: OutOption) -> None:
    """Copy a bootloader image so it can be offered as an application image."""
    _write(out, attacks.swap_stage(in_path.read_bytes()), "unmodified — the attack is the context")


@app.command("tamper-payload")
def tamper_payload(
    in_path: InOption,
    out: OutOption,
    payload: Annotated[Path, typer.Option("--payload", help="Replacement payload")],
) -> None:
    """Replace the payload and fix the header digest, leaving the old signature."""
    _write(
        out,
        attacks.tamper_payload(in_path.read_bytes(), payload.read_bytes()),
        "payload replaced, digest recomputed, signature now invalid",
    )


@app.command()
def forge(
    in_path: InOption,
    out: OutOption,
    slot: Annotated[int, typer.Option("--slot", help="The attacker's own slot")] = 0,
    algo: Annotated[str, typer.Option("--algo")] = "ed25519",
    state: Annotated[Path, typer.Option("--state", help="The attacker's keystore")] = Path(
        "state/attacker"
    ),
) -> None:
    """Sign with a key the attacker generated. Valid signature, untrusted key."""
    machine = Machine(state)
    chosen: Algo | None = algo_from_name(algo)
    if chosen is None:
        render.console().print(f"[red]error:[/red] unknown algorithm {algo!r}")
        raise typer.Exit(code=1)
    if not machine.hsm.has_slot(slot):
        machine.hsm.generate(slot, chosen)
    _write(
        out,
        attacks.forge(in_path.read_bytes(), machine.hsm, slot=slot, algo=chosen),
        "signed with an untrusted key",
    )


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
