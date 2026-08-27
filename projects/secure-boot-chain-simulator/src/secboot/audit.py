"""A tamper-evident audit log.

Models the security event log an ECU keeps for incident response. Two design
choices carry the weight:

* **Every decision is logged, including the ones that pass.** A log that only
  records failures cannot answer "what was running on this vehicle in March",
  which is the question an incident actually asks.
* **The records are hash-chained.** Each record carries the hash of the one
  before it, so editing any record invalidates every hash after it. That does
  not make the log un-editable — an attacker with write access can rewrite the
  whole file — but it makes a *quiet* edit impossible, and combined with
  periodic off-board upload of the head hash it makes any edit detectable.

Format is JSON Lines, append-only: a line per event, so a truncated write costs
one record rather than the file.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .reasons import ReasonCode

#: The chain's anchor. A real device would seed this from a value in OTP so the
#: log cannot be replaced wholesale with a shorter, valid-looking one.
GENESIS_HASH = "0" * 64


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical(record: dict[str, Any]) -> bytes:
    """The exact bytes hashed. Sorted keys and no incidental whitespace, so two
    implementations agree on the digest."""
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def chain_hash(prev_hash: str, record: dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(prev_hash.encode("ascii") + canonical(body)).hexdigest()


@dataclass(frozen=True)
class ChainStatus:
    """Where the chain broke, if it did."""

    ok: bool
    records: int
    broken_seq: int | None = None
    reason: ReasonCode = ReasonCode.ACCEPTED
    detail: str = ""


class AuditLog:
    """Append-only JSONL with a hash chain over the records."""

    def __init__(self, path: Path, clock: Callable[[], str] = _utc_now) -> None:
        self._path = path
        self._clock = clock

    @property
    def path(self) -> Path:
        return self._path

    def records(self) -> Iterator[dict[str, Any]]:
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield json.loads(line)

    def head(self) -> tuple[int, str]:
        """The next sequence number and the hash to chain from."""
        seq, prev = 0, GENESIS_HASH
        for record in self.records():
            seq = int(record["seq"]) + 1
            prev = str(record["hash"])
        return seq, prev

    def append(
        self,
        *,
        stage: str,
        event: str,
        decision: str,
        reason: ReasonCode | None = None,
        detail: dict[str, Any] | None = None,
        key_id: int | None = None,
        measurement: str | None = None,
        pcr: str | None = None,
        severity: str = "INFO",
    ) -> dict[str, Any]:
        """Write one event and return it.

        `decision` is ACCEPT, REJECT, HALT or INFO; `reason` is the stable code a
        service tool looks up. Both are present because the decision is what an
        operator reads and the reason is what a script matches on.
        """
        seq, prev = self.head()
        record: dict[str, Any] = {
            "seq": seq,
            "ts": self._clock(),
            "stage": stage,
            "event": event,
            "decision": decision,
            "severity": severity,
            "reason": str(reason) if reason is not None else None,
            "detail": detail or {},
            "key_id": key_id,
            "measurement": measurement,
            "pcr": pcr,
            "prev_hash": prev,
        }
        record["hash"] = chain_hash(prev, record)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def verify(self) -> ChainStatus:
        """Walk the chain and name the exact sequence number that broke it."""
        prev = GENESIS_HASH
        count = 0
        for expected_seq, record in enumerate(self.records()):
            count = expected_seq + 1
            if int(record.get("seq", -1)) != expected_seq:
                return ChainStatus(
                    False,
                    count,
                    broken_seq=expected_seq,
                    reason=ReasonCode.AUDIT_CHAIN_BROKEN,
                    detail=(
                        f"sequence number jumped to {record.get('seq')}, expected {expected_seq}"
                    ),
                )
            if record.get("prev_hash") != prev:
                return ChainStatus(
                    False,
                    count,
                    broken_seq=expected_seq,
                    reason=ReasonCode.AUDIT_CHAIN_BROKEN,
                    detail="prev_hash does not match the previous record's hash",
                )
            if chain_hash(prev, record) != record.get("hash"):
                return ChainStatus(
                    False,
                    count,
                    broken_seq=expected_seq,
                    reason=ReasonCode.AUDIT_CHAIN_BROKEN,
                    detail="record contents do not match their recorded hash",
                )
            prev = str(record["hash"])
        return ChainStatus(True, count)

    def tamper(self, seq: int, field_name: str = "reason", value: str = "ACCEPTED") -> bool:
        """Edit one record in place, leaving its hash untouched.

        Demo-only, and the point of it: this is what an attacker who wants the
        log to say the boot was clean would do, and `verify()` names the exact
        record they touched.
        """
        rows = list(self.records())
        for row in rows:
            if int(row["seq"]) == seq:
                row[field_name] = value
                self._path.write_text(
                    "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8"
                )
                return True
        return False

    def tail(self, count: int = 20) -> list[dict[str, Any]]:
        return list(self.records())[-count:]
