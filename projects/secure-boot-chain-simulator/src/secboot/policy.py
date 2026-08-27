"""What this machine is willing to accept.

Separated from the verifier on purpose. Policy is per-device configuration
data — which algorithms, which app signers, whether an unfused development part
may boot — while `verify.py` is the fixed logic that consults it. Keeping them
apart is what makes "the same ROM, a different policy" expressible, which is how
a development part and a production part actually differ.

The algorithm allowlist is the crypto-agility control. A verifier that runs
whichever algorithm the *image* names can be downgraded by an attacker who signs
with the weakest one the ROM still supports; the allowlist means the image can
only ask for something the device already agreed to.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .algo import Algo


@dataclass
class Policy:
    """Per-machine security policy."""

    #: Algorithms this device will verify. Everything else is rejected with
    #: ALGO_NOT_PERMITTED even though the verifier knows how to run it.
    allowed_algos: set[Algo] = field(
        default_factory=lambda: {Algo.ECDSA_P256_SHA256, Algo.ECDSA_P384_SHA384, Algo.ED25519}
    )
    #: SHA-256 of each public key the bootloader will accept for the
    #: application stage. Held by the SBL, not by the ROM: the ROM's only root
    #: of trust is the fuse hash, and delegating app-signing authority to a
    #: separate key set is what lets an application signing key be rotated
    #: without touching OTP.
    app_signer_hashes: set[str] = field(default_factory=set)
    #: When True, a part with the secure-boot fuse unburned still boots, loudly.
    #: Models a development sample. A production part burns the fuse and this
    #: flag becomes unreachable.
    allow_insecure: bool = False
    #: When True, an SVN advance is staged and needs `confirm-boot`. See ADR-0002.
    require_boot_confirmation: bool = True

    def authorize_app_signer(self, public_key: bytes) -> None:
        self.app_signer_hashes.add(hashlib.sha256(public_key).hexdigest())

    def digest_input(self) -> str:
        """A canonical rendering, measured into PCR3.

        Policy is measured because a device that quietly widened its allowlist
        is exactly as compromised as one running a modified image, and only a
        measurement makes that visible to a remote verifier.
        """
        algos = sorted(int(a) for a in self.allowed_algos)
        signers = sorted(self.app_signer_hashes)
        return (
            f"allowed_algos={algos};app_signers={signers};"
            f"allow_insecure={self.allow_insecure};"
            f"require_boot_confirmation={self.require_boot_confirmation}"
        )
