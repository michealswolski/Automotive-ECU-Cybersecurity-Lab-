"""The eight scenarios.

Each one performs a real attack against a freshly provisioned ECU and shows
which control caught it. They are ordered so the story builds: a clean boot
first, then attacks that a signature check would catch, then the two that it
would not — the rollback and the glitch.

Determinism. With a seed, every key in the demo is derived from it. An Ed25519
private key *is* its 32 seed bytes, so this derives real keys rather than faking
anything, and the whole run — measurements, PCRs, audit hashes — is byte
reproducible. That is what lets `tests/test_demo_golden.py` diff the output.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from . import attacks, render
from .algo import Algo
from .builder import sign_and_build
from .fuses import Lifecycle
from .machine import Fault, Machine
from .policy import Policy
from .reasons import EXPLANATION, ReasonCode

DEFAULT_SEED = 1337
SBL_SVN = 3
APP_SVN = 7
#: Payload bytes stand in for compiled code. The chain never executes them —
#: they are opaque blobs, exactly as SPEC section 1 scopes it.
SBL_PAYLOAD = b"<simulated secondary bootloader>" * 8
APP_PAYLOAD = b"<simulated application image>" * 16

#: A fixed timestamp so the audit log's hashes are reproducible under a seed.
FIXED_TS = "2026-01-01T00:00:00.000Z"


def _derive(seed: int, label: str) -> bytes:
    return hashlib.sha256(f"secboot-demo/{seed}/{label}".encode()).digest()


@dataclass
class Bench:
    """A provisioned ECU plus the images and keys the scenario needs."""

    machine: Machine
    sbl: bytes
    app: bytes
    attacker: Machine


def provision(root: Path, seed: int, *, label: str) -> Bench:
    """Take a virgin part through provisioning, then build the golden images.

    This is the production ceremony in miniature: generate (here, inject) the
    root key, burn its hash, enable secure boot, delegate application signing
    authority to a second key, and move the part to PRODUCTION so the
    factory-reset escape hatch is closed.
    """
    state = root / label
    policy = Policy(
        allowed_algos={Algo.ED25519, Algo.ECDSA_P384_SHA384},
        require_boot_confirmation=True,
    )
    machine = Machine(state / "ecu", policy=policy, clock=lambda: FIXED_TS)
    machine.hsm.import_private(0, Algo.ED25519, _derive(seed, "root"))
    machine.hsm.import_private(1, Algo.ED25519, _derive(seed, "app"))
    machine.fuses.burn_root_key_hash(hashlib.sha256(machine.hsm.public_key(0)).hexdigest())
    machine.fuses.enable_secure_boot()
    machine.fuses.set_lifecycle(Lifecycle.DEVELOPMENT)
    machine.fuses.set_lifecycle(Lifecycle.PRODUCTION)
    machine.policy.authorize_app_signer(machine.hsm.public_key(1))
    machine.save_policy()

    attacker = Machine(state / "attacker", clock=lambda: FIXED_TS)
    attacker.hsm.import_private(0, Algo.ED25519, _derive(seed, "attacker"))

    sbl = sign_and_build(
        machine.hsm, slot=0, stage_id=1, svn=SBL_SVN, payload=SBL_PAYLOAD, image_version=0x00010000
    )
    app = sign_and_build(
        machine.hsm, slot=1, stage_id=2, svn=APP_SVN, payload=APP_PAYLOAD, image_version=0x00070000
    )
    return Bench(machine=machine, sbl=sbl, app=app, attacker=attacker)


@dataclass
class Scenario:
    key: str
    title: str
    attack: str
    expected: ReasonCode
    run: Callable[[Console, Bench], ReasonCode]


def note(con: Console, *lines: str) -> None:
    """Dim narration. One markup span per line, because rich tags do not span
    separate `print` calls."""
    for line in lines:
        con.print(f"  [dim]{line}[/dim]")


def _boot_and_report(con: Console, bench: Bench, sbl: bytes, app: bytes) -> ReasonCode:
    result = bench.machine.boot(sbl, app)
    render.boot_tree(con, result)
    return result.reason if not result.booted else ReasonCode.ACCEPTED


# --- the scenarios ----------------------------------------------------------


def _happy(con: Console, bench: Bench) -> ReasonCode:
    outcome = _boot_and_report(con, bench, bench.sbl, bench.app)
    con.print()
    note(
        con,
        "The SVN advance is staged, not burned. Until the application",
        "reports a healthy start, the previous image is still bootable.",
    )
    before = bench.machine.fuses.read("svn_app")
    note(con, f"counters before confirm: svn_app={before}")
    bench.machine.confirm_boot()
    note(con, f"counters after  confirm: svn_app={bench.machine.fuses.read('svn_app')}")
    return outcome


def _corrupt(con: Console, bench: Bench) -> ReasonCode:
    # Offset 200 lands inside the application payload, past the 128-byte header.
    corrupted = attacks.corrupt(bench.app, 200, 3)
    return _boot_and_report(con, bench, bench.sbl, corrupted)


def _downgrade(con: Console, bench: Bench) -> ReasonCode:
    bench.machine.boot(bench.sbl, bench.app)
    bench.machine.confirm_boot()
    old = attacks.downgrade(bench.machine.hsm, bench.app, slot=1, svn=3)
    note(
        con,
        "The image below is signed by the legitimate application key.",
        "Every signature check passes. Only freshness fails.",
    )
    con.print()
    return _boot_and_report(con, bench, bench.sbl, old)


def _forged(con: Console, bench: Bench) -> ReasonCode:
    forged = attacks.forge(bench.app, bench.attacker.hsm, slot=0)
    return _boot_and_report(con, bench, bench.sbl, forged)


def _revoked(con: Console, bench: Bench) -> ReasonCode:
    first = bench.machine.boot(bench.sbl, bench.app)
    con.print(f"  [dim]a moment ago:[/dim] booted={first.booted}")
    bench.machine.confirm_boot()
    bench.machine.fuses.revoke_key(1)
    bench.machine.hsm.revoke(1)
    con.print("  [dim]the application signing key is reported compromised and revoked[/dim]")
    con.print()
    return _boot_and_report(con, bench, bench.sbl, bench.app)


def _stage_confusion(con: Console, bench: Bench) -> ReasonCode:
    fake_app = attacks.swap_stage(bench.sbl)
    note(
        con,
        "Nothing is modified. The bytes are a genuine, correctly signed",
        "bootloader image — presented where the application belongs.",
    )
    con.print()
    return _boot_and_report(con, bench, bench.sbl, fake_app)


def _algo_downgrade(con: Console, bench: Bench) -> ReasonCode:
    bench.attacker.hsm.generate(2, Algo.ECDSA_P256_SHA256)
    weaker = attacks.forge(bench.app, bench.attacker.hsm, slot=2, algo=Algo.ECDSA_P256_SHA256)
    note(
        con,
        "This machine's policy allows Ed25519 and ECDSA P-384 — the CNSA 2.0",
        "classical floor. The image asks for P-256, which the verifier can",
        "perform and refuses to.",
    )
    con.print()
    return _boot_and_report(con, bench, bench.sbl, weaker)


def _audit_tamper(con: Console, bench: Bench) -> ReasonCode:
    bench.machine.boot(bench.sbl, attacks.corrupt(bench.app, 200, 3))
    log = bench.machine.audit
    before = log.verify()
    con.print(f"  [dim]chain before:[/dim] {before.records} records, ok={before.ok}")
    target = next(r["seq"] for r in log.records() if r["decision"] == "REJECT")
    log.tamper(target, "decision", "ACCEPT")
    con.print(f"  [dim]an attacker edits record {target} to say the boot was clean[/dim]")
    after = log.verify()
    con.print(f"  [dim]chain after: [/dim] ok={after.ok}, broken at seq={after.broken_seq}")
    con.print(f"  [dim]{after.detail}[/dim]")
    return after.reason


def _glitch(con: Console, bench: Bench) -> ReasonCode:
    """Not one of the eight, but the most instructive run in the project."""
    bench.machine.boot(bench.sbl, bench.app)
    golden_pcrs = bench.machine.pcr.as_dict()
    bench.machine.confirm_boot()

    # The payload is replaced and the header digest recomputed, so every check
    # up to the signature passes. That leaves exactly one control standing --
    # which is the one the glitch lands on.
    tampered = attacks.tamper_payload(bench.app, b"<attacker payload>" * 26)
    bench.machine.fault = Fault(force_signature_pass=True)
    result = bench.machine.boot(bench.sbl, tampered)
    bench.machine.fault = None
    render.boot_tree(con, result)
    con.print()
    note(
        con,
        "Verified boot was defeated: the compare was glitched and the",
        "forged image ran. Measured boot still recorded what actually ran.",
    )
    quote = bench.machine.attest("demo-nonce")
    ok, description = bench.machine.verify_quote(quote, golden_pcrs)
    con.print(f"  [dim]attestation vs golden:[/dim] match={ok} — {description}")
    return ReasonCode.ATTESTATION_MISMATCH if not ok else ReasonCode.ACCEPTED


SCENARIOS: list[Scenario] = [
    Scenario("happy", "Clean boot", "none — the reference run", ReasonCode.ACCEPTED, _happy),
    Scenario(
        "corrupt",
        "One bit flipped in the application payload",
        "flash write access, no signing key",
        ReasonCode.PAYLOAD_DIGEST_MISMATCH,
        _corrupt,
    ),
    Scenario(
        "downgrade",
        "An older release, re-signed with the legitimate key",
        "an old signed release plus install access",
        ReasonCode.ROLLBACK_BLOCKED,
        _downgrade,
    ),
    Scenario(
        "forged",
        "Signed with the attacker's own key",
        "the attacker's signing infrastructure",
        ReasonCode.KEY_NOT_AUTHORIZED_FOR_STAGE,
        _forged,
    ),
    Scenario(
        "revoked",
        "The signing key is compromised, then revoked",
        "key theft, followed by the OEM's response",
        ReasonCode.KEY_ID_REVOKED,
        _revoked,
    ),
    Scenario(
        "stage-confusion",
        "A bootloader image presented as the application",
        "install access, no modification at all",
        ReasonCode.WRONG_STAGE_ID,
        _stage_confusion,
    ),
    Scenario(
        "algo-downgrade",
        "An algorithm below the machine's policy floor",
        "a signing key of the attacker's choosing",
        ReasonCode.ALGO_NOT_PERMITTED,
        _algo_downgrade,
    ),
    Scenario(
        "audit-tamper",
        "The audit log edited after the fact",
        "write access to the log",
        ReasonCode.AUDIT_CHAIN_BROKEN,
        _audit_tamper,
    ),
    Scenario(
        "glitch",
        "The signature compare is glitched, and measured boot catches it",
        "physical access and fault injection",
        ReasonCode.ATTESTATION_MISMATCH,
        _glitch,
    ),
]

BY_KEY = {scenario.key: scenario for scenario in SCENARIOS}


def run(
    con: Console,
    root: Path,
    *,
    seed: int = DEFAULT_SEED,
    only: str = "all",
) -> bool:
    """Run the selected scenarios. Returns True when every outcome matched."""
    chosen = SCENARIOS if only == "all" else [BY_KEY[only]]
    all_matched = True

    con.print()
    con.rule("[bold]Secure Boot Chain Simulator[/bold]")
    con.print()
    con.print("  A simulation, for education and demonstration. It models the controls;")
    con.print("  it does not protect anything. Do not put it near a real device.")
    con.print()
    note(
        con,
        f"seed {seed} — every key, measurement and audit hash below is",
        "derived from it, so this output is byte-for-byte reproducible.",
    )
    con.print()

    for index, scenario in enumerate(chosen, start=1):
        con.print()
        con.rule(f"[bold]{index}. {scenario.title}[/bold]")
        con.print()
        con.print(f"  [dim]attacker capability:[/dim] {scenario.attack}")
        con.print(f"  [dim]control under test: [/dim] {EXPLANATION[scenario.expected]}")
        con.print()
        bench = provision(root, seed, label=scenario.key)
        outcome = scenario.run(con, bench)
        matched = outcome is scenario.expected
        all_matched = all_matched and matched
        con.print()
        glyph = "[green]as expected[/green]" if matched else "[red]UNEXPECTED[/red]"
        con.print(f"  outcome: [bold]{outcome}[/bold]  ({glyph}, expected {scenario.expected})")

    con.print()
    con.rule("[bold]Summary[/bold]")
    con.print()
    for scenario in chosen:
        con.print(f"  {scenario.expected:<32} {scenario.title}")
    con.print()
    note(
        con,
        "Two of these are the reason the project exists: the downgrade, which",
        "every signature check passes, and the glitch, which no signature",
        "check can catch at all.",
    )
    con.print()
    return all_matched
