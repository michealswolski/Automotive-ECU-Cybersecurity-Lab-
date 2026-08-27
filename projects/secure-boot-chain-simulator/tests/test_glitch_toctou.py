"""Two attacks that verification alone cannot stop.

These are the tests that justify measured boot and the load-time re-check
existing at all. Both defeat the signature check — one by skipping it
physically, one by acting after it — and both are caught anyway.
"""

from __future__ import annotations

from conftest import Bench
from secboot import attacks
from secboot.machine import Fault
from secboot.reasons import ReasonCode


def test_a_glitched_signature_compare_lets_a_bad_image_run(bench: Bench) -> None:
    """The uncomfortable half: verified boot is defeated, and it boots."""
    tampered = attacks.tamper_payload(bench.app, b"<attacker payload>" * 8)
    assert bench.boot(app=tampered).reason is ReasonCode.SIGNATURE_INVALID

    bench.machine.fault = Fault(force_signature_pass=True)
    assert bench.boot(app=tampered).booted


def test_measured_boot_records_what_verified_boot_missed(bench: Bench) -> None:
    """The other half: the PCR moved, so a remote verifier sees it."""
    golden = bench.boot()
    assert golden.booted
    golden_pcrs = bench.machine.pcr.as_dict()

    bench.machine.fault = Fault(force_signature_pass=True)
    bench.boot(app=attacks.tamper_payload(bench.app, b"<attacker payload>" * 8))

    quote = bench.machine.attest("nonce-from-the-challenger")
    matches, description = bench.machine.verify_quote(quote, golden_pcrs)
    assert not matches
    assert "PCR2" in description

    # Exactly one register, and it is the one for the stage that changed. A
    # quote that diverged everywhere would name the stage no better than a
    # single boolean would.
    from secboot.measure import diff_quotes

    assert diff_quotes(quote["pcrs"], golden_pcrs).diverged == [2]


def test_the_fault_is_recorded_as_critical(bench: Bench) -> None:
    """Even a defeated control leaves evidence, which is what the log is for."""
    bench.machine.fault = Fault(force_signature_pass=True)
    bench.boot(app=attacks.tamper_payload(bench.app, b"<attacker payload>" * 8))
    critical = [r for r in bench.machine.audit.records() if r["severity"] == "CRITICAL"]
    assert any(r["event"] == "FAULT_INJECTION" for r in critical)


def test_swapping_the_image_after_verification_is_caught(bench: Bench) -> None:
    """Time-of-check to time-of-use: the bytes that load are re-measured against
    the bytes that were verified, so a swap in between does not go through."""
    bench.machine.fault = Fault(toctou_payload=attacks.corrupt(bench.app, 200, 1))

    result = bench.boot()

    assert not result.booted
    failing = result.failing
    assert failing is not None
    assert failing.verify.detail.get("toctou") is True
    assert any(r["event"] == "TOCTOU_RECHECK" for r in bench.machine.audit.records())


def test_a_loader_that_returns_the_verified_bytes_is_fine(bench: Bench) -> None:
    calls: list[int] = []

    def loader(stage_id: int, data: bytes) -> bytes:
        calls.append(stage_id)
        return data

    assert bench.machine.boot(bench.sbl, bench.app, loader=loader).booted
    assert calls == [1, 2]


def test_a_toctou_swap_halts_before_the_next_stage(bench: Bench) -> None:
    """Control must not transfer past a stage that failed its load-time check."""
    bench.machine.fault = Fault(toctou_payload=b"junk", toctou_stage=1)
    result = bench.boot()
    assert result.halted_at == 1
    assert len(result.stages) == 1
