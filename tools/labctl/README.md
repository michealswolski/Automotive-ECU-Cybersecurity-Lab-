# labctl

The repository's own command line. Keeps the [Automotive ECU Cybersecurity Lab](../../README.md) honest about itself: one manifest describes the six projects, and every table a reader sees is rendered from it rather than typed twice.

**Zero third-party dependencies.** `tomllib` has been in the standard library since Python 3.11 and everything else this tool does is string handling, so it runs on a clean checkout with nothing but an interpreter.

```bash
# from the repository root
make status
make validate
make render
make show PROJECT=can-secoc-demo

# or directly, from anywhere inside the repository
PYTHONPATH=tools/labctl python -m labctl status
```

## Modules

| Module | Responsibility |
|---|---|
| `manifest.py` | Parse and model `lab.toml`. Structural errors raise here. |
| `inspect.py` | Read on-disk project state — phases from `BUILD_PLAN.md`, progress from `ACCEPTANCE.md`. |
| `validate.py` | The consistency rules. Each one exists because breaking it would make the repository say something untrue about itself. |
| `render.py` | Generate the documentation blocks; `--check` mode is what CI runs. |
| `cli.py` | Argument parsing, output formatting, exit codes. |

## Development

```bash
make dev      # installs pytest and ruff
make test
make lint
```

The suite runs against a synthetic repository built in a temporary directory, so it asserts on behaviour rather than on whatever the manifest happens to say today. Two tests are the exception — they run `status` and `validate` against the real repository and fail if it stops satisfying its own rules.

Full documentation, including every validation rule: [`docs/tooling.md`](../../docs/tooling.md).
