"""Every reason code, reached individually, in the order the spec fixes.

The order is a security property, not a performance one: a signature check over
lengths that have not been validated is how bootloaders get exploited. Each test
here asserts both that the expected code fired *and* that no later check ran,
which `VerifyResult.checks_run` makes observable from outside the verifier.
"""

from __future__ import annotations

import hashlib
import zlib
from pathlib import Path

import pytest

from conftest import APP_PAYLOAD, Bench
from secboot import attacks, image
from secboot.algo import Algo
from secboot.builder import sign_and_build
from secboot.reasons import VERIFY_ORDER, ReasonCode
from secboot.verify import verify_stage


def _verify(bench: Bench, raw: bytes, stage: int = 2):  # type: ignore[no-untyped-def]
    return verify_stage(bench.machine, raw, stage)


def _assert_stopped_at(result, code: ReasonCode) -> None:  # type: ignore[no-untyped-def]
    assert result.reason is code, f"expected {code}, got {result.reason}: {result.detail}"
    assert result.checks_run[-1] is code, result.checks_run
    later = VERIFY_ORDER[VERIFY_ORDER.index(code) + 1 :]
    assert not set(result.checks_run) & set(later), "a later check ran"


def test_image_too_short(bench: Bench) -> None:
    _assert_stopped_at(_verify(bench, b"short"), ReasonCode.IMAGE_TOO_SHORT)


def test_bad_magic(bench: Bench) -> None:
    _assert_stopped_at(
        _verify(bench, attacks.rewrite_header(bench.app, magic=b"NOPE")), ReasonCode.BAD_MAGIC
    )


def test_unsupported_header_version(bench: Bench) -> None:
    _assert_stopped_at(
        _verify(bench, attacks.rewrite_header(bench.app, header_version=99)),
        ReasonCode.UNSUPPORTED_HEADER_VERSION,
    )


def test_reserved_not_zero(bench: Bench) -> None:
    """The forward-compatibility trap: refusing non-zero now is what makes it
    safe to assign meaning to those bytes in a later container version."""
    _assert_stopped_at(
        _verify(bench, attacks.rewrite_header(bench.app, reserved=b"\x01" + b"\x00" * 27)),
        ReasonCode.RESERVED_NOT_ZERO,
    )


def test_header_crc_mismatch(bench: Bench) -> None:
    broken = bytearray(bench.app)
    broken[image.SIGNED_HEADER_LEN] ^= 0xFF
    _assert_stopped_at(_verify(bench, bytes(broken)), ReasonCode.HEADER_CRC_MISMATCH)


def test_wrong_stage_id(bench: Bench) -> None:
    """A genuine, correctly signed bootloader image offered as the application."""
    _assert_stopped_at(_verify(bench, attacks.swap_stage(bench.sbl)), ReasonCode.WRONG_STAGE_ID)


def test_length_overflow(bench: Bench) -> None:
    lying = attacks.rewrite_header(bench.app, payload_len=0xFFFF)
    _assert_stopped_at(_verify(bench, lying), ReasonCode.LENGTH_OVERFLOW)


def test_secure_boot_disabled(bench: Bench) -> None:
    bench.machine.fuses.secure_boot_enable = False
    _assert_stopped_at(_verify(bench, bench.app), ReasonCode.SECURE_BOOT_DISABLED)


def test_secure_boot_disabled_is_survivable_on_a_development_part(bench: Bench) -> None:
    bench.machine.fuses.secure_boot_enable = False
    bench.machine.policy.allow_insecure = True
    result = _verify(bench, bench.app)
    assert result.ok and result.insecure
    warnings = [r for r in bench.machine.audit.records() if r["severity"] == "WARN"]
    assert warnings, "booting an unfused part must be loud"


def test_unknown_algo(bench: Bench) -> None:
    """`rewrite_header` fixes the CRC, so only the algorithm table refuses it."""
    _assert_stopped_at(_verify(bench, _reframe(bench.app, algo_id=200)), ReasonCode.UNKNOWN_ALGO)


def test_algo_not_permitted(bench: Bench) -> None:
    """The crypto-agility control: the verifier can run P-256 and refuses to,
    because this machine's policy floor is higher."""
    bench.attacker.hsm.generate(2, Algo.ECDSA_P256_SHA256)
    weaker = attacks.forge(bench.app, bench.attacker.hsm, slot=2, algo=Algo.ECDSA_P256_SHA256)
    _assert_stopped_at(_verify(bench, weaker), ReasonCode.ALGO_NOT_PERMITTED)


