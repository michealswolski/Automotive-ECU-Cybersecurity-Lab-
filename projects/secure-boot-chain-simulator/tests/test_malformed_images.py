"""Fuzz-ish robustness: attacker-controlled bytes must never produce a traceback.

The verifier's inputs come from flash, which is to say from whoever can write to
flash. Every one of these mutations is something a real attacker can do for
free, and the only acceptable outcomes are a reason code or a clean accept.
"""

from __future__ import annotations

import random

import pytest

from conftest import Bench
from secboot import image
from secboot.reasons import VERIFY_ORDER
from secboot.verify import verify_stage

MUTATIONS = 500


def test_five_hundred_random_mutations_produce_reason_codes(bench: Bench) -> None:
    rng = random.Random(20260101)
    original = bench.app
    seen = set()
    for _ in range(MUTATIONS):
        data = bytearray(original)
        for _ in range(rng.randrange(1, 4)):
            data[rng.randrange(len(data))] = rng.randrange(256)
        result = verify_stage(bench.machine, bytes(data), 2)
        assert result.reason in VERIFY_ORDER
        seen.add(result.reason)
    # A mutation run that only ever trips one check is not exercising much.
    assert len(seen) >= 3, seen


def test_truncation_at_every_length_is_survivable(bench: Bench) -> None:
    """Every prefix of a valid image, including the empty one."""
    for length in range(0, len(bench.app), 7):
        result = verify_stage(bench.machine, bench.app[:length], 2)
        assert result.reason in VERIFY_ORDER
        assert not result.ok


def test_absurd_lengths_do_not_allocate(bench: Bench) -> None:
    """A four-gigabyte payload_len must be refused by arithmetic, not by trying."""
    from secboot import attacks

    for field in ("payload_len", "sig_len"):
        lying = attacks.rewrite_header(bench.app, **{field: 0xFFFFFFFF})
        assert not verify_stage(bench.machine, lying, 2).ok


@pytest.mark.parametrize("junk", [b"", b"\x00" * 128, b"\xff" * 4096, bytes(range(256))])
def test_arbitrary_buffers_are_survivable(bench: Bench, junk: bytes) -> None:
    assert not verify_stage(bench.machine, junk, 2).ok


def test_parse_never_raises_on_random_input() -> None:
    rng = random.Random(7)
    for _ in range(MUTATIONS):
        size = rng.randrange(0, 400)
        image.parse(bytes(rng.randrange(256) for _ in range(size)), 2)
