"""Key revocation: an image that booted a minute ago stops booting."""

from __future__ import annotations

from conftest import Bench
from secboot.hsm import HsmError
from secboot.reasons import ReasonCode


def test_revocation_retires_an_image_that_already_booted(bench: Bench) -> None:
    assert bench.boot().booted

    bench.machine.fuses.revoke_key(1)

    result = bench.boot()
    assert not result.booted
    assert result.reason is ReasonCode.KEY_ID_REVOKED


def test_revocation_survives_a_restart(bench: Bench, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Revocation is a burned fuse, so it is not something a reboot undoes."""
    bench.machine.fuses.revoke_key(1)
    from secboot.fuses import Fuses

    assert Fuses(tmp_path / "ecu" / "fuses.json").is_revoked(1)


def test_revocation_is_checked_before_any_signature_work(bench: Bench) -> None:
    """A revoked key's signature is still mathematically valid, so verifying it
    would prove nothing and cost an HSM operation."""
    bench.machine.fuses.revoke_key(1)
    before = bench.machine.hsm.operations
    bench.boot()
    stage = bench.boot().stages[-1]
    assert ReasonCode.SIGNATURE_INVALID not in stage.verify.checks_run
    assert bench.machine.hsm.operations - before <= 4  # SBL only, twice


def test_a_revoked_slot_will_not_sign(bench: Bench) -> None:
    """Revocation is enforced inside the HSM as well as in fuses. Both, because
    they answer different questions: the fuse stops the device trusting the key,
    the HSM stops the signing infrastructure using it."""
    bench.machine.hsm.revoke(1)
    try:
        bench.machine.hsm.sign(1, b"anything")
    except HsmError as error:
        assert error.reason is ReasonCode.KEY_ID_REVOKED
    else:  # pragma: no cover
        raise AssertionError("a revoked slot signed")


def test_an_out_of_range_key_id_is_treated_as_revoked(bench: Bench) -> None:
    """Fail closed: a key ID with no bit in the bitmap cannot be proven good."""
    assert bench.machine.fuses.is_revoked(64)
    assert bench.machine.fuses.is_revoked(-1)


def test_the_root_key_can_also_be_revoked(bench: Bench) -> None:
    """Revoking the root key bricks the part. That is the correct behaviour and
    the reason revocation in production is a serious decision."""
    bench.machine.fuses.revoke_key(0)
    result = bench.boot()
    assert result.reason is ReasonCode.KEY_ID_REVOKED
    assert result.halted_at == 1
