"""Producing malicious images.

Negative paths are the deliverable here, not an afterthought, so the attacks are
library functions with tests of their own rather than shell one-liners. Each one
models a real capability an attacker might have, and the docstring says which:
flash write access, a stolen signing key, or an old but legitimately signed
release.

Every function returns bytes and touches no machine state. What each attack
proves is that a *different* control catches it — that is the point of having
five of them rather than one.
"""

from __future__ import annotations

from .algo import Algo
from .builder import sign_and_build
from .hsm import Hsm
from .image import HEADER_LEN, ImageHeader, build, parse, unpack_header


def corrupt(image_bytes: bytes, byte_offset: int, bit: int) -> bytes:
    """Flip one bit. Models flash bit-rot, or an attacker with write access
    but no signing key.

    Caught by the payload digest inside the signed header — before any
    signature operation is spent, which is why the digest field exists at all
    when the signature would also have caught it.
    """
    data = bytearray(image_bytes)
    if not 0 <= byte_offset < len(data):
        raise ValueError(f"offset {byte_offset} outside a {len(data)}-byte image")
    data[byte_offset] ^= 1 << (bit & 7)
    return bytes(data)


def downgrade(hsm: Hsm, image_bytes: bytes, *, slot: int, svn: int) -> bytes:
    """Re-sign an older security version with the *legitimate* key.

    Models the strongest realistic supply-chain position short of key theft:
    the attacker has an old, genuinely signed release and can get it installed.
    Every signature check passes. Only the monotonic counter refuses it, which
    is the single most important demonstration in this project.
    """
    header = unpack_header(image_bytes)
    payload = image_bytes[HEADER_LEN : HEADER_LEN + header.payload_len]
    return sign_and_build(
        hsm,
        slot=slot,
        stage_id=header.stage_id,
        svn=svn,
        payload=payload,
        key_id=header.key_id,
        image_version=header.image_version,
    )


def strip_signature(image_bytes: bytes) -> bytes:
    """Remove the signature and declare it zero-length.

    Models an attacker betting that the verifier treats "no signature" as
    "nothing to check" — a real bootloader bug pattern. The header is rebuilt
    with a correct CRC, so only the signature check catches it.
    """
    parsed = parse(image_bytes, unpack_header(image_bytes).stage_id)
    if parsed.image is None:
        raise ValueError(f"input is not a valid image: {parsed.reason}")
    image = parsed.image
    return build(
        stage_id=image.header.stage_id,
        svn=image.header.svn,
        payload=image.payload,
        algo_id=image.header.algo_id,
        key_id=image.header.key_id,
        signer_pubkey=image.signer_pubkey,
        signature=b"",
        image_version=image.header.image_version,
        load_address=image.header.load_address,
    )


def tamper_payload(image_bytes: bytes, new_payload: bytes) -> bytes:
    """Replace the payload and fix the header digest, leaving the signature.

    Models an attacker with flash write access who understands the container:
    recomputing `payload_sha256` gets them past the cheap digest check, so the
    image now fails at the signature instead. That is what makes it the right
    input for the fault-injection scenario — it isolates the signature compare
    as the single control standing between the attacker and execution.
    """
    parsed = parse(image_bytes, unpack_header(image_bytes).stage_id)
    if parsed.image is None:
        raise ValueError(f"input is not a valid image: {parsed.reason}")
    image = parsed.image
    return build(
        stage_id=image.header.stage_id,
        svn=image.header.svn,
        payload=new_payload,
        algo_id=image.header.algo_id,
        key_id=image.header.key_id,
        signer_pubkey=image.signer_pubkey,
        signature=image.signature,
        image_version=image.header.image_version,
        load_address=image.header.load_address,
    )


def swap_stage(image_bytes: bytes) -> bytes:
    """Present a bootloader image where the application is expected.

    Nothing is modified — the bytes are a genuine, correctly signed image. The
    attack is the *context*. Only the stage identifier inside the signed header
    distinguishes them, which is exactly why it is inside the signed header.
    """
    return image_bytes


def forge(image_bytes: bytes, attacker_hsm: Hsm, *, slot: int, algo: Algo | None = None) -> bytes:
    """Re-sign with a key the attacker generated themselves.

    Models a complete compromise of the attacker's own signing infrastructure,
    which is to say: none of the victim's. The signature is valid; the key is
    not trusted. Caught by the fuse root-key hash at stage 1 and by the
    bootloader's signer allowlist at stage 2.
    """
    header = unpack_header(image_bytes)
    payload = image_bytes[HEADER_LEN : HEADER_LEN + header.payload_len]
    return sign_and_build(
        attacker_hsm,
        slot=slot,
        stage_id=header.stage_id,
        svn=header.svn,
        payload=payload,
        algo=algo,
        key_id=header.key_id,
        image_version=header.image_version,
    )


def rewrite_header(image_bytes: bytes, **fields: int | bytes) -> bytes:
    """Edit header fields and fix the CRC, leaving the signature alone.

    The general form of "the CRC is not a security control": any header edit can
    be made to look self-consistent. Used by the tests to reach the structural
    reason codes individually.
    """
    parsed_header = unpack_header(image_bytes)
    values = {
        "stage_id": parsed_header.stage_id,
        "svn": parsed_header.svn,
        "image_version": parsed_header.image_version,
        "payload_len": parsed_header.payload_len,
        "load_address": parsed_header.load_address,
        "algo_id": parsed_header.algo_id,
        "key_id": parsed_header.key_id,
        "payload_sha256": parsed_header.payload_sha256,
        "sig_len": parsed_header.sig_len,
        "signer_pubkey_sha256": parsed_header.signer_pubkey_sha256,
        "header_version": parsed_header.header_version,
        "magic": parsed_header.magic,
        "reserved": parsed_header.reserved,
    }
    values.update(fields)
    header = ImageHeader(**values)  # type: ignore[arg-type]
    return header.pack() + image_bytes[HEADER_LEN:]
