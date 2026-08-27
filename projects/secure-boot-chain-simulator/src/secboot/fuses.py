"""OTP fuses and monotonic counters — the hardware root of trust.

Two different kinds of one-way state are modelled here, and the difference
matters:

* **OTP fuses** are write-once bits burned at production. Once burned they
  cannot be un-burned, which is why `root_key_hash` lives here: an attacker with
  full write access to flash still cannot point the ROM at their own key.
* **Monotonic counters** can be advanced but never lowered. They are what makes
  a *validly signed* old image unbootable, which signature verification alone
  can never do.

The API is deliberately hostile to misuse. There is no `set()` and no `reset()`
in the production surface — only `advance(name, to)`, which refuses anything not
strictly greater than the current value. The one escape hatch, `factory_reset`,
is refused in the PRODUCTION lifecycle state and logs a critical event.

Counter substrates are modelled because they behave differently in the field:
an eFuse counter is thermometer-coded across a fixed number of fuse bits and
genuinely runs out, while a replay-protected flash counter is a 32-bit value
whose monotonicity is enforced by the storage protocol rather than by physics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from .reasons import ReasonCode

#: A 32-bit counter refuses to advance past this, so that "at maximum" is a
#: state the code has to handle rather than an overflow.
COUNTER_MAX = 0xFFFFFFFE
#: Fuse bits available to a thermometer-coded eFuse counter. Small on purpose:
#: exhaustion is a real constraint on how many security updates a part can take.
EFUSE_BITS = 64


class Lifecycle(StrEnum):
    """SHE/EVITA-style lifecycle states, simplified to the three that change
    what the ROM will allow."""

    VIRGIN = "VIRGIN"
    DEVELOPMENT = "DEVELOPMENT"
    PRODUCTION = "PRODUCTION"


class Substrate(StrEnum):
    """Where a monotonic counter physically lives."""

    OTP_EFUSE = "otp-efuse"
    SECURED_FLASH = "secured-flash"


@dataclass(frozen=True)
class FuseResult:
    """Errors are values here too, so the CLI can print a reason code."""

    reason: ReasonCode
    detail: dict[str, object] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.reason is ReasonCode.ACCEPTED


@dataclass
class Counter:
    """One monotonic counter."""

    value: int = 0
    #: Staged advance, not yet permanent. See `Fuses.confirm_pending`.
    pending: int | None = None
    substrate: Substrate = Substrate.OTP_EFUSE
    #: Fuse bits already burned. Only meaningful for OTP_EFUSE.
    burned_bits: int = 0

    def headroom(self) -> int:
        """Advances still physically available."""
        if self.substrate is Substrate.OTP_EFUSE:
            return EFUSE_BITS - self.burned_bits
        return COUNTER_MAX - self.value


class Fuses:
    """The one-time-programmable region plus the counter bank.

    Persisted to a JSON file so that a rollback attempt survives a process
    restart — a counter that resets when the demo restarts proves nothing.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self.root_key_hash: str | None = None
        self.secure_boot_enable: bool = False
        self.lifecycle: Lifecycle = Lifecycle.VIRGIN
        #: One bit per key ID. Burned, so revocation is irreversible — which is
        #: exactly why revoking a key in production is a serious decision.
        self.revoked_key_ids: int = 0
        self.counters: dict[str, Counter] = {
            "svn_sbl": Counter(substrate=Substrate.OTP_EFUSE),
            "svn_app": Counter(substrate=Substrate.SECURED_FLASH),
        }
        if path.exists():
            self._load()

    # --- persistence --------------------------------------------------------

    def _load(self) -> None:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        self.root_key_hash = raw.get("root_key_hash")
        self.secure_boot_enable = raw.get("secure_boot_enable", False)
        self.lifecycle = Lifecycle(raw.get("lifecycle", Lifecycle.VIRGIN))
        self.revoked_key_ids = raw.get("revoked_key_ids", 0)
        for name, entry in raw.get("counters", {}).items():
            self.counters[name] = Counter(
                value=entry["value"],
                pending=entry.get("pending"),
                substrate=Substrate(entry.get("substrate", Substrate.OTP_EFUSE)),
                burned_bits=entry.get("burned_bits", 0),
            )

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {
                    "root_key_hash": self.root_key_hash,
                    "secure_boot_enable": self.secure_boot_enable,
                    "lifecycle": str(self.lifecycle),
                    "revoked_key_ids": self.revoked_key_ids,
                    "counters": {
                        name: {
                            "value": counter.value,
                            "pending": counter.pending,
                            "substrate": str(counter.substrate),
                            "burned_bits": counter.burned_bits,
                        }
                        for name, counter in self.counters.items()
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    # --- one-time-programmable region ---------------------------------------

    def burn_root_key_hash(self, digest_hex: str) -> FuseResult:
        """Burn the SHA-256 of the root public key. Write-once, by definition.

        Storing a 32-byte hash rather than the key itself is the standard
        pattern: OTP area is expensive, and a hash is all the ROM needs to
        authenticate the key that travels inside the image.
        """
        if self.root_key_hash is not None:
            return FuseResult(ReasonCode.FUSE_ALREADY_BURNED, {"fuse": "root_key_hash"})
        self.root_key_hash = digest_hex
        self.save()
        return FuseResult(ReasonCode.ACCEPTED)

    def enable_secure_boot(self) -> FuseResult:
        if self.secure_boot_enable:
            return FuseResult(ReasonCode.FUSE_ALREADY_BURNED, {"fuse": "secure_boot_enable"})
        self.secure_boot_enable = True
        self.save()
        return FuseResult(ReasonCode.ACCEPTED)

    def set_lifecycle(self, state: Lifecycle) -> FuseResult:
        """Lifecycle only ever moves forward: VIRGIN, DEVELOPMENT, PRODUCTION."""
        order = [Lifecycle.VIRGIN, Lifecycle.DEVELOPMENT, Lifecycle.PRODUCTION]
        if order.index(state) <= order.index(self.lifecycle):
            return FuseResult(
                ReasonCode.FUSE_ALREADY_BURNED,
                {"lifecycle": str(self.lifecycle), "requested": str(state)},
            )
        self.lifecycle = state
        self.save()
        return FuseResult(ReasonCode.ACCEPTED)

    def revoke_key(self, key_id: int) -> FuseResult:
        """Burn the revocation bit for one key ID. Irreversible."""
        if key_id < 0 or key_id > 63:
            return FuseResult(ReasonCode.KEY_SLOT_MISSING, {"key_id": key_id})
        self.revoked_key_ids |= 1 << key_id
        self.save()
        return FuseResult(ReasonCode.ACCEPTED)

    def is_revoked(self, key_id: int) -> bool:
        if key_id < 0 or key_id > 63:
            return True
        return bool(self.revoked_key_ids & (1 << key_id))

    # --- monotonic counters -------------------------------------------------

    def read(self, name: str) -> int:
        """The permanent value. Never includes a pending advance."""
        return self.counters[name].value

    def pending(self, name: str) -> int | None:
        return self.counters[name].pending

    def advance(self, name: str, to: int) -> FuseResult:
        """The only way a counter's value ever changes.

        Refuses anything not strictly greater than the current value, which is
        what makes rollback protection meaningful. There is no companion setter:
        the absence of one is the security property.
        """
        counter = self.counters[name]
        if to <= counter.value:
            return FuseResult(
                ReasonCode.COUNTER_MONOTONICITY_VIOLATION,
                {"counter": name, "current": counter.value, "requested": to},
            )
        if to > COUNTER_MAX or counter.headroom() <= 0:
            return FuseResult(
                ReasonCode.COUNTER_EXHAUSTED,
                {
                    "counter": name,
                    "substrate": str(counter.substrate),
                    "headroom": counter.headroom(),
                },
            )
        counter.value = to
        if counter.substrate is Substrate.OTP_EFUSE:
            counter.burned_bits += 1
        counter.pending = None
        self.save()
        return FuseResult(ReasonCode.ACCEPTED)

    def stage_advance(self, name: str, to: int) -> FuseResult:
        """Record an advance without committing it.

        This is the safer half of the counter-timing tradeoff (ADR-0002).
        Burning the counter the moment a new image verifies bricks the ECU if
        that image is signed but broken, because the known-good older image is
        now below the counter. Staging it and requiring `confirm-boot` — which
        models a watchdog or a health-check reporting a successful application
        start — keeps the old image bootable until the new one has proven it can
        run.
        """
        counter = self.counters[name]
        if to <= counter.value:
            return FuseResult(
                ReasonCode.COUNTER_MONOTONICITY_VIOLATION,
                {"counter": name, "current": counter.value, "requested": to},
            )
        counter.pending = to
        self.save()
        return FuseResult(ReasonCode.ACCEPTED, {"counter": name, "pending": to})

    def confirm_pending(self) -> list[FuseResult]:
        """Commit every staged advance. Models the health-check confirmation."""
        results: list[FuseResult] = []
        staged = [(name, c.pending) for name, c in self.counters.items() if c.pending is not None]
        if not staged:
            return [FuseResult(ReasonCode.NO_PENDING_ADVANCE)]
        for name, target in staged:
            assert target is not None
            results.append(self.advance(name, target))
        return results

    def factory_reset(self) -> FuseResult:
        """Demo-only escape hatch. Refused once the part is in PRODUCTION.

        A real part has no such command; this exists so the demo can be re-run,
        and it is here rather than in the counter API precisely so that the
        production surface stays free of it.
        """
        if self.lifecycle is Lifecycle.PRODUCTION:
            return FuseResult(ReasonCode.FACTORY_RESET_REFUSED, {"lifecycle": str(self.lifecycle)})
        if self._path.exists():
            self._path.unlink()
        self.__init__(self._path)  # type: ignore[misc]
        return FuseResult(ReasonCode.ACCEPTED)

    def state_digest_input(self) -> str:
        """A canonical rendering of the fuse state, measured into PCR0."""
        return json.dumps(
            {
                "root_key_hash": self.root_key_hash,
                "secure_boot_enable": self.secure_boot_enable,
                "lifecycle": str(self.lifecycle),
                "revoked_key_ids": self.revoked_key_ids,
            },
            sort_keys=True,
        )
