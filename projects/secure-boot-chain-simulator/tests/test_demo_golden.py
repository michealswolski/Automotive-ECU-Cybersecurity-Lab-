"""The demo is a deliverable, so its output is pinned.

A golden file turns "the demo still runs" into "the demo still says the same
thing". Determinism comes from the seed: every key in the demo is derived from
it, so the measurements, PCRs and audit hashes are reproducible.

Regenerate deliberately, never reflexively:

    python tests/test_demo_golden.py --write
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console

from secboot import demo

GOLDEN = Path(__file__).resolve().parent / "golden" / "demo.txt"
WIDTH = 96


def capture(root: Path, *, seed: int = demo.DEFAULT_SEED, only: str = "all") -> tuple[str, bool]:
    buffer = io.StringIO()
    console = Console(file=buffer, no_color=True, width=WIDTH, highlight=False, soft_wrap=False)
    matched = demo.run(console, root, seed=seed, only=only)
    return buffer.getvalue(), matched


def test_every_scenario_reaches_its_expected_reason_code(tmp_path: Path) -> None:
    """The stronger half of this file: the demo asserts its own outcomes."""
    _, matched = capture(tmp_path)
    assert matched


def test_demo_output_matches_the_golden_file(tmp_path: Path) -> None:
    output, _ = capture(tmp_path)
    assert output == GOLDEN.read_text(encoding="utf-8"), (
        "demo output drifted. If the change is intended, regenerate with "
        "`python tests/test_demo_golden.py --write` and read the diff."
    )


def test_the_run_is_reproducible_across_processes(tmp_path: Path) -> None:
    first, _ = capture(tmp_path / "a")
    second, _ = capture(tmp_path / "b")
    assert first == second


def test_a_different_seed_produces_different_keys(tmp_path: Path) -> None:
    """Proves the seed is actually load-bearing rather than decorative."""
    first, _ = capture(tmp_path / "a", seed=1, only="happy")
    second, _ = capture(tmp_path / "b", seed=2, only="happy")
    assert first != second


@pytest.mark.parametrize("key", list(demo.BY_KEY))
def test_each_scenario_runs_on_its_own(tmp_path: Path, key: str) -> None:
    _, matched = capture(tmp_path / key, only=key)
    assert matched


if __name__ == "__main__":  # pragma: no cover - maintenance entry point
    import shutil
    import sys
    import tempfile

    if "--write" not in sys.argv:
        raise SystemExit("pass --write to regenerate the golden file")
    root = Path(tempfile.mkdtemp(prefix="secboot-golden-"))
    try:
        text, ok = capture(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(text, encoding="utf-8")
    print(f"wrote {GOLDEN} ({len(text)} bytes, all scenarios matched: {ok})")
