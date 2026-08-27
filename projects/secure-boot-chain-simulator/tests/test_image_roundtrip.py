"""The container format: what is packed is what is parsed."""

from __future__ import annotations

import hashlib
import random

import pytest

from secboot import image
from secboot.algo import Algo
from secboot.reasons import ReasonCode


def _valid(payload: bytes = b"payload", *, stage_id: int = 2) -> bytes:
    pubkey = b"\x04" + b"\x11" * 64
    return image.build(
        stage_id=stage_id,
        svn=5,
        payload=payload,
        algo_id=int(Algo.ECDSA_P256_SHA256),
        key_id=1,
        signer_pubkey=pubkey,
        signature=b"\x30" * 70,
    )


def test_header_is_exactly_128_bytes() -> None:
    """A ROM parses this with a fixed-size buffer, so the size is a contract."""
    assert len(_valid()[: image.HEADER_LEN]) == image.HEADER_LEN
    assert image.SIGNED_HEADER_LEN == 0x7C


def test_pack_then_parse_round_trips() -> None:
    raw = _valid(b"a longer payload " * 4)
    result = image.parse(raw, expected_stage_id=2)
    assert result.ok and result.image is not None
    parsed = result.image
    assert parsed.header.svn == 5
    assert parsed.header.key_id == 1
    assert parsed.payload == b"a longer payload " * 4
    assert parsed.header.payload_sha256 == hashlib.sha256(parsed.payload).digest()


@pytest.mark.parametrize("seed", range(25))
def test_random_headers_round_trip(seed: int) -> None:
    rng = random.Random(seed)
    payload = bytes(rng.randrange(256) for _ in range(rng.randrange(1, 200)))
    raw = _valid(payload)
    result = image.parse(raw, expected_stage_id=2)
    assert result.ok and result.image is not None
    assert result.image.payload == payload


def test_signed_region_excludes_the_crc() -> None:
    """The CRC is a corruption detector, not a security control, so it is
    deliberately outside the bytes the signature covers."""
    raw = _valid()
    result = image.parse(raw, 2)
    assert result.image is not None
    assert result.image.signed_data().startswith(raw[: image.SIGNED_HEADER_LEN])
    assert raw[image.SIGNED_HEADER_LEN : image.HEADER_LEN] not in result.image.signed_data()


def test_measurement_covers_the_authenticated_bytes_only() -> None:
    """ADR-0003: re-signing identical content must not move the measurement."""
    raw = _valid()
    other = bytearray(raw)
    other[-1] ^= 0xFF  # a different signature over the same content
    first = image.parse(bytes(raw), 2).image
    second = image.parse(bytes(other), 2).image
    assert first is not None and second is not None
    assert first.measurement() == second.measurement()


def test_trailing_bytes_are_rejected() -> None:
    """Extra bytes after the signature are a place to hide a payload."""
    result = image.parse(_valid() + b"smuggled", 2)
    assert result.reason is ReasonCode.LENGTH_OVERFLOW


@pytest.mark.parametrize("cli_name", ["ecdsa-p256", "ecdsa-p384", "ed25519"])
def test_signature_length_is_a_constant_per_algorithm(cli_name: str) -> None:
    """The regression this file gained after a CI failure.

    `sig_len` lives inside the signed header, so it has to be known *before*
    signing. DER-encoded ECDSA does not oblige: `r` and `s` each gain a 0x00 pad
    byte whenever their top bit is set, so a P-256 signature is 70, 71 or 72
    bytes depending on the nonce — a property of the signature, not of the key.
    The builder originally signed, checked, and re-signed against a corrected
    header, which converges only by luck and failed on CI at roughly one run in
    two hundred.

    ADR-0011 re-encodes ECDSA as fixed-width `r || s` instead. Sixty signatures
    over sixty different messages: under the old encoding the odds of every one
    landing on the same length are about 1 in 10^19.
    """
    from secboot.algo import BY_CLI_NAME, SPECS

    spec = SPECS[BY_CLI_NAME[cli_name]]
    key = spec.generate()
    lengths = {len(spec.sign(key, f"message {n}".encode())) for n in range(60)}

    assert lengths == {spec.sig_len}


def test_a_fixed_width_signature_still_verifies() -> None:
    """Re-encoding must not have broken the thing it re-encodes."""
    from secboot.algo import SPECS, Algo, verify_signature

    spec = SPECS[Algo.ECDSA_P256_SHA256]
    key = spec.generate()
    public = spec.public_bytes(key)
    signature = spec.sign(key, b"payload")

    assert verify_signature(spec, public, signature, b"payload")
    assert not verify_signature(spec, public, signature, b"payload!")
    assert not verify_signature(spec, public, signature[:-1], b"payload")
    assert not verify_signature(spec, public, bytes(len(signature)), b"payload")
