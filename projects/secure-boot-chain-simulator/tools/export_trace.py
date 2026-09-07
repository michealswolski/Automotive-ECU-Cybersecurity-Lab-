#!/usr/bin/env python3
"""Generate the trace data behind `site/visualizer.html`.

This does not reimplement the boot chain. It runs the real `secboot` library —
the same `demo.provision()` / `Scenario.run()` every scenario in `make demo`
uses — and captures what actually came out of it: the hash-chained audit log,
the final PCR bank, and whether the outcome matched what the scenario expects.
That JSON is embedded into `site/visualizer.html` between two markers, the
same way `labctl` regenerates the blocks in the root README from `lab.toml`.

    PYTHONPATH=src python3 tools/export_trace.py            # regenerate
    PYTHONPATH=src python3 tools/export_trace.py --check     # verify, no write

`make visualize` / `make visualize-check` run these from the project root.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console  # noqa: E402

from secboot import demo, measure  # noqa: E402
from secboot.image import STAGE_NAMES  # noqa: E402
from secboot.reasons import EXPLANATION, ReasonCode  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VISUALIZER_HTML = PROJECT_ROOT / "site" / "visualizer.html"
BEGIN_MARKER = "<!-- secboot:trace:begin -->"
END_MARKER = "<!-- secboot:trace:end -->"


def _quiet_console() -> Console:
    """A Console the scenarios can narrate into without touching stdout."""
    return Console(file=io.StringIO(), no_color=True, width=100)


def _scenario_trace(scenario: demo.Scenario, seed: int, root: Path) -> dict[str, Any]:
    bench = demo.provision(root, seed, label=scenario.key)
    outcome = scenario.run(_quiet_console(), bench)
    chain = bench.machine.audit.verify()
    return {
        "key": scenario.key,
        "title": scenario.title,
        "attack": scenario.attack,
        "expected": str(scenario.expected),
        "outcome": str(outcome),
        "matched": outcome is scenario.expected,
        "final_pcrs": bench.machine.pcr.as_dict(),
        "chain": {
            "ok": chain.ok,
            "records": chain.records,
            "broken_seq": chain.broken_seq,
            "reason": str(chain.reason),
            "detail": chain.detail,
        },
        "audit": list(bench.machine.audit.records()),
    }


def build_trace() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="secboot-trace-") as tmp:
        root = Path(tmp)
        scenarios = [
            _scenario_trace(scenario, demo.DEFAULT_SEED, root) for scenario in demo.SCENARIOS
        ]
    return {
        "seed": demo.DEFAULT_SEED,
        "stage_names": {str(k): v for k, v in STAGE_NAMES.items()},
        "pcr_purpose": {str(k): v for k, v in measure.PCR_PURPOSE.items()},
        "reason_explanations": {str(code): EXPLANATION[code] for code in ReasonCode},
        "scenarios": scenarios,
    }


def render_block(trace: dict[str, Any]) -> str:
    payload = json.dumps(trace, indent=2, sort_keys=True, default=str)
    return (
        f"{BEGIN_MARKER}\n"
        f'<script id="trace-data" type="application/json">\n{payload}\n</script>\n'
        f"{END_MARKER}"
    )


def inject(html: str, block: str) -> str:
    start = html.index(BEGIN_MARKER)
    end = html.index(END_MARKER) + len(END_MARKER)
    return html[:start] + block + html[end:]


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    if not VISUALIZER_HTML.exists():
        print(f"missing {VISUALIZER_HTML} — nothing to inject into", file=sys.stderr)
        return 1

    html = VISUALIZER_HTML.read_text(encoding="utf-8")
    if BEGIN_MARKER not in html or END_MARKER not in html:
        print(f"{VISUALIZER_HTML} has no {BEGIN_MARKER} / {END_MARKER} markers", file=sys.stderr)
        return 1

    trace = build_trace()
    block = render_block(trace)
    updated = inject(html, block)

    if check_only:
        if updated != html:
            print("visualizer.html is stale — run `make visualize` to regenerate", file=sys.stderr)
            return 1
        print("visualizer.html trace data is current")
        return 0

    VISUALIZER_HTML.write_text(updated, encoding="utf-8")
    matched = sum(1 for s in trace["scenarios"] if s["matched"])
    print(f"wrote {VISUALIZER_HTML} — {matched}/{len(trace['scenarios'])} scenarios matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
