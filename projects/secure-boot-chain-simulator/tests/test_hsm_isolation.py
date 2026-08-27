"""The key custody boundary, enforced by a test rather than by convention.

Two independent checks, because they can fail separately:

1. **Static.** An AST scan proving no module outside the boundary so much as
   *names* a private-key attribute. A regex over the source would match strings
   and comments; walking the tree does not.
2. **Dynamic.** Every value the public API returns is compared against the real
   private key bytes, so a leak through an innocuous-looking accessor is caught
   even if it never mentions a suspicious name.

`hsm.py` and `algo.py` are inside the boundary: `algo.py` is the crypto engine
the module calls, and a real HSM has one of those too. Everything else in the
package is outside it.
"""

from __future__ import annotations

import ast
from pathlib import Path

from conftest import TEST_KDF_N
from secboot.algo import SPECS, Algo
from secboot.hsm import Hsm, Usage

SOURCE_DIR = Path(__file__).resolve().parents[1] / "src" / "secboot"
INSIDE_THE_BOUNDARY = {"hsm.py", "algo.py"}
#: Names that touch private key material in any of the backends.
FORBIDDEN = {
    "_private_keys",
    "private_bytes",
    "private_bytes_raw",
    "load_private",
    "from_private_bytes",
}


def _referenced_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    return names


def test_no_module_outside_the_boundary_names_private_key_material() -> None:
    offenders: dict[str, set[str]] = {}
    for path in sorted(SOURCE_DIR.glob("*.py")):
        if path.name in INSIDE_THE_BOUNDARY:
            continue
        hits = _referenced_names(ast.parse(path.read_text(encoding="utf-8"))) & FORBIDDEN
        if hits:
            offenders[path.name] = hits
    assert not offenders, f"private key material referenced outside the HSM: {offenders}"


def test_the_scan_would_actually_catch_a_leak(tmp_path: Path) -> None:
    """A guard that cannot fail is not a guard. This proves the scan fires."""
    leaky = ast.parse("def steal(hsm):\n    return hsm._private_keys[0]\n")
    assert _referenced_names(leaky) & FORBIDDEN


def test_no_public_return_value_contains_the_private_key(tmp_path: Path) -> None:
    hsm = Hsm(tmp_path / "keystore.json", kdf_n=TEST_KDF_N)
    hsm.import_private(0, Algo.ED25519, b"\x07" * 32)
    secret = SPECS[Algo.ED25519].private_bytes(hsm._private_keys[0])

    exposed = [
        hsm.public_key(0),
        bytes(str(hsm.slot_info(0)), "utf-8"),
        bytes(str(hsm.slots()), "utf-8"),
        hsm.sign(0, b"message"),
    ]
    for value in exposed:
        assert secret not in value


def test_the_keystore_on_disk_is_encrypted(tmp_path: Path) -> None:
    """ "Protected by the HSM boundary" has to mean something for a process that
    survives a restart."""
    path = tmp_path / "keystore.json"
    hsm = Hsm(path, kdf_n=TEST_KDF_N)
    hsm.import_private(0, Algo.ED25519, b"\x07" * 32)
    secret = SPECS[Algo.ED25519].private_bytes(hsm._private_keys[0])
    assert secret.hex() not in path.read_text(encoding="utf-8")


def test_keys_survive_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "keystore.json"
    first = Hsm(path, kdf_n=TEST_KDF_N)
    first.generate(0, Algo.ED25519)
    public = first.public_key(0)

    second = Hsm(path, kdf_n=TEST_KDF_N)
    assert second.public_key(0) == public
    assert second.slot_info(0).exportable is False


def test_a_wrong_passphrase_does_not_open_the_keystore(tmp_path: Path) -> None:
    path = tmp_path / "keystore.json"
    Hsm(path, passphrase="right", kdf_n=TEST_KDF_N).generate(0, Algo.ED25519)
    try:
        Hsm(path, passphrase="wrong", kdf_n=TEST_KDF_N)
    except Exception as error:  # noqa: BLE001 - the library's own exception type
        assert "decrypt" in type(error).__name__.lower() or "Invalid" in type(error).__name__
    else:  # pragma: no cover
        raise AssertionError("the keystore opened under the wrong passphrase")


def test_an_attestation_key_cannot_sign_firmware(tmp_path: Path) -> None:
    """Usage flags, not convention: a key that can do both lets whoever can ask
    for a quote also ask for a firmware signature."""
    hsm = Hsm(tmp_path / "keystore.json", kdf_n=TEST_KDF_N)
    hsm.generate(3, Algo.ED25519, Usage.ATTEST)
    try:
        hsm.sign(3, b"firmware")
    except Exception as error:  # noqa: BLE001
        assert "signing key" in str(error)
    else:  # pragma: no cover
        raise AssertionError("an ATTEST-only slot signed")


def test_latency_is_charged_per_operation(tmp_path: Path) -> None:
    hsm = Hsm(tmp_path / "keystore.json", kdf_n=TEST_KDF_N)
    hsm.generate(0, Algo.ED25519)
    before = hsm.operations
    hsm.simulate_operation()
    hsm.sign(0, b"x")
    assert hsm.operations == before + 2
