"""The audit log: every decision recorded, and no quiet edit possible."""

from __future__ import annotations

from pathlib import Path

from conftest import Bench
from secboot.audit import GENESIS_HASH, AuditLog
from secboot.reasons import ReasonCode


def test_passing_decisions_are_logged_too(bench: Bench) -> None:
    """A log that only records failures cannot answer "what was running"."""
    bench.boot()
    decisions = {record["decision"] for record in bench.machine.audit.records()}
    assert "ACCEPT" in decisions
    assert {"PASS", "INFO"} & decisions


def test_a_rejection_records_the_reason_and_the_counter_state(bench: Bench) -> None:
    bench.boot()
    bench.machine.confirm_boot()
    from secboot import attacks

    bench.boot(app=attacks.downgrade(bench.machine.hsm, bench.app, slot=1, svn=1))
    rejection = [r for r in bench.machine.audit.records() if r["decision"] == "REJECT"][-1]
    assert rejection["reason"] == ReasonCode.ROLLBACK_BLOCKED
    assert rejection["detail"]["counter_svn"] == 7


def test_the_chain_verifies_on_a_clean_log(bench: Bench) -> None:
    bench.boot()
    status = bench.machine.audit.verify()
    assert status.ok and status.records > 0


def test_a_single_byte_edit_is_caught_at_its_sequence_number(bench: Bench) -> None:
    bench.boot()
    log = bench.machine.audit
    target = 2
    assert log.tamper(target, "stage", "TAMPERED")

    status = log.verify()
    assert not status.ok
    assert status.broken_seq == target
    assert status.reason is ReasonCode.AUDIT_CHAIN_BROKEN


def test_deleting_a_record_is_caught(bench: Bench) -> None:
    """Removing an inconvenient line breaks the sequence, not only the hashes."""
    bench.boot()
    path = bench.machine.audit.path
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:2] + lines[3:]) + "\n", encoding="utf-8")
    assert bench.machine.audit.verify().broken_seq == 2


def test_the_chain_starts_from_a_known_anchor(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    first = log.append(stage="ROM", event="RESET", decision="INFO")
    assert first["prev_hash"] == GENESIS_HASH
    second = log.append(stage="ROM", event="RESET", decision="INFO")
    assert second["prev_hash"] == first["hash"]


def test_tampering_with_a_missing_record_is_a_no_op(tmp_path: Path) -> None:
    assert not AuditLog(tmp_path / "audit.jsonl").tamper(99)


def test_tail_returns_the_most_recent_events(bench: Bench) -> None:
    bench.boot()
    tail = bench.machine.audit.tail(3)
    assert len(tail) == 3
    assert tail[-1]["seq"] == max(r["seq"] for r in bench.machine.audit.records())
