"""The operator-facing command line.

Split into groups that mirror the real roles: `keygen` and `revoke` belong to
whoever runs the signing infrastructure, `fuses` to production, `build` to the
release pipeline, and `boot`, `attest` and `audit` to the device and whoever
investigates it. The attacker tooling is a separate binary — `secboot-attack` —
so that no command in here can produce a malicious image by accident.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from . import image, render
from .algo import SPECS, Algo, available
from .builder import algo_from_name, sign_and_build
from .fuses import Lifecycle
from .hsm import HsmError
from .image import STAGE_APP, STAGE_SBL
from .machine import Machine
from .policy import Policy
from .reasons import EXPLANATION, ReasonCode

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A simulated automotive secure boot chain. Education and demonstration only.",
)
fuses_app = typer.Typer(no_args_is_help=True, help="OTP fuses and monotonic counters")
audit_app = typer.Typer(no_args_is_help=True, help="The tamper-evident audit log")
app.add_typer(fuses_app, name="fuses")
app.add_typer(audit_app, name="audit")

DEFAULT_STATE = Path("state")

StateOption = Annotated[Path, typer.Option("--state", help="Directory holding this ECU's state")]
LatencyOption = Annotated[
    float, typer.Option("--hsm-latency-ms", help="Simulated per-operation HSM latency")
]


def _machine(state: Path, *, latency: float = 0.0, allow_insecure: bool = False) -> Machine:
    machine = Machine(state, hsm_latency_ms=latency)
    if allow_insecure:
        machine.policy.allow_insecure = True
    return machine


def _console() -> Console:
    return render.console()


def _fail(message: str, reason: ReasonCode | None = None) -> None:
    con = _console()
    con.print(f"[red]error:[/red] {message}")
    if reason is not None:
        con.print(f"  [dim]{reason}[/dim] — {EXPLANATION.get(reason, '')}")
    raise typer.Exit(code=1)


# --- keys -------------------------------------------------------------------


@app.command()
def keygen(
    slot: Annotated[int, typer.Option("--slot", help="HSM key slot")] = 0,
    algo: Annotated[str, typer.Option("--algo", help="Signature algorithm")] = "ecdsa-p256",
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Create a key pair inside the simulated HSM."""
    chosen = algo_from_name(algo)
    if chosen is None:
        _fail(f"unknown algorithm {algo!r}; try: {', '.join(s.cli_name for s in SPECS.values())}")
        return
    machine = _machine(state)
    try:
        info = machine.hsm.generate(slot, chosen)
    except HsmError as error:
        _fail(str(error), error.reason)
        return
    con = _console()
    con.print(f"  slot {info.slot}: [bold]{info.algo_name}[/bold] created, exportable=False")
    con.print(f"  [dim]public key:[/dim] {info.public_key.hex()[:48]}…")


@app.command()
def slots(state: StateOption = DEFAULT_STATE) -> None:
    """List the HSM's key slots. Note that no column holds a private key."""
    render.slot_table(_console(), _machine(state).hsm.slots())


@app.command()
def algos() -> None:
    """The algorithm table, and whether the installed backend can run each one."""
    con = _console()
    for algo, spec in SPECS.items():
        mark = "[green]available[/green]" if available(algo) else "[yellow]unavailable[/yellow]"
        con.print(f"  {int(algo)}  {spec.cli_name:<12} {mark}  [dim]{spec.description}[/dim]")
    con.print()
    con.print("  [dim]Unavailable usually means the backend is OpenSSL-backed; ML-DSA needs[/dim]")
    con.print("  [dim]AWS-LC or BoringSSL. See docs/post-quantum.md.[/dim]")


