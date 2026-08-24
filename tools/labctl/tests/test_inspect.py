"""Parsing the two files that define a project's progress."""

from __future__ import annotations

from pathlib import Path

from labctl import inspect, manifest


def test_phase_parser_handles_every_heading_style_the_kits_use() -> None:
    """The six kits were written independently and punctuate differently. The
    parser has to cope with all of it, because normalising the kits would mean
    editing the specs to suit the tooling."""
    text = "\n".join(
        [
            "## Phase 0 - Scaffold",
            "## Phase 1 — Image container",
            "## Phase 2 — Scaffold (30 min)",
            "## Phase 7 - THE WORKED EXAMPLE",
            "## Phase 9 (optional) - Extras, in value order",
            "## Phase 10 (optional, high value)",
            "### Phase 11 - not a phase heading",
        ]
    )
    phases = inspect.parse_phases(text)
    assert [p.number for p in phases] == [0, 1, 2, 7, 9, 10]
    assert phases[0].title == "Scaffold"
    assert phases[1].title == "Image container"
    assert phases[2].title == "Scaffold (30 min)"
    assert phases[3].title == "THE WORKED EXAMPLE"
    assert phases[4].title == "Extras, in value order"
    assert [p.optional for p in phases] == [False, False, False, False, True, True]


def test_optional_only_phase_keeps_a_usable_title() -> None:
    (phase,) = inspect.parse_phases("## Phase 10 (optional, high value)")
    assert phase.optional is True
    assert phase.title == "Phase 10"


def test_checklist_counts_checked_and_unchecked() -> None:
    total, done = inspect.parse_checklist(
        "- [ ] one\n- [x] two\n- [X] three\n* [ ] four\nnot a box\n"
    )
    assert (total, done) == (4, 2)


def test_checklist_of_a_file_with_no_boxes() -> None:
    assert inspect.parse_checklist("# Nothing here\n") == (0, 0)


def test_inspect_reports_phase_and_acceptance_counts(lab_root: Path) -> None:
    (lab_root / "projects" / "alpha" / "ACCEPTANCE.md").write_text(
        "- [ ] one\n- [ ] two\n- [x] three\n", encoding="utf-8"
    )
    lab = manifest.load(lab_root)
    state = inspect.inspect_project(lab_root, lab.project("alpha"))
    assert state.exists is True
    assert state.missing_files == ()
    assert state.core_phases == 2
    assert state.optional_phases == 1
    assert (state.acceptance_total, state.acceptance_done) == (3, 1)
    assert state.acceptance_pct == 33
    assert state.complete is False


def test_inspect_flags_a_missing_kit_file(lab_root: Path) -> None:
    (lab_root / "projects" / "alpha" / "SPEC.md").unlink()
    lab = manifest.load(lab_root)
    state = inspect.inspect_project(lab_root, lab.project("alpha"))
    assert "SPEC.md" in state.missing_files


def test_inspect_handles_a_missing_directory(lab_root: Path, tmp_path: Path) -> None:
    lab = manifest.load(lab_root)
    state = inspect.inspect_project(tmp_path / "nowhere", lab.project("alpha"))
    assert state.exists is False
    assert state.core_phases == 0


def test_complete_requires_a_non_empty_checklist(lab_root: Path) -> None:
    """An empty ACCEPTANCE.md must never read as finished."""
    (lab_root / "projects" / "alpha" / "ACCEPTANCE.md").write_text("# Acceptance\n", "utf-8")
    lab = manifest.load(lab_root)
    assert inspect.inspect_project(lab_root, lab.project("alpha")).complete is False


def test_all_boxes_checked_is_complete(lab_root: Path) -> None:
    (lab_root / "projects" / "alpha" / "ACCEPTANCE.md").write_text(
        "- [x] one\n- [x] two\n", "utf-8"
    )
    lab = manifest.load(lab_root)
    state = inspect.inspect_project(lab_root, lab.project("alpha"))
    assert state.complete is True
    assert state.acceptance_pct == 100
