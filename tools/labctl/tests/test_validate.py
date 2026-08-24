"""Each rule, exercised by breaking exactly the thing it guards."""

from __future__ import annotations

from pathlib import Path

from conftest import write_project

from labctl import manifest, validate


def rules(findings) -> set[str]:
    return {finding.rule for finding in findings}


def test_a_well_formed_repository_has_no_findings(lab_root: Path) -> None:
    assert validate.run_all(manifest.load(lab_root)) == []


def test_missing_project_directory_is_reported(lab_root: Path) -> None:
    import shutil

    shutil.rmtree(lab_root / "projects" / "beta")
    findings = validate.run_all(manifest.load(lab_root))
    assert "project-dir" in rules(findings)


def test_missing_kit_file_is_reported(lab_root: Path) -> None:
    (lab_root / "projects" / "alpha" / "prompts" / "kickoff.md").unlink()
    findings = validate.run_all(manifest.load(lab_root))
    assert "project-files" in rules(findings)
    assert any("kickoff.md" in str(f) for f in findings)


def test_undeclared_project_directory_is_reported(lab_root: Path) -> None:
    write_project(lab_root, "gamma")
    findings = validate.run_all(manifest.load(lab_root))
    assert "orphan-project" in rules(findings)


def test_built_status_requires_a_finished_checklist(lab_root: Path) -> None:
    """The rule that stops the README claiming a project is done early."""
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('status = "specified"', 'status = "built"', 1),
        encoding="utf-8",
    )
    findings = validate.run_all(manifest.load(lab_root))
    assert "status" in rules(findings)
    assert any("still unchecked" in str(f) for f in findings)


def test_specified_status_goes_stale_once_work_starts(lab_root: Path) -> None:
    """Checking a box while the manifest still says 'specified' means the
    README would understate progress. Catch it rather than let it drift."""
    assert [f for f in validate.run_all(manifest.load(lab_root)) if f.rule == "status"] == []

    (lab_root / "projects" / "beta" / "ACCEPTANCE.md").write_text(
        "- [x] done\n- [ ] not yet\n", encoding="utf-8"
    )
    findings = validate.run_all(manifest.load(lab_root))
    assert any("bump it to 'building'" in str(f) for f in findings)


def test_unknown_skill_reference_is_reported(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('covers = ["thing"]', 'covers = ["nope"]'),
        encoding="utf-8",
    )
    findings = validate.run_all(manifest.load(lab_root))
    assert "skill-ref" in rules(findings)


def test_claiming_a_bench_skill_is_reported(lab_root: Path) -> None:
    """A simulation may not claim a capability that needs hardware. This is the
    rule that encodes the repo's whole claim-discipline policy in code."""
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            'covers = ["thing"]', 'covers = ["thing", "bench-thing"]'
        ),
        encoding="utf-8",
    )
    findings = validate.run_all(manifest.load(lab_root))
    assert "bench-claim" in rules(findings)
    assert any("bench-path" in str(f) for f in findings)


def test_uncovered_skill_is_reported(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8")
        + '\n[[skill]]\nid = "dangling"\nlabel = "Dangling"\ngroup = "Group A"\n',
        encoding="utf-8",
    )
    findings = validate.run_all(manifest.load(lab_root))
    assert "uncovered-skill" in rules(findings)


def test_unsatisfied_bridge_is_reported(lab_root: Path) -> None:
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('provides = ["alpha:widget"]', ""),
        encoding="utf-8",
    )
    findings = validate.run_all(manifest.load(lab_root))
    assert "bridge" in rules(findings)


def test_dead_relative_link_is_reported(lab_root: Path) -> None:
    (lab_root / "README.md").write_text("See [the spec](./docs/nope.md).\n", encoding="utf-8")
    findings = validate.run_all(manifest.load(lab_root))
    assert "dead-link" in rules(findings)


def test_live_relative_link_is_accepted(lab_root: Path) -> None:
    (lab_root / "README.md").write_text(
        "See [alpha](./projects/alpha/SPEC.md) and [anchors](./projects/alpha/SPEC.md#top).\n",
        encoding="utf-8",
    )
    assert "dead-link" not in rules(validate.run_all(manifest.load(lab_root)))


def test_external_links_and_images_are_not_followed(lab_root: Path) -> None:
    (lab_root / "README.md").write_text(
        "[web](https://example.invalid/x) ![img](./assets/missing.svg) [anchor](#section)\n",
        encoding="utf-8",
    )
    assert "dead-link" not in rules(validate.run_all(manifest.load(lab_root)))


def test_build_plan_without_phases_is_reported(lab_root: Path) -> None:
    (lab_root / "projects" / "alpha" / "BUILD_PLAN.md").write_text("# Plan\n", encoding="utf-8")
    findings = validate.run_all(manifest.load(lab_root))
    assert "build-plan" in rules(findings)


def test_empty_acceptance_is_reported(lab_root: Path) -> None:
    (lab_root / "projects" / "alpha" / "ACCEPTANCE.md").write_text("# Done\n", encoding="utf-8")
    findings = validate.run_all(manifest.load(lab_root))
    assert "acceptance" in rules(findings)