@app.command()
def revoke(
    key_id: Annotated[int, typer.Option("--key-id", help="Key ID to revoke")],
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Burn a key's revocation fuse. Irreversible, on purpose."""
    machine = _machine(state)
    outcome = machine.fuses.revoke_key(key_id)
    if machine.hsm.has_slot(key_id):
        machine.hsm.revoke(key_id)
    machine.audit.append(
        stage="ROM",
        event="REVOKE",
        decision="INFO",
        reason=outcome.reason,
        detail={"key_id": key_id},
        severity="CRITICAL",
    )
    _console().print(f"  key ID {key_id}: [red]revoked[/red]  ({outcome.reason})")


@app.command("authorize-app-signer")
def authorize_app_signer(
    slot: Annotated[int, typer.Option("--slot", help="HSM slot holding the app signing key")],
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Add a key to the bootloader's application-signer allowlist.

    Stage 2 authority is delegated rather than anchored in OTP, which is what
    lets an application signing key be rotated without burning a fuse.
    """
    machine = _machine(state)
    machine.policy.authorize_app_signer(machine.hsm.public_key(slot))
    machine.save_policy()
    _console().print(f"  slot {slot} authorized to sign application images")


# --- fuses ------------------------------------------------------------------


@fuses_app.command("init")
def fuses_init(
    root_slot: Annotated[int, typer.Option("--root-slot", help="Slot holding the root key")] = 0,
    lifecycle: Annotated[str, typer.Option("--lifecycle")] = "PRODUCTION",
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Provision a virgin part: burn the root key hash and enable secure boot."""
    import hashlib

    machine = _machine(state)
    if not machine.hsm.has_slot(root_slot):
        _fail(f"no key in slot {root_slot} — run `secboot keygen --slot {root_slot}` first")
        return
    digest = hashlib.sha256(machine.hsm.public_key(root_slot)).hexdigest()
    outcome = machine.fuses.burn_root_key_hash(digest)
    if not outcome.ok:
        _fail("root_key_hash is already burned; this fuse is write-once", outcome.reason)
        return
    machine.fuses.enable_secure_boot()
    for step in (Lifecycle.DEVELOPMENT, Lifecycle(lifecycle)):
        machine.fuses.set_lifecycle(step)
    machine.save_policy()
    con = _console()
    con.print(f"  root_key_hash burned: [bold]{digest[:32]}…[/bold]")
    con.print(f"  secure boot enabled, lifecycle {machine.fuses.lifecycle}")


@fuses_app.command("show")
def fuses_show(state: StateOption = DEFAULT_STATE) -> None:
    """The fuse and counter state."""
    render.fuse_table(_console(), _machine(state).fuses)


@fuses_app.command("factory-reset")
def fuses_factory_reset(
    understood: Annotated[
        bool, typer.Option("--i-understand", help="Required. Refused in PRODUCTION.")
    ] = False,
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Wipe the fuses so the demo can be re-run. No real part has this command."""
    if not understood:
        _fail("pass --i-understand; this exists only so the demo can be re-run")
    machine = _machine(state)
    outcome = machine.fuses.factory_reset()
    machine.audit.append(
        stage="ROM",
        event="FACTORY_RESET",
        decision="INFO" if outcome.ok else "REJECT",
        reason=outcome.reason,
        detail=dict(outcome.detail),
        severity="CRITICAL",
    )
    if not outcome.ok:
        _fail("refused", outcome.reason)
    _console().print("  fuses cleared")


# --- images -----------------------------------------------------------------


@app.command()
def build(
    stage: Annotated[str, typer.Option("--stage", help="sbl or app")],
    svn: Annotated[int, typer.Option("--svn", help="Security version number")],
    slot: Annotated[int, typer.Option("--slot", help="HSM slot to sign with")],
    payload: Annotated[Path, typer.Option("--payload", help="Payload file")],
    out: Annotated[Path, typer.Option("-o", "--out", help="Output .sbi path")],
    image_version: Annotated[int, typer.Option("--image-version")] = 0,
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Sign and package a boot image."""
    stage_id = {"sbl": STAGE_SBL, "app": STAGE_APP}.get(stage.lower())
    if stage_id is None:
        _fail(f"unknown stage {stage!r}; expected sbl or app")
        return
    if not payload.exists():
        _fail(f"no payload file at {payload}")
        return
    machine = _machine(state)
    try:
        image = sign_and_build(
            machine.hsm,
            slot=slot,
            stage_id=stage_id,
            svn=svn,
            payload=payload.read_bytes(),
            image_version=image_version,
        )
    except HsmError as error:
        _fail(str(error), error.reason)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(image)
    _console().print(f"  {out}  [dim]{len(image)} bytes, stage={stage}, svn={svn}[/dim]")


@app.command()
def boot(
    sbl: Annotated[Path, typer.Option("--sbl", help="Bootloader image")],
    app_image: Annotated[Path, typer.Option("--app", help="Application image")],
    allow_insecure: Annotated[
        bool, typer.Option("--allow-insecure", help="Boot a part with the fuse unburned")
    ] = False,
    hsm_latency_ms: LatencyOption = 0.0,
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Run the boot chain against two images."""
    machine = _machine(state, latency=hsm_latency_ms, allow_insecure=allow_insecure)
    result = machine.boot(sbl.read_bytes(), app_image.read_bytes())
    con = _console()
    con.print()
    render.boot_tree(con, result)
    con.print()
    con.print(f"  [dim]HSM operations:[/dim] {result.hsm_operations}")
    if not result.booted:
        raise typer.Exit(code=2)


@app.command("confirm-boot")
def confirm_boot(state: StateOption = DEFAULT_STATE) -> None:
    """Commit staged SVN advances. Models a health check reporting success."""
    machine = _machine(state)
    con = _console()
    for reason in machine.confirm_boot():
        con.print(f"  {reason} — {EXPLANATION.get(reason, '')}")
    render.fuse_table(con, machine.fuses)


# --- attestation ------------------------------------------------------------


@app.command()
def attest(
    nonce: Annotated[str, typer.Option("--nonce", help="Challenger-supplied freshness value")] = (
        "0" * 32
    ),
    out: Annotated[Path | None, typer.Option("--out", help="Write the quote here")] = None,
    verify: Annotated[Path | None, typer.Option("--verify", help="A quote to check")] = None,
    expected: Annotated[Path | None, typer.Option("--expected", help="Golden PCR set")] = None,
    sbl: Annotated[Path | None, typer.Option("--sbl")] = None,
    app_image: Annotated[Path | None, typer.Option("--app")] = None,
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Produce or check an attestation quote over the PCR bank.

    Producing one needs a boot to measure, so pass the same images `boot` was
    given; the PCR bank is reset at every power-on and is not persisted, exactly
    as on a real part.
    """
    machine = _machine(state)
    if verify is not None:
        quote = json.loads(verify.read_text(encoding="utf-8"))
        golden = (
            json.loads(expected.read_text(encoding="utf-8"))
            if expected is not None
            else quote["pcrs"]
        )
        golden = golden.get("pcrs", golden)
        ok, description = machine.verify_quote(quote, golden)
        con = _console()
        con.print(f"  signature and PCRs: {'[green]match[/green]' if ok else '[red]differ[/red]'}")
        con.print(f"  [dim]{description}[/dim]")
        raise typer.Exit(code=0 if ok else 3)

    if sbl is None or app_image is None:
        _fail("pass --sbl and --app so there is a boot to attest to")
        return
    machine.boot(sbl.read_bytes(), app_image.read_bytes())
    quote = machine.attest(nonce)
    con = _console()
    render.quote_table(con, quote)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(quote, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        con.print(f"  [dim]quote written to {out}[/dim]")


# --- audit ------------------------------------------------------------------


@audit_app.command("verify")
def audit_verify(state: StateOption = DEFAULT_STATE) -> None:
    """Walk the hash chain and name the first record that does not fit."""
    status = _machine(state).audit.verify()
    con = _console()
    if status.ok:
        con.print(f"  [green]chain intact[/green] — {status.records} records")
        return
    con.print(f"  [red]chain broken at seq {status.broken_seq}[/red]")
    con.print(f"  [dim]{status.detail}[/dim]")
    raise typer.Exit(code=4)


@audit_app.command("tail")
def audit_tail(
    count: Annotated[int, typer.Option("-n", "--count")] = 20,
    state: StateOption = DEFAULT_STATE,
) -> None:
    """The most recent events."""
    render.audit_rows(_console(), _machine(state).audit.tail(count))


@audit_app.command("tamper")
def audit_tamper(
    seq: Annotated[int, typer.Option("--seq", help="Sequence number to edit")],
    field: Annotated[str, typer.Option("--field")] = "decision",
    value: Annotated[str, typer.Option("--value")] = "ACCEPT",
    state: StateOption = DEFAULT_STATE,
) -> None:
    """Edit a record in place, so `audit verify` can be shown catching it."""
    if not _machine(state).audit.tamper(seq, field, value):
        _fail(f"no record with seq {seq}")
    _console().print(f"  record {seq} edited: {field} = {value!r}")


# --- policy and demo --------------------------------------------------------


@app.command("policy")
def policy_show(state: StateOption = DEFAULT_STATE) -> None:
    """What this machine will accept."""
    policy: Policy = _machine(state).policy
    con = _console()
    con.print("  allowed algorithms:")
    for algo in sorted(policy.allowed_algos, key=int):
        con.print(f"    [bold]{SPECS[Algo(algo)].cli_name}[/bold]  {SPECS[Algo(algo)].description}")
    con.print(f"  app signer allowlist: {len(policy.app_signer_hashes)} key(s)")
    con.print(f"  allow_insecure: {policy.allow_insecure}")
    con.print(f"  require_boot_confirmation: {policy.require_boot_confirmation}")


@app.command()
def demo(
    scenario: Annotated[str, typer.Option("--scenario", help="all, or one scenario key")] = "all",
    seed: Annotated[int, typer.Option("--seed", help="Makes the run reproducible")] = 1337,
    state: StateOption = Path("state/demo"),
    no_color: Annotated[bool, typer.Option("--no-color")] = False,
    width: Annotated[int, typer.Option("--width")] = 96,
) -> None:
    """Run the attack scenarios end to end."""
    from . import demo as demo_module  # noqa: PLC0415 - keeps `--help` fast

    if scenario != "all" and scenario not in demo_module.BY_KEY:
        _fail(f"unknown scenario {scenario!r}; try: all, {', '.join(demo_module.BY_KEY)}")
    import shutil
    import tempfile

    # A fresh part per run. The demo provisions from virgin silicon, and a part
    # that has already been through it would fail on the write-once fuses.
    root = Path(tempfile.mkdtemp(prefix="secboot-demo-"))
    try:
        con = render.console(no_color=no_color, width=width)
        matched = demo_module.run(con, root, seed=seed, only=scenario)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        _ = state
    if not matched:
        raise typer.Exit(code=5)


@app.command()
def inspect(
    path: Annotated[Path, typer.Argument(metavar="IMAGE", help="An .sbi file")],
) -> None:
    """Print a container's header without verifying anything."""
    raw = path.read_bytes()
    if len(raw) < image.HEADER_LEN:
        _fail(
            f"{path} is {len(raw)} bytes; a header is {image.HEADER_LEN}",
            ReasonCode.IMAGE_TOO_SHORT,
        )
    header = image.unpack_header(raw)
    con = _console()
    spec = SPECS.get(Algo(header.algo_id)) if header.algo_id in {int(a) for a in Algo} else None
    con.print(f"  magic            {header.magic!r}")
    con.print(f"  stage            {header.stage_name} ({header.stage_id})")
    con.print(f"  svn              {header.svn}")
    con.print(f"  image_version    0x{header.image_version:08x}  [dim]informational only[/dim]")
    con.print(f"  payload_len      {header.payload_len}")
    con.print(f"  algo             {spec.cli_name if spec else 'unknown'} ({header.algo_id})")
    con.print(f"  key_id           {header.key_id}")
    con.print(f"  payload_sha256   {header.payload_sha256.hex()[:32]}…")
    con.print(f"  signer_pubkey    {header.signer_pubkey_sha256.hex()[:32]}…")
    con.print(f"  sig_len          {header.sig_len}")


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        sys.exit(130)


if __name__ == "__main__":  # pragma: no cover
    main()
