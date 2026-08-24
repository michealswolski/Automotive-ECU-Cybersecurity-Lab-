"""End-to-end CLI behaviour, including the exit codes CI keys off."""

from __future__ import annotations

from pathlib import Path

import pytest

from labctl import cli


def run(capsys, *argv: str) -> tuple[int, str]:
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


def test_no_command_prints_help(capsys) -> None:
    code, out = run(capsys)
    assert code == 0
    assert "usage: labctl" in out


def test_status_lists_every_project(capsys, lab_root: Path) -> None:
    code, out = run(capsys, "-C", str(lab_root), "status")
    assert code == 0
    assert "Alpha" in out and "Beta" in out
    assert "2 projects" in out


def test_status_counts_bench_only_capabilities(capsys, lab_root: Path) -> None:
    _, out = run(capsys, "-C", str(lab_root), "status")
    assert "1 capabilities deliberately not claimed" in out


def test_validate_passes_on_a_clean_repository(capsys, lab_root: Path) -> None:
    code, out = run(capsys, "-C", str(lab_root), "validate")
    assert code == 0
    assert "all checks passed" in out


def test_validate_exits_non_zero_on_a_finding(capsys, lab_root: Path) -> None:
    (lab_root / "projects" / "alpha" / "SPEC.md").unlink()
    code, out = run(capsys, "-C", str(lab_root), "validate")
    assert code == 1
    assert "SPEC.md" in out
    assert "finding(s)" in out


def test_render_check_exits_non_zero_when_stale(capsys, lab_root: Path) -> None:
    (lab_root / "README.md").write_text(
        "<!-- labctl:begin totals -->\nstale\n<!-- labctl:end totals -->\n", encoding="utf-8"
    )
    code, out = run(capsys, "-C", str(lab_root), "render", "--check")
    assert code == 1
    assert "make render" in out


def test_render_writes_then_check_passes(capsys, lab_root: Path) -> None:
    (lab_root / "README.md").write_text(
        "<!-- labctl:begin totals -->\nstale\n<!-- labctl:end totals -->\n", encoding="utf-8"
    )
    assert run(capsys, "-C", str(lab_root), "render")[0] == 0
    assert run(capsys, "-C", str(lab_root), "render", "--check")[0] == 0


def test_show_prints_phases_and_bridges(capsys, lab_root: Path) -> None:
    code, out = run(capsys, "-C", str(lab_root), "show", "beta")
    assert code == 0
    assert "Beta" in out
    assert "Real work" in out
    assert "consumes  alpha:widget" in out


def test_show_rejects_an_unknown_project(capsys, lab_root: Path) -> None:
    code, out = run(capsys, "-C", str(lab_root), "show", "delta")
    assert code == 2
    assert "known: alpha, beta" in out


def test_missing_manifest_exits_two(capsys, tmp_path: Path) -> None:
    code, out = run(capsys, "-C", str(tmp_path), "status")
    assert code == 2
    assert "no lab.toml" in out


def test_root_is_discovered_from_a_subdirectory(lab_root: Path, monkeypatch) -> None:
    """The CLI should work from anywhere inside the repo, like git."""
    monkeypatch.chdir(lab_root / "projects" / "alpha" / "docs")
    assert cli.main(["validate"]) == 0


def test_colour_is_suppressed_when_not_a_tty(lab_root: Path, capsys) -> None:
    _, out = run(capsys, "-C", str(lab_root), "status")
    assert "\033[" not in out


@pytest.mark.parametrize("command", ["status", "validate"])
def test_commands_run_against_the_real_repository(capsys, repo_root: Path, command: str) -> None:
    """The repository has to satisfy its own rules. If this fails, the repo is
    describing itself inaccurately somewhere."""
    code, _ = run(capsys, "-C", str(repo_root), command)
    assert code == 0
