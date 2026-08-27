"""Measured boot: a simulated PCR bank and an attestation quote.

Verified boot **blocks** — a bad image never runs. Measured boot **records** —
whatever ran, ran, and there is now a value that proves what it was. Production
designs use both, because verified boot cannot tell a remote party *which* good
image booted, and measured boot cannot stop a bad one.

A caveat this module is careful about: the TCG PCR-extend model being emulated
here comes from the TPM world, and most automotive HSMs are SHE or EVITA class,
not TPMs. There is no dominant automotive attestation standard yet. NIST SP
800-155 and the TCG extend construction are the model, not a claim of
conformance. See docs/verified-vs-measured-boot.md.

The extend operation is the whole idea:

    PCR[n] = SHA256(PCR[n] || measurement)

It is one-way and order-dependent, so a stage cannot un-measure itself, and two
stages measured in the wrong order produce a different bank.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

PCR_COUNT = 4
PCR_LEN = 32

#: What each register is reserved for. Fixed allocations, as in a real design:
#: a remote verifier has to know what a register means before it can compare it.
PCR_PURPOSE = {
    0: "BootROM configuration — the fuse state digest",
    1: "SBL image measurement",
    2: "Application image measurement",
    3: "Policy digest — allowed algorithms and revocation bitmap",
}


@dataclass
class PcrBank:
    """Four registers that only ever move forward."""

    registers: list[bytes] = field(
        default_factory=lambda: [b"\x00" * PCR_LEN for _ in range(PCR_COUNT)]
    )

    def extend(self, index: int, measurement: bytes) -> bytes:
        """Fold a measurement into a register. There is no way back out."""
        if not 0 <= index < PCR_COUNT:
            raise ValueError(f"no PCR {index}")
        self.registers[index] = hashlib.sha256(self.registers[index] + measurement).digest()
        return self.registers[index]

    def extend_data(self, index: int, data: bytes) -> bytes:
        """Extend with the SHA-256 of arbitrary data, for callers that hold the
        thing rather than its digest."""
        return self.extend(index, hashlib.sha256(data).digest())

    def read(self, index: int) -> bytes:
        return self.registers[index]

    def as_dict(self) -> dict[str, str]:
        return {f"pcr{i}": r.hex() for i, r in enumerate(self.registers)}


def quote_body(bank: PcrBank, nonce: str) -> bytes:
    """The bytes an attestation key signs.

    The nonce is what makes a quote a statement about *now* rather than a
    replayable recording; a challenger supplies it.
    """
    return json.dumps({"nonce": nonce, "pcrs": bank.as_dict()}, sort_keys=True).encode("utf-8")


@dataclass(frozen=True)
class QuoteDiff:
    """The result of comparing a quote against a golden reference."""

    matches: bool
    diverged: list[int]

    def describe(self) -> str:
        if self.matches:
            return "every PCR matches the golden reference"
        parts = [f"PCR{i} ({PCR_PURPOSE[i].split(' — ')[0]})" for i in self.diverged]
        return "diverged: " + ", ".join(parts)


def diff_quotes(actual: dict[str, str], golden: dict[str, str]) -> QuoteDiff:
    """Which registers differ, so the operator learns *which stage* changed
    rather than only that something did."""
    diverged = [i for i in range(PCR_COUNT) if actual.get(f"pcr{i}") != golden.get(f"pcr{i}")]
    return QuoteDiff(matches=not diverged, diverged=diverged)
