"""The standards register: parsing, the rules that enforce it, and rendering.

These exist because the register's whole value is that it cannot quietly go
stale. A rule nobody tests is a rule that stops working the first time someone
refactors around it.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from labctl import cli, manifest, render, validate


def rules(findings) -> set[str]:
    return {finding.rule for finding in findings}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_standards_load_with_their_provenance(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    one = lab.standard("spec-one")
    assert one.name == "SPEC ONE"
    assert one.edition == "2024"
    assert one.source == "web"
    assert one.citable is True
    assert one.moving is False


def test_imminent_and_draft_count_as_moving(lab_root: Path) -> None:
    """Anything under active revision has to be re-checked before it is quoted."""
    lab = manifest.load(lab_root)
    assert lab.standard("spec-two").moving is True


def test_superseded_is_not_citable(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('status = "imminent"', 'status = "superseded"'),
        encoding="utf-8",
    )
    assert manifest.load(lab_root).standard("spec-two").citable is False


def test_unknown_standard_status_is_rejected(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('status = "imminent"', 'status = "probably fine"'),
        encoding="utf-8",
    )
    with pytest.raises(manifest.ManifestError, match="probably fine"):
        manifest.load(lab_root)


def test_unknown_standard_source_is_rejected(lab_root: Path) -> None:
    """A register that cannot say how it knows is decoration."""
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('source = "web"', 'source = "vibes"'),
        encoding="utf-8",
    )
    with pytest.raises(manifest.ManifestError, match="vibes"):
        manifest.load(lab_root)


def test_duplicate_standard_id_is_rejected(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('id = "spec-two"', 'id = "spec-one"'),
        encoding="utf-8",
    )
    with pytest.raises(manifest.ManifestError, match="duplicate standard id"):
        manifest.load(lab_root)


def test_citing_lists_projects_in_display_order(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    assert [p.id for p in lab.citing("spec-one")] == ["alpha", "beta"]
    assert [p.id for p in lab.citing("spec-two")] == ["beta"]


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def test_unknown_standard_reference_is_reported(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('standards = ["spec-one"]', 'standards = ["nope"]'),
        encoding="utf-8",
    )
    assert "standard-ref" in rules(validate.run_all(manifest.load(lab_root)))


def test_citing_a_superseded_standard_fails_the_build(lab_root: Path) -> None:
    """The rule that turns 'cite the current edition' into a build property."""
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('status = "imminent"', 'status = "superseded"'),
        encoding="utf-8",
    )
    findings = validate.run_all(manifest.load(lab_root))
    assert "superseded-standard" in rules(findings)
    assert any("SPEC TWO" in str(f) for f in findings)


def test_orphan_standard_is_reported(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8")
        + '\n[[standard]]\nid = "dangling"\nname = "D"\ntitle = "T"\nedition = "1"\n'
        'status = "current"\ngroup = "Group S"\nverified = "2026-08-24"\nsource = "web"\n',
        encoding="utf-8",
    )
    assert "orphan-standard" in rules(validate.run_all(manifest.load(lab_root)))


def test_a_project_citing_nothing_is_reported(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('standards = ["spec-one"]\n', "", 1),
        encoding="utf-8",
    )
    findings = validate.run_all(manifest.load(lab_root))
    assert "no-standard" in rules(findings)


def test_non_iso_verified_date_is_reported(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('verified = "2026-08-24"', 'verified = "recently"'),
        encoding="utf-8",
    )
    assert "standard-verified" in rules(validate.run_all(manifest.load(lab_root)))


# ---------------------------------------------------------------------------
# The re-check list
# ---------------------------------------------------------------------------


def test_moving_standards_are_always_on_the_recheck_list(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    stale = validate.stale_standards(lab, today=date(2026, 8, 24))
    assert [s.id for s in stale] == ["spec-two"]


def test_a_row_unchecked_for_over_a_year_joins_the_recheck_list(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    stale = validate.stale_standards(lab, today=date(2028, 1, 1))
    assert {s.id for s in stale} == {"spec-one", "spec-two"}


def test_staleness_is_a_prompt_not_a_build_failure(lab_root: Path) -> None:
    """Failing the build on the passage of time would train people to ignore
    the build. The re-check list is advisory on purpose."""
    lab = manifest.load(lab_root)
    assert validate.stale_standards(lab, today=date(2030, 1, 1))
    assert validate.run_all(lab) == []


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_register_groups_rows_and_shows_who_cites_them(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    body = render.standards_register(lab, {})
    assert "### Group S" in body
    assert "**SPEC ONE**" in body
    assert "`01` `02`" in body
    assert "2026-08-24 · web" in body


def test_watchlist_holds_only_moving_rows(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    body = render.standards_watchlist(lab, {})
    assert "SPEC TWO" in body
    assert "SPEC ONE" not in body


def test_project_standards_names_the_documents(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    body = render.project_standards(lab, {}, prefix="../")
    assert "SPEC ONE, SPEC TWO" in body
    assert "(../projects/beta)" in body


def test_notes_render_only_where_a_note_exists(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    body = render.standards_notes(lab, {})
    assert "A note about spec one." in body
    assert "**SPEC TWO" not in body


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_standards_command_prints_the_register(capsys, lab_root: Path) -> None:
    assert cli.main(["-C", str(lab_root), "standards"]) == 0
    out = capsys.readouterr().out
    assert "SPEC ONE" in out
    assert "GROUP S" in out
    assert "Re-check before quoting" in out


def test_show_lists_the_documents_a_project_implements(capsys, lab_root: Path) -> None:
    assert cli.main(["-C", str(lab_root), "show", "beta"]) == 0
    out = capsys.readouterr().out
    assert "Implements" in out
    assert "SPEC TWO — draft" in out


def test_real_repository_cites_a_current_edition_everywhere(repo_root: Path) -> None:
    """If this fails, the repository is naming an edition it has retired."""
    lab = manifest.load(repo_root)
    for project in lab.projects:
        assert project.standards, project.id
        for standard_id in project.standards:
            assert lab.standard(standard_id).citable
