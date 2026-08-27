"""The verifier — steps 8 to 16 of SPEC section 4, and the heart of the project.

Two properties are load-bearing and both are testable from the outside:

**Order.** Cheap and structural checks run before expensive and cryptographic
ones, and the verifier returns on the first failure. That is not only a
performance argument: attempting a signature check over lengths that have not
been validated is how bootloaders get exploited. Every check emits an audit
event as it runs, which makes the order *observable* — `test_verify_order.py`
asserts on the event sequence rather than on internal state.

**Errors are values.** Nothing on this path raises. A malformed image, a revoked
key and a stale SVN are all attacker-reachable inputs; a traceback on any of
them would be the bug.

Digest comparisons use `hmac.compare_digest`. On a boot verifier the timing
argument is weak — the attacker usually has the image — but the habit is not
optional and the cost is zero.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .algo import Algo, spec_for, verify_signature
from .image import STAGE_SBL, ParsedImage, parse
from .reasons import ReasonCode

if TYPE_CHECKING:  # pragma: no cover - import cycle only matters to type checkers
    from .machine import Machine

#: Which monotonic counter guards which stage.
COUNTER_FOR_STAGE = {1: "svn_sbl", 2: "svn_app"}


@dataclass
class VerifyResult:
    """The outcome of verifying one stage."""

    ok: bool
    reason: ReasonCode
    detail: dict[str, object] = field(default_factory=dict)
    image: ParsedImage | None = None
    #: Every check that actually ran, in order. What makes ordering observable.
    checks_run: list[ReasonCode] = field(default_factory=list)
    #: True when the stage was accepted only because the part is a development
    #: sample with the secure-boot fuse unburned.
    insecure: bool = False


def verify_stage(machine: Machine, image_bytes: bytes, expected_stage_id: int) -> VerifyResult:
    """Verify one boot stage. Never raises."""
    result = VerifyResult(ok=False, reason=ReasonCode.ACCEPTED)
    stage_name = {1: "SBL", 2: "APP"}.get(expected_stage_id, str(expected_stage_id))

    def check(code: ReasonCode) -> None:
        result.checks_run.append(code)

    def reject(code: ReasonCode, detail: dict[str, object]) -> VerifyResult:
        result.ok = False
        result.reason = code
        result.detail = detail
        machine.audit.append(
            stage=stage_name,
            event="VERIFY",
            decision="REJECT",
            reason=code,
            detail=detail,
            severity="ERROR",
        )
        return result

    # --- Steps 1 to 7: structure. Nothing cryptographic, nothing allocated
    #     from an attacker-supplied length until every length has been proven.
    for code in (
        ReasonCode.IMAGE_TOO_SHORT,
        ReasonCode.BAD_MAGIC,
        ReasonCode.UNSUPPORTED_HEADER_VERSION,
        ReasonCode.RESERVED_NOT_ZERO,
        ReasonCode.HEADER_CRC_MISMATCH,
        ReasonCode.WRONG_STAGE_ID,
        ReasonCode.LENGTH_OVERFLOW,
    ):
        check(code)
    parsed = parse(image_bytes, expected_stage_id)
    if not parsed.ok or parsed.image is None:
        # Truncate the record of checks run to the one that actually fired, so
        # the audit trail does not claim later structural checks were reached.
        fired = parsed.reason
        result.checks_run = result.checks_run[: result.checks_run.index(fired) + 1]
        return reject(fired, dict(parsed.detail or {}))

    image = parsed.image
    header = image.header
    result.image = image
    machine.audit.append(
        stage=stage_name,
        event="PARSE",
        decision="PASS",
        reason=ReasonCode.ACCEPTED,
        detail={"svn": header.svn, "algo_id": header.algo_id, "payload_len": header.payload_len},
        key_id=header.key_id,
    )

    # --- 8. Secure-boot enable fuse.
    check(ReasonCode.SECURE_BOOT_DISABLED)
    if not machine.fuses.secure_boot_enable:
        if not machine.policy.allow_insecure:
            return reject(ReasonCode.SECURE_BOOT_DISABLED, {"fuse": "secure_boot_enable"})
        result.insecure = True
        machine.audit.append(
            stage=stage_name,
            event="POLICY",
            decision="INFO",
            reason=ReasonCode.SECURE_BOOT_DISABLED,
            detail={"note": "development part booted with --allow-insecure"},
            severity="WARN",
        )

    # --- 9. Algorithm: known, then permitted. Two distinct failures, because
    #        "we cannot verify this" and "we refuse to verify this" are
    #        different findings for whoever reads the log.
    check(ReasonCode.UNKNOWN_ALGO)
    spec = spec_for(header.algo_id)
    if spec is None:
        return reject(ReasonCode.UNKNOWN_ALGO, {"algo_id": header.algo_id})

    check(ReasonCode.ALGO_NOT_PERMITTED)
    if Algo(header.algo_id) not in machine.policy.allowed_algos:
        return reject(
            ReasonCode.ALGO_NOT_PERMITTED,
            {
                "algo": spec.cli_name,
                "allowed": sorted(a.name for a in machine.policy.allowed_algos),
            },
        )

    # --- 10. Revocation, before any signature work: a revoked key's signature
    #         is still mathematically valid, so checking it would prove nothing
    #         and cost an HSM operation.
    check(ReasonCode.KEY_ID_REVOKED)
    if machine.fuses.is_revoked(header.key_id):
        return reject(ReasonCode.KEY_ID_REVOKED, {"key_id": header.key_id})

    actual_pubkey_hash = hashlib.sha256(image.signer_pubkey).hexdigest()

    # --- 11. Stage 1 only: the root of trust. The public key travels inside
    #         the image; what anchors it is the hash burned into OTP.
    check(ReasonCode.ROOT_KEY_MISMATCH)
    if expected_stage_id == STAGE_SBL:
        expected = machine.fuses.root_key_hash or ""
        header_claim = header.signer_pubkey_sha256.hex()
        if not hmac.compare_digest(actual_pubkey_hash, expected) or not hmac.compare_digest(
            actual_pubkey_hash, header_claim
        ):
            return reject(
                ReasonCode.ROOT_KEY_MISMATCH,
                {"fuse_root_key_hash": expected[:16], "image_signer": actual_pubkey_hash[:16]},
            )

    # --- 12. Stage 2: authority is delegated. The bootloader carries its own
    #         allowlist of app-signer hashes, so an application signing key can
    #         be rotated without touching a write-once fuse.
    check(ReasonCode.KEY_NOT_AUTHORIZED_FOR_STAGE)
    if expected_stage_id != STAGE_SBL:
        authorized = any(
            hmac.compare_digest(actual_pubkey_hash, allowed)
            for allowed in machine.policy.app_signer_hashes
        )
        consistent = hmac.compare_digest(actual_pubkey_hash, header.signer_pubkey_sha256.hex())
        if not authorized or not consistent:
            return reject(
                ReasonCode.KEY_NOT_AUTHORIZED_FOR_STAGE,
                {
                    "image_signer": actual_pubkey_hash[:16],
                    "authorized_signers": len(machine.policy.app_signer_hashes),
                },
            )

    # --- 13. Payload digest, from the signed header. Catches corruption before
    #         a signature operation is spent on it.
    check(ReasonCode.PAYLOAD_DIGEST_MISMATCH)
    computed = hashlib.sha256(image.payload).digest()
    if not hmac.compare_digest(computed, header.payload_sha256):
        return reject(
            ReasonCode.PAYLOAD_DIGEST_MISMATCH,
            {"header": header.payload_sha256.hex()[:16], "computed": computed.hex()[:16]},
        )

    # --- 14. The signature itself. On a real ECU this runs inside the HSM,
    #         which is why the boot-time budget is charged here.
    check(ReasonCode.SIGNATURE_INVALID)
    machine.hsm.simulate_operation()
    signature_ok = verify_signature(spec, image.signer_pubkey, image.signature, image.signed_data())
    if machine.fault is not None and machine.fault.force_signature_pass:
        # Models a voltage or clock glitch landing on the branch that consumes
        # the comparison result. The signature did not verify; the CPU acted as
        # though it had. Nothing downstream can detect this — which is the
        # point of also *measuring* the stage. See tests/test_glitch_toctou.py.
        machine.audit.append(
            stage=stage_name,
            event="FAULT_INJECTION",
            decision="INFO",
            reason=ReasonCode.SIGNATURE_INVALID,
            detail={"note": "simulated glitch forced the signature compare to pass"},
            severity="CRITICAL",
        )
        signature_ok = True
    if not signature_ok:
        return reject(
            ReasonCode.SIGNATURE_INVALID,
            {"algo": spec.cli_name, "key_id": header.key_id, "sig_len": header.sig_len},
        )

    # --- 15. Rollback. The signature is valid and the image is still refused,
    #         because freshness is a separate property from authenticity. This
    #         is the control most often missing from a real design.
    check(ReasonCode.ROLLBACK_BLOCKED)
    counter_name = COUNTER_FOR_STAGE[expected_stage_id]
    counter_svn = machine.fuses.read(counter_name)
    if header.svn < counter_svn:
        return reject(
            ReasonCode.ROLLBACK_BLOCKED,
            {"image_svn": header.svn, "counter_svn": counter_svn, "counter": counter_name},
        )

    # --- 16. Accept.
    check(ReasonCode.ACCEPTED)
    result.ok = True
    result.reason = ReasonCode.ACCEPTED
    result.detail = {"svn": header.svn, "counter_svn": counter_svn, "algo": spec.cli_name}
    machine.audit.append(
        stage=stage_name,
        event="VERIFY",
        decision="ACCEPT",
        reason=ReasonCode.ACCEPTED,
        detail=result.detail,
        key_id=header.key_id,
        measurement=image.measurement().hex(),
    )
    return result
