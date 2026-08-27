"""secboot — a simulated automotive secure boot chain.

This package models, in software, the chain of trust an ECU establishes at
power-on: an immutable BootROM verifies a secondary bootloader, which verifies
the application, with a hardware root of trust in OTP fuses and a simulated HSM
that never releases a private key.

It is a simulation for education and demonstration. It must not be used to
protect a real device.
"""

from __future__ import annotations

__version__ = "1.0.0"

__all__ = ["__version__"]