def test_key_id_revoked(bench: Bench) -> None:
    bench.machine.fuses.revoke_key(1)
    _assert_stopped_at(_verify(bench, bench.app), ReasonCode.KEY_ID_REVOKED)


def test_root_key_mismatch(bench: Bench) -> None:
    forged_sbl = attacks.forge(bench.sbl, bench.attacker.hsm, slot=0)
    _assert_stopped_at(_verify(bench, forged_sbl, stage=1), ReasonCode.ROOT_KEY_MISMATCH)


def test_key_not_authorized_for_stage(bench: Bench) -> None:
    forged = attacks.forge(bench.app, bench.attacker.hsm, slot=0)
    _assert_stopped_at(_verify(bench, forged), ReasonCode.KEY_NOT_AUTHORIZED_FOR_STAGE)


def test_payload_digest_mismatch(bench: Bench) -> None:
    _assert_stopped_at(
        _verify(bench, attacks.corrupt(bench.app, 200, 3)), ReasonCode.PAYLOAD_DIGEST_MISMATCH
    )


def test_signature_invalid(bench: Bench) -> None:
    tampered = attacks.tamper_payload(bench.app, b"<attacker payload>" * 8)
    _assert_stopped_at(_verify(bench, tampered), ReasonCode.SIGNATURE_INVALID)


def test_stripped_signature_is_not_a_free_pass(bench: Bench) -> None:
    """A missing signature must not read as nothing to check."""
    _assert_stopped_at(
        _verify(bench, attacks.strip_signature(bench.app)), ReasonCode.SIGNATURE_INVALID
    )


def test_rollback_blocked(bench: Bench) -> None:
    bench.machine.fuses.advance("svn_app", 9)
    _assert_stopped_at(_verify(bench, bench.app), ReasonCode.ROLLBACK_BLOCKED)


def test_accepted(bench: Bench) -> None:
    result = _verify(bench, bench.app)
    assert result.ok
    _assert_stopped_at(result, ReasonCode.ACCEPTED)


def test_every_reason_code_in_the_spec_is_covered_by_a_test() -> None:
    """A guard on this file rather than on the verifier: if a code is added to
    the order, a test for it has to appear here too."""
    source = Path(__file__).read_text(encoding="utf-8")
    missing = [code for code in VERIFY_ORDER if f"ReasonCode.{code.name}" not in source]
    assert not missing, f"no test reaches: {missing}"


@pytest.mark.parametrize("stage,counter", [(1, "svn_sbl"), (2, "svn_app")])
def test_each_stage_is_guarded_by_its_own_counter(bench: Bench, stage: int, counter: str) -> None:
    bench.machine.fuses.advance(counter, 99)
    raw = bench.sbl if stage == 1 else bench.app
    assert _verify(bench, raw, stage).reason is ReasonCode.ROLLBACK_BLOCKED


def _reframe(raw: bytes, *, algo_id: int) -> bytes:
    """Rebuild an image under a different algo_id, keeping lengths consistent.

    A bare header edit would trip LENGTH_OVERFLOW first, because the public key
    length is derived from the algorithm — so reaching UNKNOWN_ALGO needs an
    image whose lengths still add up under the unknown identifier.
    """
    parsed = image.parse(raw, 2)
    assert parsed.image is not None
    inner = parsed.image
    header = image.ImageHeader(
        stage_id=inner.header.stage_id,
        svn=inner.header.svn,
        image_version=inner.header.image_version,
        payload_len=inner.header.payload_len,
        load_address=inner.header.load_address,
        algo_id=algo_id,
        key_id=inner.header.key_id,
        payload_sha256=hashlib.sha256(inner.payload).digest(),
        sig_len=inner.header.sig_len + len(inner.signer_pubkey),
        signer_pubkey_sha256=inner.header.signer_pubkey_sha256,
    )
    body = inner.payload + inner.signer_pubkey + inner.signature
    packed = header.pack() + body
    assert zlib.crc32(packed[: image.SIGNED_HEADER_LEN]) & 0xFFFFFFFF
    return packed


def test_verify_order_matches_the_spec_sequence(bench: Bench) -> None:
    """A clean image runs every check exactly once, in the documented order."""
    result = _verify(bench, bench.app)
    assert result.checks_run == list(VERIFY_ORDER)


def test_a_second_stage_image_never_satisfies_the_root_key_check(bench: Bench) -> None:
    """Stage authority is delegated, so the app signer is *not* the root key."""
    app_signed_as_sbl = sign_and_build(
        bench.machine.hsm, slot=1, stage_id=1, svn=3, payload=APP_PAYLOAD
    )
    assert _verify(bench, app_signed_as_sbl, stage=1).reason is ReasonCode.ROOT_KEY_MISMATCH
