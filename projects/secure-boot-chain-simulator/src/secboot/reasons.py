"""Stable machine-readable outcomes for every decision the boot chain makes.

Models the fault codes a production bootloader reports over its diagnostic
interface: a fielded ECU cannot return a stack trace, it returns a number that a
service tool can look up. Each code here names one control, and the order of
`VERIFY_ORDER` is the order the verifier runs those controls in.

Every code is documented in ``docs/reason-codes.md`` with the threat it detects.
"""

from __future__ import annotations

from enum import StrEnum


class ReasonCode(StrEnum):
    """Why a stage was accepted, rejected, or why the chain halted."""

    # --- The verification path, in execution order (SPEC section 4) ----------
    IMAGE_TOO_SHORT = "IMAGE_TOO_SHORT"
    BAD_MAGIC = "BAD_MAGIC"
    UNSUPPORTED_HEADER_VERSION = "UNSUPPORTED_HEADER_VERSION"
    RESERVED_NOT_ZERO = "RESERVED_NOT_ZERO"
    HEADER_CRC_MISMATCH = "HEADER_CRC_MISMATCH"
    WRONG_STAGE_ID = "WRONG_STAGE_ID"
    LENGTH_OVERFLOW = "LENGTH_OVERFLOW"
    SECURE_BOOT_DISABLED = "SECURE_BOOT_DISABLED"
    UNKNOWN_ALGO = "UNKNOWN_ALGO"
    ALGO_NOT_PERMITTED = "ALGO_NOT_PERMITTED"
    KEY_ID_REVOKED = "KEY_ID_REVOKED"
    ROOT_KEY_MISMATCH = "ROOT_KEY_MISMATCH"
    KEY_NOT_AUTHORIZED_FOR_STAGE = "KEY_NOT_AUTHORIZED_FOR_STAGE"
    PAYLOAD_DIGEST_MISMATCH = "PAYLOAD_DIGEST_MISMATCH"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    ROLLBACK_BLOCKED = "ROLLBACK_BLOCKED"
    ACCEPTED = "ACCEPTED"

    # --- Fuses and monotonic counters ---------------------------------------
    COUNTER_MONOTONICITY_VIOLATION = "COUNTER_MONOTONICITY_VIOLATION"
    COUNTER_EXHAUSTED = "COUNTER_EXHAUSTED"
    NO_PENDING_ADVANCE = "NO_PENDING_ADVANCE"
    FUSE_ALREADY_BURNED = "FUSE_ALREADY_BURNED"
    FACTORY_RESET_REFUSED = "FACTORY_RESET_REFUSED"

    # --- Everything else ----------------------------------------------------
    ALGO_BACKEND_UNAVAILABLE = "ALGO_BACKEND_UNAVAILABLE"
    KEY_SLOT_MISSING = "KEY_SLOT_MISSING"
    AUDIT_CHAIN_BROKEN = "AUDIT_CHAIN_BROKEN"
    ATTESTATION_MISMATCH = "ATTESTATION_MISMATCH"


#: The sixteen verification outcomes in the order the verifier evaluates them.
#: Cheap and structural checks come before expensive and cryptographic ones, so
#: a malformed buffer is rejected without ever reaching a signature operation.
#: ``tests/test_verify_order.py`` walks this tuple and proves each code is
#: individually reachable and that no later check ran.
VERIFY_ORDER: tuple[ReasonCode, ...] = (
    ReasonCode.IMAGE_TOO_SHORT,
    ReasonCode.BAD_MAGIC,
    ReasonCode.UNSUPPORTED_HEADER_VERSION,
    ReasonCode.RESERVED_NOT_ZERO,
    ReasonCode.HEADER_CRC_MISMATCH,
    ReasonCode.WRONG_STAGE_ID,
    ReasonCode.LENGTH_OVERFLOW,
    ReasonCode.SECURE_BOOT_DISABLED,
    ReasonCode.UNKNOWN_ALGO,
    ReasonCode.ALGO_NOT_PERMITTED,
    ReasonCode.KEY_ID_REVOKED,
    ReasonCode.ROOT_KEY_MISMATCH,
    ReasonCode.KEY_NOT_AUTHORIZED_FOR_STAGE,
    ReasonCode.PAYLOAD_DIGEST_MISMATCH,
    ReasonCode.SIGNATURE_INVALID,
    ReasonCode.ROLLBACK_BLOCKED,
    ReasonCode.ACCEPTED,
)


#: One line per code, shown by the CLI next to a rejection so the operator sees
#: which control fired rather than only its name.
EXPLANATION: dict[ReasonCode, str] = {
    ReasonCode.IMAGE_TOO_SHORT: "buffer is smaller than the fixed 128-byte header",
    ReasonCode.BAD_MAGIC: "container magic is not SBI1 — this is not a boot image",
    ReasonCode.UNSUPPORTED_HEADER_VERSION: "header version is not one this ROM can parse",
    ReasonCode.RESERVED_NOT_ZERO: "reserved header bytes are non-zero (forward-compatibility trap)",
    ReasonCode.HEADER_CRC_MISMATCH: "header CRC32 does not match — corruption detected early",
    ReasonCode.WRONG_STAGE_ID: "image is for a different boot stage (stage-confusion attack)",
    ReasonCode.LENGTH_OVERFLOW: "declared lengths do not fit the buffer",
    ReasonCode.SECURE_BOOT_DISABLED: "the secure-boot enable fuse is not burned",
    ReasonCode.UNKNOWN_ALGO: "algorithm identifier is not one this verifier implements",
    ReasonCode.ALGO_NOT_PERMITTED: "algorithm is not on the machine's policy allowlist",
    ReasonCode.KEY_ID_REVOKED: "the signing key ID is set in the fuse revocation bitmap",
    ReasonCode.ROOT_KEY_MISMATCH: "signer public key does not hash to the root key hash in fuses",
    ReasonCode.KEY_NOT_AUTHORIZED_FOR_STAGE: (
        "signer is not on the bootloader's app-signer allowlist"
    ),
    ReasonCode.PAYLOAD_DIGEST_MISMATCH: "payload does not match the digest in the signed header",
    ReasonCode.SIGNATURE_INVALID: "signature does not verify over header and payload",
    ReasonCode.ROLLBACK_BLOCKED: "security version number is behind the monotonic counter",
    ReasonCode.ACCEPTED: "every control passed",
    ReasonCode.COUNTER_MONOTONICITY_VIOLATION: (
        "attempt to write a counter to an equal or lower value"
    ),
    ReasonCode.COUNTER_EXHAUSTED: "the counter substrate has no advances left",
    ReasonCode.NO_PENDING_ADVANCE: "there is no staged counter advance to confirm",
    ReasonCode.FUSE_ALREADY_BURNED: "an OTP fuse is write-once and has already been burned",
    ReasonCode.FACTORY_RESET_REFUSED: "factory reset is refused in the PRODUCTION lifecycle state",
    ReasonCode.ALGO_BACKEND_UNAVAILABLE: (
        "the installed crypto backend cannot perform this algorithm"
    ),
    ReasonCode.KEY_SLOT_MISSING: "no key exists in the requested HSM slot",
    ReasonCode.AUDIT_CHAIN_BROKEN: "the audit log hash chain does not verify",
    ReasonCode.ATTESTATION_MISMATCH: "a PCR differs from the golden reference",
}
