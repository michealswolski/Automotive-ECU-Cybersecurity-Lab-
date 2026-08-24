"""Manifest parsing: the structural guarantees everything else assumes."""

from __future__ import annotations

from pathlib import Path

import pytest

from labctl import manifest


def test_loads_projects_and_skills(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    assert lab.name == "Test Lab"
    assert [p.id for p in lab.by_number()] == ["alpha", "beta"]
    assert lab.skill("thing").label == "Thing"
    assert lab.skill("bench-thing").bench_only is True


def test_multiline_summary_is_collapsed(lab_root: Path) -> None:
    """Manifest prose is line-wrapped for editing; readers want one paragraph."""
    (lab_root / "lab.toml").write_text(
        (lab_root / "lab.toml")
        .read_text(encoding="utf-8")
        .replace('summary = "Alpha summary."', 'summary = """\nAlpha \\\n  wrapped   summary."""'),
        encoding="utf-8",
    )
    lab = manifest.load(lab_root)
    assert lab.project("alpha").summary == "Alpha wrapped summary."


def test_missing_manifest_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(manifest.ManifestError, match="no lab.toml"):
        manifest.load(tmp_path)


def test_unknown_status_is_rejected(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('status = "specified"', 'status = "shipped"', 1),
        encoding="utf-8",
    )
    with pytest.raises(manifest.ManifestError, match="shipped"):
        manifest.load(lab_root)


def test_missing_required_key_names_the_entry(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('effort = "M"\n', "", 1), encoding="utf-8"
    )
    with pytest.raises(manifest.ManifestError, match=r"\[\[project\]\] #1: missing required key"):
        manifest.load(lab_root)


def test_duplicate_project_number_is_rejected(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("number = 2", "number = 1", 1), encoding="utf-8"
    )
    with pytest.raises(manifest.ManifestError, match="duplicate project number"):
        manifest.load(lab_root)


def test_project_label_and_paths(lab_root: Path) -> None:
    project = manifest.load(lab_root).project("alpha")
    assert project.label == "01 · Alpha"
    assert project.path == "projects/alpha"


def test_skill_groups_preserve_manifest_order(lab_root: Path) -> None:
    groups = manifest.load(lab_root).skill_groups()
    assert list(groups) == ["Group A", "Bench"]
    assert [s.id for s in groups["Group A"]] == ["thing", "other"]
