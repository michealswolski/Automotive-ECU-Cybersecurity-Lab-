"""Shared fixtures: a provisioned ECU, an attacker, and a matched image pair.

Every test gets its own machine in its own temporary directory, so there is no
shared state to reset and no ordering dependency between tests.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from secboot.algo import Algo
from secboot.builder import sign_and_build
from secboot.fuses import Lifecycle
from secboot.machine import Machine
from secboot.policy import Policy

#: Scrypt is deliberately expensive in production. In tests it is called on
#: every keystore write, so the cost parameter is lowered here and only here.
TEST_KDF_N = 2**10

SBL_SVN = 3
APP_SVN = 7
SBL_PAYLOAD = b"<bootloader>" * 12
APP_PAYLOAD = b"<application>" * 12


@dataclass
class Bench:
    machine: Machine
    attacker: Machine
    sbl: bytes
    app: bytes

    def boot(self, sbl: bytes | None = None, app: bytes | None = None):  # type: ignore[no-untyped-def]
        return self.machine.boot(
            sbl if sbl is not None else self.sbl, app if app is not None else self.app
        )


def _machine(path: Path, policy: Policy | None = None) -> Machine:
    return Machine(path, policy=policy, kdf_n=TEST_KDF_N, clock=lambda: "2026-01-01T00:00:00.000Z")


@pytest.fixture
def bench(tmp_path: Path) -> Bench:
    policy = Policy(allowed_algos={Algo.ED25519, Algo.ECDSA_P384_SHA384})
    machine = _machine(tmp_path / "ecu", policy)
    machine.hsm.import_private(0, Algo.ED25519, b"\x01" * 32)
    machine.hsm.import_private(1, Algo.ED25519, b"\x02" * 32)
    machine.fuses.burn_root_key_hash(hashlib.sha256(machine.hsm.public_key(0)).hexdigest())
    machine.fuses.enable_secure_boot()
    machine.fuses.set_lifecycle(Lifecycle.DEVELOPMENT)
    machine.policy.authorize_app_signer(machine.hsm.public_key(1))
    machine.save_policy()

    attacker = _machine(tmp_path / "attacker")
    attacker.hsm.import_private(0, Algo.ED25519, b"\x03" * 32)

    return Bench(
        machine=machine,
        attacker=attacker,
        sbl=sign_and_build(machine.hsm, slot=0, stage_id=1, svn=SBL_SVN, payload=SBL_PAYLOAD),
        app=sign_and_build(machine.hsm, slot=1, stage_id=2, svn=APP_SVN, payload=APP_PAYLOAD),
    )
