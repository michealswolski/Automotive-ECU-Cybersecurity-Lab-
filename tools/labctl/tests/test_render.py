"""Generated-block rendering, and the --check path CI relies on."""

from __future__ import annotations

from pathlib import Path

import pytest

from labctl import inspect, manifest, render


def test_apply_block_replaces_only_the_marked_span() -> None:
    text = (
        "before\n"
        "<!-- labctl:begin readme-status -->\n"
        "old content\n"
        "<!-- labctl:end readme-status -->\n"
        "after\n"
    )
    out = render.apply_block(text, "readme-status", "\nnew content\n")
    assert "before\n" in out
    assert "after\n" in out
    assert "old content" not in out
    assert "new content" in out
    assert out.count("<!-- labctl:begin readme-status -->") == 1


def test_apply_block_is_idempotent() -> None:
    text = "<!-- labctl:begin totals -->\nx\n<!-- labctl:end totals -->\n"
    once = render.apply_block(text, "totals", "\nbody\n")
    assert render.apply_block(once, "totals", "\nbody\n") == once


def test_apply_block_rejects_an_unknown_block() -> None:
    with pytest.raises(render.RenderError, match="nope"):
        render.apply_block("nothing here", "nope", "body")


def test_generators_produce_content_for_every_block(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    states = inspect.inspect_all(lab_root, lab.projects)
    for name, generator in render.GENERATORS.items():
        body = generator(lab, states)
        assert body.strip(), f"{name} rendered empty"


def test_project_cards_are_laid_out_two_per_row(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    states = inspect.inspect_all(lab_root, lab.projects)
    body = render.readme_projects(lab, states)
    assert body.count("<tr>") == 1
    assert body.count("<td") == 2
    assert "Alpha" in body and "Beta" in body


def test_odd_project_count_gets_a_filler_cell(lab_root: Path) -> None:
    """A three-project lab must not render a ragged table."""
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "[[skill]]",
            '[[project]]\nid = "gamma"\nnumber = 3\norder = 3\ntitle = "Gamma"\n'
            'status = "specified"\nlanguage = "Python"\neffort = "S"\n'
            'summary = "S."\ncenterpiece = "C."\ncovers = ["thing"]\n\n[[skill]]',
            1,
        ),
        encoding="utf-8",
    )
    lab = manifest.load(lab_root)
    states = inspect.inspect_all(lab_root, lab.projects)
    body = render.readme_projects(lab, states)
    assert body.count("<tr>") == 2
    assert body.count("<td") == 4


def test_coverage_matrix_marks_only_claimed_skills(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    states = inspect.inspect_all(lab_root, lab.projects)
    body = render.coverage_matrix(lab, states)
    assert "| Thing | ● | · |" in body
    assert "| Other | · | ● |" in body
    # Bench-only skills never appear in the coverage matrix.
    assert "Bench Thing" not in body


def test_bench_gaps_lists_every_bench_skill(lab_root: Path) -> None:
    lab = manifest.load(lab_root)
    states = inspect.inspect_all(lab_root, lab.projects)
    assert "Bench Thing" in render.bench_gaps(lab, states)


def test_render_writes_then_reports_clean(lab_root: Path) -> None:
    (lab_root / "README.md").write_text(
        "# Lab\n\n<!-- labctl:begin readme-status -->\nstale\n<!-- labctl:end readme-status -->\n",
        encoding="utf-8",
    )
    lab = manifest.load(lab_root)

    changed = render.render(lab, check=False)
    assert [r.path.name for r in changed] == ["README.md"]
    assert "Alpha" in (lab_root / "README.md").read_text(encoding="utf-8")

    assert render.render(lab, check=False) == []
    assert render.render(lab, check=True) == []


def test_render_check_does_not_write(lab_root: Path) -> None:
    readme = lab_root / "README.md"
    readme.write_text(
        "<!-- labctl:begin totals -->\nstale\n<!-- labctl:end totals -->\n", encoding="utf-8"
    )
    before = readme.read_text(encoding="utf-8")
    stale = render.render(manifest.load(lab_root), check=True)
    assert stale
    assert readme.read_text(encoding="utf-8") == before


def test_files_without_blocks_are_left_alone(lab_root: Path) -> None:
    readme = lab_root / "README.md"
    readme.write_text("# Just prose\n", encoding="utf-8")
    assert render.render(manifest.load(lab_root)) == []
    assert readme.read_text(encoding="utf-8") == "# Just prose\n"


def test_link_prefix_reaches_the_root_from_any_depth(lab_root: Path) -> None:
    assert render.link_prefix(lab_root / "README.md", lab_root) == "./"
    assert render.link_prefix(lab_root / "docs" / "status.md", lab_root) == "../"
    assert render.link_prefix(lab_root / "a" / "b" / "c.md", lab_root) == "../../"


def test_docs_blocks_link_back_out_of_the_docs_directory(lab_root: Path) -> None:
    """A project link rendered into docs/ must not resolve to docs/projects/."""
    docs = lab_root / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "status.md").write_text(
        "<!-- labctl:begin readme-status -->\nstale\n<!-- labctl:end readme-status -->\n",
        encoding="utf-8",
    )
    render.render(manifest.load(lab_root))
    body = (docs / "status.md").read_text(encoding="utf-8")
    assert "(../projects/alpha)" in body
    assert "(./projects/alpha)" not in body


def test_a_built_project_advertises_its_run_command(lab_root: Path) -> None:
    """A finished project's card leads with how to run it, and links its own
    README rather than the build plan — which is history by then."""
    path = lab_root / "lab.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            'status = "specified"',
            'status = "building"\nrun = "make demo"',
            1,
        ),
        encoding="utf-8",
    )
    lab = manifest.load(lab_root)
    states = inspect.inspect_all(lab_root, lab.projects)

    building = render.readme_projects(lab, states)
    assert "**Run it.**" not in building, "a command is only advertised once it works"
    assert "build plan" in building

    path.write_text(
        path.read_text(encoding="utf-8").replace('status = "building"', 'status = "built"', 1),
        encoding="utf-8",
    )
    lab = manifest.load(lab_root)
    built = render.readme_projects(lab, inspect.inspect_all(lab_root, lab.projects))
    assert "**Run it.** `make demo`" in built
    assert "readme</a>" in built
