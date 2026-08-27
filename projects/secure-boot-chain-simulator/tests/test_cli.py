"""The command line, exercised as an operator would use it.

`ACCEPTANCE.md` requires that a fresh clone can be driven end to end with no
manual steps, so the first test here is the whole provisioning-to-boot sequence
in order. The rest cover the failure messages, which are the part an operator
actually reads.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from secboot.attack_cli import app as attack_app
from secboot.cli import app

runner = CliRunner()


def run(*args: str) -> object:
    return runner.invoke(app, list(args))


def attack(*args: str) -> object:
    return runner.invoke(attack_app, list(args))


def provision(tmp_path: Path) -> tuple[str, Path, Path]:
    state = str(tmp_path / "state")
    (tmp_path / "sbl.bin").write_bytes(b"bootloader")
    (tmp_path / "app.bin").write_bytes(b"application")
    sbl = tmp_path / "images" / "sbl.sbi"
    app_image = tmp_path / "images" / "app.sbi"

    assert run("keygen", "--slot", "0", "--algo", "ed25519", "--state", state).exit_code == 0
    assert run("keygen", "--slot", "1", "--algo", "ed25519", "--state", state).exit_code == 0
    assert run("fuses", "init", "--root-slot", "0", "--state", state).exit_code == 0
    assert run("authorize-app-signer", "--slot", "1", "--state", state).exit_code == 0
    assert (
        run(
            "build",
            "--stage",
            "sbl",
            "--svn",
            "3",
            "--slot",
            "0",
            "--payload",
            str(tmp_path / "sbl.bin"),
            "-o",
            str(sbl),
            "--state",
            state,
        ).exit_code
        == 0
    )
    assert (
        run(
            "build",
            "--stage",
            "app",
            "--svn",
            "7",
            "--slot",
            "1",
            "--payload",
            str(tmp_path / "app.bin"),
            "-o",
            str(app_image),
            "--state",
            state,
        ).exit_code
        == 0
    )
    return state, sbl, app_image


def test_the_whole_operator_sequence_works(tmp_path: Path) -> None:
    state, sbl, app_image = provision(tmp_path)

    booted = run("boot", "--sbl", str(sbl), "--app", str(app_image), "--state", state)
    assert booted.exit_code == 0
    assert "application running" in booted.stdout

    assert run("confirm-boot", "--state", state).exit_code == 0
    assert run("fuses", "show", "--state", state).exit_code == 0
    assert run("slots", "--state", state).exit_code == 0
    assert run("policy", "--state", state).exit_code == 0
    assert run("audit", "verify", "--state", state).exit_code == 0
    assert run("inspect", str(app_image)).exit_code == 0


def test_a_rejected_boot_exits_non_zero(tmp_path: Path) -> None:
    """A demo that exits 0 on a rejected boot cannot be used in a pipeline."""
    state, sbl, app_image = provision(tmp_path)
    corrupted = tmp_path / "images" / "app_corrupt.sbi"
    # Offset 130 lands inside the 11-byte payload, just past the 128-byte
    # header, so this reaches the digest check rather than the signature.
    assert (
        attack(
            "corrupt", "--in", str(app_image), "--out", str(corrupted), "--byte-offset", "130"
        ).exit_code
        == 0
    )

    result = run("boot", "--sbl", str(sbl), "--app", str(corrupted), "--state", state)
    assert result.exit_code == 2
    assert "PAYLOAD_DIGEST_MISMATCH" in result.stdout


def test_the_downgrade_attack_through_the_cli(tmp_path: Path) -> None:
    state, sbl, app_image = provision(tmp_path)
    run("boot", "--sbl", str(sbl), "--app", str(app_image), "--state", state)
    run("confirm-boot", "--state", state)

    old = tmp_path / "images" / "app_v3.sbi"
    assert (
        attack(
            "downgrade",
            "--in",
            str(app_image),
            "--out",
            str(old),
            "--svn",
            "3",
            "--slot",
            "1",
            "--state",
            state,
        ).exit_code
        == 0
    )

    result = run("boot", "--sbl", str(sbl), "--app", str(old), "--state", state)
    assert result.exit_code == 2
    assert "ROLLBACK_BLOCKED" in result.stdout


def test_revocation_through_the_cli(tmp_path: Path) -> None:
    state, sbl, app_image = provision(tmp_path)
    assert run("boot", "--sbl", str(sbl), "--app", str(app_image), "--state", state).exit_code == 0
    assert run("revoke", "--key-id", "1", "--state", state).exit_code == 0
    result = run("boot", "--sbl", str(sbl), "--app", str(app_image), "--state", state)
    assert "KEY_ID_REVOKED" in result.stdout


def test_attest_writes_and_checks_a_quote(tmp_path: Path) -> None:
    state, sbl, app_image = provision(tmp_path)
    quote = tmp_path / "quote.json"
    assert (
        run(
            "attest",
            "--sbl",
            str(sbl),
            "--app",
            str(app_image),
            "--out",
            str(quote),
            "--state",
            state,
        ).exit_code
        == 0
    )
    assert json.loads(quote.read_text(encoding="utf-8"))["pcrs"]["pcr2"]

    assert run("attest", "--verify", str(quote), "--state", state).exit_code == 0

    golden = tmp_path / "golden.json"
    payload = json.loads(quote.read_text(encoding="utf-8"))
    payload["pcrs"]["pcr2"] = "00" * 32
    golden.write_text(json.dumps(payload), encoding="utf-8")
    mismatched = run("attest", "--verify", str(quote), "--expected", str(golden), "--state", state)
    assert mismatched.exit_code == 3
    assert "PCR2" in mismatched.stdout


def test_audit_tamper_is_caught_through_the_cli(tmp_path: Path) -> None:
    state, sbl, app_image = provision(tmp_path)
    run("boot", "--sbl", str(sbl), "--app", str(app_image), "--state", state)
    assert (
        run(
            "audit",
            "tamper",
            "--seq",
            "2",
            "--value",
            "TAMPERED",
            "--field",
            "stage",
            "--state",
            state,
        ).exit_code
        == 0
    )
    broken = run("audit", "verify", "--state", state)
    assert broken.exit_code == 4
    assert "seq 2" in broken.stdout
    assert run("audit", "tail", "-n", "5", "--state", state).exit_code == 0


def test_factory_reset_needs_the_flag_and_is_refused_in_production(tmp_path: Path) -> None:
    state, _, _ = provision(tmp_path)
    assert run("fuses", "factory-reset", "--state", state).exit_code == 1
    refused = run("fuses", "factory-reset", "--i-understand", "--state", state)
    assert refused.exit_code == 1
    assert "FACTORY_RESET_REFUSED" in refused.stdout


def test_unhelpful_inputs_get_helpful_errors(tmp_path: Path) -> None:
    state = str(tmp_path / "state")
    unknown_algo = run("keygen", "--algo", "rot13", "--state", state)
    assert unknown_algo.exit_code == 1
    assert "ed25519" in unknown_algo.stdout

    assert run("fuses", "init", "--state", state).exit_code == 1
    assert (
        run(
            "build",
            "--stage",
            "bootrom",
            "--svn",
            "1",
            "--slot",
            "0",
            "--payload",
            "nope.bin",
            "-o",
            "x.sbi",
            "--state",
            state,
        ).exit_code
        == 1
    )
    assert run("attest", "--state", state).exit_code == 1
    assert run("demo", "--scenario", "nonsense").exit_code == 1


def test_algos_reports_backend_availability() -> None:
    result = run("algos")
    assert result.exit_code == 0
    assert "ml-dsa-65" in result.stdout
    assert "available" in result.stdout


def test_demo_runs_one_scenario_through_the_cli() -> None:
    result = run("demo", "--scenario", "downgrade", "--no-color", "--width", "80")
    assert result.exit_code == 0
    assert "ROLLBACK_BLOCKED" in result.stdout


def test_every_attack_subcommand_produces_an_image(tmp_path: Path) -> None:
    state, sbl, app_image = provision(tmp_path)
    out = tmp_path / "images"
    payload = tmp_path / "evil.bin"
    payload.write_bytes(b"evil" * 4)

    assert attack("strip-sig", "--in", str(app_image), "--out", str(out / "a.sbi")).exit_code == 0
    assert attack("swap-stage", "--in", str(sbl), "--out", str(out / "b.sbi")).exit_code == 0
    assert (
        attack(
            "tamper-payload",
            "--in",
            str(app_image),
            "--out",
            str(out / "c.sbi"),
            "--payload",
            str(payload),
        ).exit_code
        == 0
    )
    assert (
        attack(
            "forge",
            "--in",
            str(app_image),
            "--out",
            str(out / "d.sbi"),
            "--state",
            str(tmp_path / "attacker"),
        ).exit_code
        == 0
    )
    assert (
        attack(
            "forge",
            "--in",
            str(app_image),
            "--out",
            str(out / "e.sbi"),
            "--algo",
            "rot13",
            "--state",
            str(tmp_path / "attacker"),
        ).exit_code
        == 1
    )

    for name, expected in (
        ("a.sbi", "SIGNATURE_INVALID"),
        ("b.sbi", "WRONG_STAGE_ID"),
        ("c.sbi", "SIGNATURE_INVALID"),
        ("d.sbi", "KEY_NOT_AUTHORIZED_FOR_STAGE"),
    ):
        result = run("boot", "--sbl", str(sbl), "--app", str(out / name), "--state", state)
        assert expected in result.stdout, name


def test_inspect_refuses_a_file_that_is_not_an_image(tmp_path: Path) -> None:
    """Even the diagnostic command returns a reason code rather than a
    traceback — the file it is pointed at is attacker-controlled too."""
    stub = tmp_path / "not-an-image.bin"
    stub.write_bytes(b"nope")
    result = run("inspect", str(stub))
    assert result.exit_code == 1
    assert "IMAGE_TOO_SHORT" in result.stdout
