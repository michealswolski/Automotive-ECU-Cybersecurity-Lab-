"""Signature algorithms the boot chain knows about.

Models the crypto-agility policy of a fielded ECU: the container names an
algorithm, the verifier looks it up in a table, and a machine's policy decides
which entries in that table it is willing to accept. A ROM that hard-codes one
algorithm cannot be migrated; a ROM that accepts any algorithm the *image* names
can be downgraded by an attacker. The allowlist in `policy.py` is what closes
that gap.

No cryptography is implemented here. Every primitive comes from `cryptography`
(pyca); this module only maps identifiers to it.

Public-key length is derived from the algorithm rather than carried in the
header. That is deliberate: the header is a fixed 128 bytes with no spare field,
and a ROM that already has to know how to verify an algorithm necessarily knows
how long that algorithm's public key is.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)


class Algo(IntEnum):
    """`algo_id` values carried in the image header.

    1-3 are the identifiers fixed by SPEC section 3. 4 is an addition: NSA CNSA
    2.0 puts the classical floor at ECDSA P-384 with SHA-384, and having a
    second classical algorithm in the table is what makes the allowlist in
    `policy.py` demonstrable rather than theoretical. See ADR-0004.
    """

    ECDSA_P256_SHA256 = 1
    ED25519 = 2
    ML_DSA_65 = 3
    ECDSA_P384_SHA384 = 4


@dataclass(frozen=True)
class AlgoSpec:
    """Everything the verifier needs to know about one algorithm."""

    algo: Algo
    cli_name: str
    pubkey_len: int
    #: Signature length in bytes. Fixed for every algorithm in this table --
    #: see the ECDSA note below for why that took deliberate effort.
    sig_len: int
    #: Human-readable, printed by `secboot policy show`.
    description: str
    generate: Callable[[], Any]
    sign: Callable[[Any, bytes], bytes]
    verify: Callable[[bytes, bytes, bytes], None]
    public_bytes: Callable[[Any], bytes]
    private_bytes: Callable[[Any], bytes]
    load_private: Callable[[bytes], Any]
    #: True when this algorithm is post-quantum. Used only for reporting.
    post_quantum: bool = False


# --- ECDSA over the NIST curves ---------------------------------------------
#
# The public key travels as an uncompressed X9.62 point (0x04 || X || Y), which
# is what an automotive bootloader would store: fixed length, no ASN.1 parser in
# the ROM. The signature stays DER because that is what pyca produces and the
# header carries an explicit `sig_len`.


def _ec_spec(
    curve: ec.EllipticCurve, digest: hashes.HashAlgorithm, size: int, coordinate: int
) -> dict[str, Any]:
    """ECDSA with a **fixed-width** signature encoding.

    pyca produces DER, whose length varies from signature to signature: `r` and
    `s` are encoded as signed integers, so each gains a 0x00 pad byte whenever
    its top bit is set. For P-256 that means 70, 71 or 72 bytes depending on the
    nonce -- a property of the *signature*, not of the key.

    A boot container cannot carry a length that is only known after signing:
    `sig_len` lives inside the signed header. So the signature is re-encoded here
    as fixed-width `r || s`, big-endian, zero-padded to the curve's coordinate
    size. That makes `sig_len` a constant per algorithm and removes the need to
    guess it, and it is what a bootloader would want anyway -- the same reason
    the public key travels as a raw X9.62 point rather than as ASN.1. No ROM
    should need a DER parser to boot. ADR-0011.
    """

    def generate() -> ec.EllipticCurvePrivateKey:
        return ec.generate_private_key(curve)

    def sign(key: ec.EllipticCurvePrivateKey, data: bytes) -> bytes:
        r, s = decode_dss_signature(key.sign(data, ec.ECDSA(digest)))
        return r.to_bytes(coordinate, "big") + s.to_bytes(coordinate, "big")

    def verify(pub: bytes, signature: bytes, data: bytes) -> None:
        if len(signature) != 2 * coordinate:
            raise InvalidSignature("wrong signature length for this curve")
        r = int.from_bytes(signature[:coordinate], "big")
        s = int.from_bytes(signature[coordinate:], "big")
        public = ec.EllipticCurvePublicKey.from_encoded_point(curve, pub)
        public.verify(encode_dss_signature(r, s), data, ec.ECDSA(digest))

    def public_bytes(key: ec.EllipticCurvePrivateKey) -> bytes:
        return key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )

    def private_bytes(key: ec.EllipticCurvePrivateKey) -> bytes:
        return key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

    def load_private(raw: bytes) -> Any:
        return serialization.load_der_private_key(raw, password=None)

    return {
        "pubkey_len": size,
        "sig_len": 2 * coordinate,
        "generate": generate,
        "sign": sign,
        "verify": verify,
        "public_bytes": public_bytes,
        "private_bytes": private_bytes,
        "load_private": load_private,
    }


def _ed25519_spec() -> dict[str, Any]:
    def verify(pub: bytes, signature: bytes, data: bytes) -> None:
        ed25519.Ed25519PublicKey.from_public_bytes(pub).verify(signature, data)

    return {
        "pubkey_len": 32,
        "sig_len": 64,
        "generate": ed25519.Ed25519PrivateKey.generate,
        "sign": lambda key, data: key.sign(data),
        "verify": verify,
        "public_bytes": lambda key: key.public_key().public_bytes_raw(),
        "private_bytes": lambda key: key.private_bytes_raw(),
        "load_private": ed25519.Ed25519PrivateKey.from_private_bytes,
        "post_quantum": False,
    }


def _mldsa_spec() -> dict[str, Any]:
    """ML-DSA-65 (FIPS 204), resolved lazily.

    `cryptography` exposes this from 47.0.0, but the module imports cleanly over
    an OpenSSL backend and only raises when a key is actually generated. So
    every entry point here resolves the module at call time and `available()`
    proves the backend by generating a key, rather than trusting a version
    number. Never fake a post-quantum signature.
    """

    def _mod() -> Any:
        from cryptography.hazmat.primitives.asymmetric import mldsa  # noqa: PLC0415

        return mldsa

    def verify(pub: bytes, signature: bytes, data: bytes) -> None:
        _mod().MLDSA65PublicKey.from_public_bytes(pub).verify(signature, data)

    return {
        "pubkey_len": 1952,
        "sig_len": 3309,
        "generate": lambda: _mod().MLDSA65PrivateKey.generate(),
        "sign": lambda key, data: key.sign(data),
        "verify": verify,
        "public_bytes": lambda key: key.public_key().public_bytes_raw(),
        "private_bytes": lambda key: key.private_bytes_raw(),
        "load_private": lambda raw: _mod().MLDSA65PrivateKey.from_private_bytes(raw),
        "post_quantum": True,
    }


SPECS: dict[Algo, AlgoSpec] = {
    Algo.ECDSA_P256_SHA256: AlgoSpec(
        algo=Algo.ECDSA_P256_SHA256,
        cli_name="ecdsa-p256",
        description="ECDSA on NIST P-256 with SHA-256",
        **_ec_spec(ec.SECP256R1(), hashes.SHA256(), 65, 32),
    ),
    Algo.ED25519: AlgoSpec(
        algo=Algo.ED25519,
        cli_name="ed25519",
        description="Ed25519 (EdDSA over Curve25519)",
        **_ed25519_spec(),
    ),
    Algo.ML_DSA_65: AlgoSpec(
        algo=Algo.ML_DSA_65,
        cli_name="ml-dsa-65",
        description="ML-DSA-65 (FIPS 204) — post-quantum, backend-dependent",
        **_mldsa_spec(),
    ),
    Algo.ECDSA_P384_SHA384: AlgoSpec(
        algo=Algo.ECDSA_P384_SHA384,
        cli_name="ecdsa-p384",
        description="ECDSA on NIST P-384 with SHA-384 — the CNSA 2.0 classical floor",
        **_ec_spec(ec.SECP384R1(), hashes.SHA384(), 97, 48),
    ),
}

BY_CLI_NAME: dict[str, Algo] = {spec.cli_name: algo for algo, spec in SPECS.items()}


def spec_for(algo_id: int) -> AlgoSpec | None:
    """The algorithm table entry for a header's `algo_id`, or None if unknown.

    Returns None rather than raising: an unknown algorithm identifier is an
    attacker-controlled value on the verification path, and errors are values
    there.
    """
    try:
        return SPECS[Algo(algo_id)]
    except ValueError:
        return None


def available(algo: Algo) -> bool:
    """Whether the installed backend can actually perform this algorithm.

    Proven by generating a key, not by inspecting a version. See ADR-0006.
    """
    try:
        SPECS[algo].generate()
    except (ImportError, UnsupportedAlgorithm, NotImplementedError, ValueError):
        return False
    return True


def verify_signature(spec: AlgoSpec, pubkey: bytes, signature: bytes, data: bytes) -> bool:
    """Signature check, as a value rather than an exception.

    Every failure mode collapses to False on purpose. A verifier that
    distinguishes "malformed point" from "wrong signature" in its return value
    hands an attacker an oracle; the audit log records the detail instead.
    """
    try:
        spec.verify(pubkey, signature, data)
    except (InvalidSignature, ValueError, TypeError, UnsupportedAlgorithm, ImportError):
        return False
    return True
