"""labctl — the Automotive ECU Cybersecurity Lab's own command line.

Keeps the repository honest about itself: one manifest describes the six
projects, and every table a reader sees is rendered from it rather than typed
twice.
"""

from __future__ import annotations

__all__ = ["__version__", "main"]

__version__ = "1.0.0"


def main(argv: list[str] | None = None) -> int:
    """Entry point indirection so ``import labctl`` stays cheap."""
    from .cli import main as _main

    return _main(argv)
