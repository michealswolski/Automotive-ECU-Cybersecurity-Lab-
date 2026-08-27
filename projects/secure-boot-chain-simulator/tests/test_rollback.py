"""Anti-rollback: the control a signature check can never provide.

The single most important test in this project is
`test_a_validly_signed_older_image_is_refused`. Everything else here defends the
counter that makes it possible.
"""

from __future__ import annotations

import pytest

from conftest import APP_PAYLOAD, APP_SVN, Bench
from secboot import attacks
from secboot.fuses import COUNTER_MAX, EFUSE_BITS, Fuses, Lifecycle, Substrate
from secboot.reasons import ReasonCode


def test_a_validly_signed_older_image_is_refused(bench: Bench) -> None:
    """Signed by the legitimate key. Every signature check passes. Refused."""
    bench.boot()
    bench.machine.confirm_boot()
    old = attacks.downgrade(bench.machine.hsm, bench.app, slot=1, svn=3)

    result = bench.boot(app=old)

    assert not result.booted
    assert result.reason is ReasonCode.ROLLBACK_BLOCKED
    failing = result.failing
    assert failing is not None
    assert failing.verify.detail == {"image_svn": 3, "counter_svn": APP_SVN, "counter": "svn_app"}


def test_advance_cannot_lower_a_counter(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """There is no public path that writes a counter downwards. The absence of
    a setter is the security property, so this test looks for one."""
    fuses = Fuses(tmp_path / "fuses.json")
    assert fuses.advance("svn_app", 5).ok
    for target in (5, 4, 0, -1):
        outcome = fuses.advance("svn_app", target)
        assert outcome.reason is ReasonCode.COUNTER_MONOTONICITY_VIOLATION
        assert fuses.read("svn_app") == 5
    assert not any(name in dir(fuses) for name in ("set", "reset", "write", "decrement"))


def test_a_counter_survives_a_restart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A counter that forgets on reboot proves nothing."""
    Fuses(tmp_path / "fuses.json").advance("svn_app", 11)
    assert Fuses(tmp_path / "fuses.json").read("svn_app") == 11


def test_an_advance_is_staged_until_the_boot_is_confirmed(bench: Bench) -> None:
    """ADR-0002. Until the application reports a healthy start, the previous
    image is still bootable — which is the whole point of staging."""
    bench.boot()
    assert bench.machine.fuses.read("svn_app") == 0
    assert bench.machine.fuses.pending("svn_app") == APP_SVN

    older = attacks.downgrade(bench.machine.hsm, bench.app, slot=1, svn=1)
    assert bench.boot(app=older).booted, "the recovery path must stay open before confirmation"

    bench.boot()
    bench.machine.confirm_boot()
    assert bench.machine.fuses.read("svn_app") == APP_SVN
    assert not bench.boot(app=older).booted


def test_confirming_with_nothing_staged_says_so(bench: Bench) -> None:
    assert bench.machine.confirm_boot() == [ReasonCode.NO_PENDING_ADVANCE]


def test_an_efuse_counter_runs_out(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Thermometer-coded fuse bits are a finite resource. A part that can take
    only 64 security updates in its life is a real design constraint."""
    fuses = Fuses(tmp_path / "fuses.json")
    for step in range(1, EFUSE_BITS + 1):
        assert fuses.advance("svn_sbl", step).ok
    outcome = fuses.advance("svn_sbl", EFUSE_BITS + 1)
    assert outcome.reason is ReasonCode.COUNTER_EXHAUSTED
    assert outcome.detail["substrate"] == Substrate.OTP_EFUSE


def test_a_flash_counter_refuses_to_wrap(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fuses = Fuses(tmp_path / "fuses.json")
    assert fuses.advance("svn_app", COUNTER_MAX).ok
    assert fuses.advance("svn_app", COUNTER_MAX + 1).reason is ReasonCode.COUNTER_EXHAUSTED


def test_factory_reset_is_refused_in_production(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fuses = Fuses(tmp_path / "fuses.json")
    fuses.set_lifecycle(Lifecycle.DEVELOPMENT)
    fuses.advance("svn_app", 4)
    assert fuses.factory_reset().ok

    fuses = Fuses(tmp_path / "fuses.json")
    fuses.set_lifecycle(Lifecycle.DEVELOPMENT)
    fuses.set_lifecycle(Lifecycle.PRODUCTION)
    assert fuses.factory_reset().reason is ReasonCode.FACTORY_RESET_REFUSED


def test_lifecycle_only_moves_forward(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fuses = Fuses(tmp_path / "fuses.json")
    fuses.set_lifecycle(Lifecycle.PRODUCTION)
    assert fuses.set_lifecycle(Lifecycle.DEVELOPMENT).reason is ReasonCode.FUSE_ALREADY_BURNED
    assert fuses.lifecycle is Lifecycle.PRODUCTION


def test_a_write_once_fuse_refuses_a_second_burn(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fuses = Fuses(tmp_path / "fuses.json")
    assert fuses.burn_root_key_hash("ab" * 32).ok
    assert fuses.burn_root_key_hash("cd" * 32).reason is ReasonCode.FUSE_ALREADY_BURNED
    assert fuses.root_key_hash == "ab" * 32


@pytest.mark.parametrize("svn", [APP_SVN, APP_SVN + 1])
def test_an_equal_or_newer_svn_still_boots(bench: Bench, svn: int) -> None:
    """Rollback protection must not block a legitimate update or a re-flash of
    the same version."""
    from secboot.builder import sign_and_build

    bench.boot()
    bench.machine.confirm_boot()
    image = sign_and_build(bench.machine.hsm, slot=1, stage_id=2, svn=svn, payload=APP_PAYLOAD)
    assert bench.boot(app=image).booted
