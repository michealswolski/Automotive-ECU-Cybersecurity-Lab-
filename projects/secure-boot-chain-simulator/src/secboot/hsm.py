"""A simulated hardware security module.

Models an EVITA-Medium class automotive HSM: a separate execution domain that
generates key pairs, signs on request, and hands out public keys — and has no
operation at all that returns a private key. The whole point of the boundary is
that "export the key" is not in the instruction set, so it is not in this API
either.

What is simulated and what is not:

* **Simulated:** the key custody boundary, non-exportability, per-slot usage
  flags, revocation, and operation latency (an ECU's boot-time budget is real).
* **Not simulated:** tamper resistance, side-channel hardening, secure key
  injection at the silicon vendor. Those are physical properties and no amount
  of Python models them.

Keys are persisted to a keystore encrypted with AES-256-GCM under a key derived
from a passphrase with Scrypt. That models "the key material is protected by the
HSM boundary" for a process that has to survive a restart; it is not a claim
that this is equivalent to hardware.

`hsm.py` and `algo.py` are the two modules inside the boundary. Nothing else in
the package may touch private key material, and `tests/test_hsm_isolation.py`
enforces that with an AST scan rather than a text search.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Flag, auto
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .algo import SPECS, Algo
from .reasons import ReasonCode

#: Scrypt cost parameters from SPEC section 7. Deliberately expensive: this is
#: the passphrase-to-key step, and it is done once per process.
KDF_N = 2**15
KDF_R = 8
KDF_P = 1
KDF_SALT_LEN = 16
#: Used when no passphrase is supplied. The caller is warned loudly; a real
#: provisioning flow would take the passphrase from an HSM operator ceremony.
DEV_PASSPHRASE = "insecure-development-passphrase"


class Usage(Flag):
    """What a slot is allowed to do.

    Separating SIGN from ATTEST matters: the attestation key signs statements
    *about* the device, and a key that can do both lets an attacker who can
    request an attestation quote also request a firmware signature.
    """

    NONE = 0
    SIGN = auto()
    VERIFY = auto()
    ATTEST = auto()


@dataclass(frozen=True)
class SlotInfo:
    """The public view of a key slot. Note what is absent."""

    slot: int
    algo: Algo
    usage: Usage
    created: str
    revoked: bool
    public_key: bytes
    #: Always False. Present because a real HSM slot has this attribute and
    #: a reader should see that it is pinned rather than assume it.
    exportable: bool = False

    @property
    def algo_name(self) -> str:
        return SPECS[self.algo].cli_name


class HsmError(Exception):
    """Programmer error against the HSM API — a missing slot, a usage
    violation. Distinct from the verification path, where errors are values."""

    def __init__(self, reason: ReasonCode, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class Hsm:
    """The simulated module. One instance owns one keystore file."""

    def __init__(
        self,
        path: Path,
        passphrase: str = DEV_PASSPHRASE,
        *,
        latency_ms: float = 0.0,
        kdf_n: int = KDF_N,
    ) -> None:
        self._path = path
        self._passphrase = passphrase
        self._latency_ms = latency_ms
        self._kdf_n = kdf_n
        #: Private key material. Never returned, never logged, never compared
        #: against attacker input. The single reason this class exists.
        self._private_keys: dict[int, Any] = {}
        self._meta: dict[int, dict[str, Any]] = {}
        self._operations = 0
        if path.exists():
            self._load()

    # --- persistence --------------------------------------------------------

    def _derive(self, salt: bytes) -> bytes:
        kdf = Scrypt(salt=salt, length=32, n=self._kdf_n, r=KDF_R, p=KDF_P)
        return kdf.derive(self._passphrase.encode("utf-8"))

    def _load(self) -> None:
        envelope = json.loads(self._path.read_text(encoding="utf-8"))
        salt = bytes.fromhex(envelope["kdf"]["salt"])
        key = self._derive(salt)
        plaintext = AESGCM(key).decrypt(
            bytes.fromhex(envelope["nonce"]),
            bytes.fromhex(envelope["ciphertext"]),
            b"secboot-keystore-v1",
        )
        for raw_slot, entry in json.loads(plaintext).items():
            slot = int(raw_slot)
            algo = Algo(entry["algo"])
            self._private_keys[slot] = SPECS[algo].load_private(bytes.fromhex(entry["private"]))
            self._meta[slot] = {
                "algo": algo,
                "usage": Usage(entry["usage"]),
                "created": entry["created"],
                "revoked": entry["revoked"],
            }

    def _save(self) -> None:
        body = {
            str(slot): {
                "algo": int(meta["algo"]),
                "usage": meta["usage"].value,
                "created": meta["created"],
                "revoked": meta["revoked"],
                "private": SPECS[meta["algo"]].private_bytes(self._private_keys[slot]).hex(),
            }
            for slot, meta in self._meta.items()
        }
        salt = os.urandom(KDF_SALT_LEN)
        nonce = os.urandom(12)
        key = self._derive(salt)
        ciphertext = AESGCM(key).encrypt(
            nonce, json.dumps(body).encode("utf-8"), b"secboot-keystore-v1"
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "kdf": {
                        "algorithm": "scrypt",
                        "salt": salt.hex(),
                        "n": self._kdf_n,
                        "r": KDF_R,
                        "p": KDF_P,
                    },
                    "nonce": nonce.hex(),
                    "ciphertext": ciphertext.hex(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    # --- public API ---------------------------------------------------------

    def generate(self, slot: int, algo: Algo, usage: Usage = Usage.SIGN | Usage.VERIFY) -> SlotInfo:
        """Create a key pair inside the module.

        Models the HSM key-generation command: the private half is created in
        the module and never crosses the boundary, so there is no window in
        which it exists anywhere a compromised application could read it.
        """
        if not SPECS[algo]:  # pragma: no cover - defensive
            raise HsmError(ReasonCode.UNKNOWN_ALGO, f"unknown algorithm {algo}")
        try:
            private = SPECS[algo].generate()
        except Exception as exc:  # noqa: BLE001 - backend availability is a value here
            raise HsmError(
                ReasonCode.ALGO_BACKEND_UNAVAILABLE,
                f"the installed cryptography backend cannot generate {SPECS[algo].cli_name} keys "
                f"({type(exc).__name__}). ML-DSA needs an AWS-LC or BoringSSL backed build; "
                f"see docs/post-quantum.md.",
            ) from exc
        self._private_keys[slot] = private
        self._meta[slot] = {
            "algo": algo,
            "usage": usage,
            "created": datetime.now(UTC).isoformat(timespec="seconds"),
            "revoked": False,
        }
        self._save()
        return self.slot_info(slot)

    def import_private(
        self,
        slot: int,
        algo: Algo,
        raw: bytes,
        usage: Usage = Usage.SIGN | Usage.VERIFY,
    ) -> SlotInfo:
        """Inject an externally generated key into a slot.

        Models the key-injection step of a production provisioning ceremony,
        where the signing key is generated in the OEM's HSM and injected into
        the part rather than generated on it. It is also what makes the demo
        reproducible: an Ed25519 private key *is* its 32 seed bytes, so a
        seeded demo can derive a real key deterministically without inventing
        any cryptography.

        The key goes in and cannot come back out. Import is not the inverse of
        export; there is still no export.
        """
        self._private_keys[slot] = SPECS[algo].load_private(raw)
        self._meta[slot] = {
            "algo": algo,
            "usage": usage,
            "created": datetime.now(UTC).isoformat(timespec="seconds"),
            "revoked": False,
        }
        self._save()
        return self.slot_info(slot)

    def sign(self, slot: int, data: bytes) -> bytes:
        """Sign inside the module. The only way to use a private key."""
        meta = self._require(slot)
        if Usage.SIGN not in meta["usage"]:
            raise HsmError(ReasonCode.KEY_SLOT_MISSING, f"slot {slot} is not a signing key")
        if meta["revoked"]:
            raise HsmError(ReasonCode.KEY_ID_REVOKED, f"slot {slot} is revoked")
        self._simulate_latency()
        return bytes(SPECS[meta["algo"]].sign(self._private_keys[slot], data))

    def attest(self, slot: int, data: bytes) -> bytes:
        """Sign an attestation statement. A separate operation from `sign`.

        The split is the point: an ATTEST slot cannot sign firmware and a SIGN
        slot cannot produce a quote, so whoever can request an attestation
        cannot parlay that into a firmware signature.
        """
        meta = self._require(slot)
        if Usage.ATTEST not in meta["usage"]:
            raise HsmError(ReasonCode.KEY_SLOT_MISSING, f"slot {slot} is not an attestation key")
        if meta["revoked"]:
            raise HsmError(ReasonCode.KEY_ID_REVOKED, f"slot {slot} is revoked")
        self._simulate_latency()
        return bytes(SPECS[meta["algo"]].sign(self._private_keys[slot], data))

    def public_key(self, slot: int) -> bytes:
        """The public half, in the encoding the image container carries."""
        meta = self._require(slot)
        return bytes(SPECS[meta["algo"]].public_bytes(self._private_keys[slot]))

    def revoke(self, slot: int) -> None:
        """Mark a slot unusable. Models blowing the slot's disable fuse."""
        meta = self._require(slot)
        meta["revoked"] = True
        self._save()

    def slot_info(self, slot: int) -> SlotInfo:
        meta = self._require(slot)
        return SlotInfo(
            slot=slot,
            algo=meta["algo"],
            usage=meta["usage"],
            created=meta["created"],
            revoked=meta["revoked"],
            public_key=self.public_key(slot),
        )

    def slots(self) -> list[SlotInfo]:
        return [self.slot_info(slot) for slot in sorted(self._meta)]

    def has_slot(self, slot: int) -> bool:
        return slot in self._meta

    # --- latency model ------------------------------------------------------

    def simulate_operation(self) -> None:
        """Charge the boot-time budget for one HSM operation.

        Called by the verifier before a signature check, because on a real ECU
        that check runs *in* the HSM. `secboot boot --hsm-latency-ms 8` makes
        the cost of a three-stage chain visible, which is the honest answer to
        "what does secure boot do to your startup time?".
        """
        self._simulate_latency()

    def _simulate_latency(self) -> None:
        self._operations += 1
        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)

    @property
    def operations(self) -> int:
        """How many HSM operations this boot cost."""
        return self._operations

    def _require(self, slot: int) -> dict[str, Any]:
        meta = self._meta.get(slot)
        if meta is None:
            raise HsmError(ReasonCode.KEY_SLOT_MISSING, f"no key in slot {slot}")
        return meta
