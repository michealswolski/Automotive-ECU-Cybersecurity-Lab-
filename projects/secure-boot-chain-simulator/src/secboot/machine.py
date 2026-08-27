"""The ECU: everything the boot chain needs, and the orchestration itself.

`Machine` is the context object the rest of the package is written against.
Nothing here is global mutable state — a test constructs a machine in a
temporary directory and gets a whole independent ECU, which is what makes the
attack scenarios reproducible.

The boot sequence is the one a real part follows:

    reset  ->  measure fuses and policy  ->  ROM verifies SBL  ->  load SBL
           ->  SBL verifies APP  ->  load APP  ->  application confirms health

with the two things that catch what verification alone cannot: every stage is
*measured* into the PCR bank whether or not anyone asks, and the bytes that are
actually loaded are re-checked against the bytes that were verified.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .audit import AuditLog
from .fuses import Fuses
from .hsm import Hsm, Usage
from .image import STAGE_APP, STAGE_NAMES, STAGE_SBL
from .measure import PcrBank, diff_quotes, quote_body
from .policy import Policy
from .reasons import ReasonCode
from .verify import COUNTER_FOR_STAGE, VerifyResult, verify_stage

#: PCR allocation. Fixed, because a remote verifier has to know what each
#: register means before it can compare one.
PCR_FUSES = 0
PCR_SBL = 1
PCR_APP = 2
PCR_POLICY = 3
PCR_FOR_STAGE = {STAGE_SBL: PCR_SBL, STAGE_APP: PCR_APP}

#: The HSM slot holding the attestation key. Separate from any signing key: a
#: key that can both sign firmware and sign attestations lets whoever can ask
#: for a quote also ask for a firmware signature.
ATTEST_SLOT = 15


@dataclass
class Fault:
    """A simulated physical attack.

    Voltage and clock glitching against the instruction that consumes a
    comparison result is the classic way to defeat secure boot without breaking
    any cryptography. Modelling it is worth the twenty lines: it is what shows
    why measured boot earns its place next to verified boot.
    """

    force_signature_pass: bool = False
    #: Swap the loaded bytes after verification succeeded — a time-of-check to
    #: time-of-use attack against DMA or shared flash.
    toctou_payload: bytes | None = None
    toctou_stage: int = STAGE_APP


@dataclass
class StageResult:
    """What happened at one stage of the chain."""

    stage_id: int
    verify: VerifyResult
    loaded: bool = False
    measurement: str | None = None
    pcr: str | None = None
    staged_svn: int | None = None

    @property
    def stage_name(self) -> str:
        return STAGE_NAMES.get(self.stage_id, str(self.stage_id))


@dataclass
class BootResult:
    """The whole chain."""

    stages: list[StageResult] = field(default_factory=list)
    booted: bool = False
    halted_at: int | None = None
    reason: ReasonCode = ReasonCode.ACCEPTED
    hsm_operations: int = 0

    @property
    def failing(self) -> StageResult | None:
        return next((s for s in self.stages if not s.verify.ok), None)


class Machine:
    """One simulated ECU."""

    def __init__(
        self,
        state_dir: Path,
        *,
        policy: Policy | None = None,
        passphrase: str | None = None,
        hsm_latency_ms: float = 0.0,
        clock: Callable[[], str] | None = None,
        kdf_n: int | None = None,
    ) -> None:
        self.state_dir = state_dir
        state_dir.mkdir(parents=True, exist_ok=True)
        self.fuses = Fuses(state_dir / "fuses.json")
        hsm_kwargs: dict[str, Any] = {"latency_ms": hsm_latency_ms}
        if passphrase is not None:
            hsm_kwargs["passphrase"] = passphrase
        if kdf_n is not None:
            hsm_kwargs["kdf_n"] = kdf_n
        self.hsm = Hsm(state_dir / "keystore.json", **hsm_kwargs)
        self.audit = AuditLog(state_dir / "audit.jsonl", **({"clock": clock} if clock else {}))
        self.policy = policy if policy is not None else self._load_policy()
        self.pcr = PcrBank()
        self.fault: Fault | None = None

    # --- policy persistence -------------------------------------------------
    #
    # Policy is device configuration, so it survives a restart like the fuses
    # do. It is *not* in OTP: an app-signer allowlist that could never change
    # would make key rotation impossible.

    @property
    def _policy_path(self) -> Path:
        return self.state_dir / "policy.json"

    def _load_policy(self) -> Policy:
        policy = Policy()
        if self._policy_path.exists():
            raw = json.loads(self._policy_path.read_text(encoding="utf-8"))
            from .algo import Algo  # noqa: PLC0415 - avoids an import cycle at module load

            policy.allowed_algos = {Algo(a) for a in raw["allowed_algos"]}
            policy.app_signer_hashes = set(raw["app_signer_hashes"])
            policy.allow_insecure = raw["allow_insecure"]
            policy.require_boot_confirmation = raw["require_boot_confirmation"]
        return policy

    def save_policy(self) -> None:
        self._policy_path.write_text(
            json.dumps(
                {
                    "allowed_algos": sorted(int(a) for a in self.policy.allowed_algos),
                    "app_signer_hashes": sorted(self.policy.app_signer_hashes),
                    "allow_insecure": self.policy.allow_insecure,
                    "require_boot_confirmation": self.policy.require_boot_confirmation,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    # --- boot ---------------------------------------------------------------

    def reset(self) -> None:
        """Power-on reset: a fresh PCR bank, then the two measurements the ROM
        makes before it looks at any image.

        Measuring the fuse state and the policy *first* is what makes the rest
        of the bank meaningful. A quote that says "these images booted" without
        saying "under this policy, on a part with these fuses" is missing the
        half an attacker would change.
        """
        self.pcr = PcrBank()
        self.pcr.extend_data(PCR_FUSES, self.fuses.state_digest_input().encode("utf-8"))
        self.pcr.extend_data(PCR_POLICY, self.policy.digest_input().encode("utf-8"))
        self.audit.append(
            stage="ROM",
            event="RESET",
            decision="INFO",
            reason=ReasonCode.ACCEPTED,
            detail={
                "lifecycle": str(self.fuses.lifecycle),
                "secure_boot_enable": self.fuses.secure_boot_enable,
                "svn_sbl": self.fuses.read("svn_sbl"),
                "svn_app": self.fuses.read("svn_app"),
            },
            pcr=self.pcr.read(PCR_FUSES).hex(),
        )

    def boot(
        self,
        sbl_image: bytes,
        app_image: bytes,
        *,
        loader: Callable[[int, bytes], bytes] | None = None,
    ) -> BootResult:
        """Run the chain. Halts at the first rejection and never continues past it.

        `loader` models the copy from flash into RAM. It exists so a
        time-of-check-to-time-of-use attack is expressible: the bytes that get
        loaded are re-measured and compared against the bytes that were
        verified, so a swap in between is caught rather than assumed away.
        """
        self.reset()
        result = BootResult()
        for stage_id, image_bytes in ((STAGE_SBL, sbl_image), (STAGE_APP, app_image)):
            stage = self._run_stage(stage_id, image_bytes, loader)
            result.stages.append(stage)
            if not stage.verify.ok or not stage.loaded:
                result.halted_at = stage_id
                result.reason = stage.verify.reason
                self.audit.append(
                    stage=stage.stage_name,
                    event="HALT",
                    decision="HALT",
                    reason=stage.verify.reason,
                    detail={"note": "control was not transferred"},
                    severity="CRITICAL",
                )
                result.hsm_operations = self.hsm.operations
                return result

        result.booted = True
        result.hsm_operations = self.hsm.operations
        self.audit.append(
            stage="APP",
            event="BOOT",
            decision="ACCEPT",
            reason=ReasonCode.ACCEPTED,
            detail={"pcrs": self.pcr.as_dict()},
        )
        return result

    def _run_stage(
        self,
        stage_id: int,
        image_bytes: bytes,
        loader: Callable[[int, bytes], bytes] | None,
    ) -> StageResult:
        verdict = verify_stage(self, image_bytes, stage_id)
        stage = StageResult(stage_id=stage_id, verify=verdict)
        if not verdict.ok or verdict.image is None:
            return stage

        # Measure before loading. A stage that is measured only after it runs
        # can decline to measure itself.
        measurement = verdict.image.measurement()
        pcr_index = PCR_FOR_STAGE[stage_id]
        self.pcr.extend(pcr_index, measurement)
        stage.measurement = measurement.hex()
        stage.pcr = self.pcr.read(pcr_index).hex()
        self.audit.append(
            stage=stage.stage_name,
            event="MEASURE",
            decision="INFO",
            reason=ReasonCode.ACCEPTED,
            detail={"pcr_index": pcr_index},
            measurement=stage.measurement,
            pcr=stage.pcr,
        )

        loaded_bytes = self._load(stage_id, image_bytes, loader)
        if hashlib.sha256(loaded_bytes).digest() != hashlib.sha256(image_bytes).digest():
            # Time-of-check to time-of-use: what was loaded is not what was
            # verified. Re-checking at load time is the only place this is
            # visible, which is why the check is here and not in verify.py.
            stage.verify.ok = False
            stage.verify.reason = ReasonCode.PAYLOAD_DIGEST_MISMATCH
            stage.verify.detail = {
                "toctou": True,
                "note": "loaded bytes differ from verified bytes",
            }
            self.audit.append(
                stage=stage.stage_name,
                event="TOCTOU_RECHECK",
                decision="REJECT",
                reason=ReasonCode.PAYLOAD_DIGEST_MISMATCH,
                detail={"note": "image changed between verification and load"},
                severity="CRITICAL",
            )
            return stage

        stage.loaded = True
        counter_name = COUNTER_FOR_STAGE[stage_id]
        svn = verdict.image.header.svn
        if svn > self.fuses.read(counter_name):
            if self.policy.require_boot_confirmation:
                self.fuses.stage_advance(counter_name, svn)
                stage.staged_svn = svn
                self.audit.append(
                    stage=stage.stage_name,
                    event="COUNTER_STAGE",
                    decision="INFO",
                    reason=ReasonCode.ACCEPTED,
                    detail={"counter": counter_name, "pending": svn},
                )
            else:
                outcome = self.fuses.advance(counter_name, svn)
                self.audit.append(
                    stage=stage.stage_name,
                    event="COUNTER_ADVANCE",
                    decision="INFO" if outcome.ok else "REJECT",
                    reason=outcome.reason,
                    detail={"counter": counter_name, "to": svn},
                )
        return stage

    def _load(
        self,
        stage_id: int,
        image_bytes: bytes,
        loader: Callable[[int, bytes], bytes] | None,
    ) -> bytes:
        if (
            self.fault is not None
            and self.fault.toctou_payload is not None
            and self.fault.toctou_stage == stage_id
        ):
            return self.fault.toctou_payload
        if loader is not None:
            return loader(stage_id, image_bytes)
        return image_bytes

    # --- confirmation -------------------------------------------------------

    def confirm_boot(self) -> list[ReasonCode]:
        """Commit staged SVN advances. Models a health check reporting success.

        Until this runs the older image is still bootable, which is the whole
        reason the advance is staged rather than burned at verification time.
        """
        outcomes = self.fuses.confirm_pending()
        for outcome in outcomes:
            self.audit.append(
                stage="APP",
                event="CONFIRM_BOOT",
                decision="INFO" if outcome.ok else "REJECT",
                reason=outcome.reason,
                detail=dict(outcome.detail),
                severity="INFO" if outcome.ok else "WARN",
            )
        return [outcome.reason for outcome in outcomes]

    # --- attestation --------------------------------------------------------

    def attest(self, nonce: str = "0" * 32) -> dict[str, Any]:
        """Produce a signed statement about what booted.

        The quote is signed by a dedicated attestation key inside the HSM. If
        that key does not exist yet it is created here, with ATTEST usage only.
        """
        if not self.hsm.has_slot(ATTEST_SLOT):
            from .algo import Algo  # noqa: PLC0415 - avoids an import cycle at module load

            self.hsm.generate(ATTEST_SLOT, Algo.ECDSA_P256_SHA256, Usage.ATTEST)
        body = quote_body(self.pcr, nonce)
        signature = self.hsm.attest(ATTEST_SLOT, body)
        quote = {
            "nonce": nonce,
            "pcrs": self.pcr.as_dict(),
            "purposes": {f"pcr{i}": p for i, p in enumerate(_pcr_purposes())},
            "signature": signature.hex(),
            "attest_key": self.hsm.public_key(ATTEST_SLOT).hex(),
        }
        self.audit.append(
            stage="APP",
            event="ATTEST",
            decision="INFO",
            reason=ReasonCode.ACCEPTED,
            detail={"nonce": nonce},
        )
        return quote

    def verify_quote(self, quote: dict[str, Any], golden: dict[str, str]) -> tuple[bool, str]:
        """Check a quote's signature, then diff it against a golden PCR set."""
        from .algo import SPECS, Algo, verify_signature  # noqa: PLC0415 - import cycle

        spec = SPECS[Algo.ECDSA_P256_SHA256]
        body = json.dumps({"nonce": quote["nonce"], "pcrs": quote["pcrs"]}, sort_keys=True).encode(
            "utf-8"
        )
        if not verify_signature(
            spec,
            bytes.fromhex(quote["attest_key"]),
            bytes.fromhex(quote["signature"]),
            body,
        ):
            return False, "the quote's signature does not verify"
        difference = diff_quotes(quote["pcrs"], golden)
        return difference.matches, difference.describe()


def _pcr_purposes() -> list[str]:
    from .measure import PCR_COUNT, PCR_PURPOSE  # noqa: PLC0415 - keeps machine.py's imports flat

    return [PCR_PURPOSE[i] for i in range(PCR_COUNT)]
