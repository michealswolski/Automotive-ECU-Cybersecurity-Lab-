"""Producing signed images. The other half of the container format.

Kept separate from `image.py` so the parser has no dependency on the signer:
a ROM contains the parser and never the builder, and the module graph should
say so.
"""

from __future__ import annotations

from .algo import SPECS, Algo
from .hsm import Hsm
from .image import RESERVED_LEN, build, signing_preimage


def sign_and_build(
    hsm: Hsm,
    *,
    slot: int,
    stage_id: int,
    svn: int,
    payload: bytes,
    algo: Algo | None = None,
    key_id: int | None = None,
    image_version: int = 0,
    load_address: int = 0,
    reserved: bytes = b"\x00" * RESERVED_LEN,
) -> bytes:
    """Build a complete, correctly signed `.sbi` image.

    `key_id` defaults to the HSM slot number, which is the common arrangement:
    the revocation bitmap in fuses indexes the same slot table the signing
    infrastructure uses.
    """
    info = hsm.slot_info(slot)
    algo = algo or info.algo
    key_id = slot if key_id is None else key_id
    pubkey = hsm.public_key(slot)

    # `sig_len` sits inside the signed header, so it has to be known before
    # signing. Every algorithm in the table has a fixed signature length, which
    # is exactly why ADR-0011 re-encodes ECDSA away from variable-length DER.
    sig_len = SPECS[algo].sig_len
    preimage = signing_preimage(
        stage_id=stage_id,
        svn=svn,
        payload=payload,
        algo_id=int(algo),
        key_id=key_id,
        signer_pubkey=pubkey,
        sig_len=sig_len,
        image_version=image_version,
        load_address=load_address,
        reserved=reserved,
    )
    signature = hsm.sign(slot, preimage)
    if len(signature) != sig_len:  # pragma: no cover - a backend contract breach
        raise RuntimeError(
            f"{SPECS[algo].cli_name} produced a {len(signature)}-byte signature, expected {sig_len}"
        )

    return build(
        stage_id=stage_id,
        svn=svn,
        payload=payload,
        algo_id=int(algo),
        key_id=key_id,
        signer_pubkey=pubkey,
        signature=signature,
        image_version=image_version,
        load_address=load_address,
        reserved=reserved,
    )


def algo_from_name(name: str) -> Algo | None:
    for algo, spec in SPECS.items():
        if spec.cli_name == name:
            return algo
    return None
