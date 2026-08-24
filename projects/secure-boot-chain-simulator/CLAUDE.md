# CLAUDE.md — Secure Boot Chain Simulator

> **Read [`CORRECTIONS.md`](./CORRECTIONS.md) before writing any code.** Several
> standards anchors in this file and in `SPEC.md` have moved since they were
> written — AUTOSAR release, UDS security services, the post-quantum firmware
> signing story, tool maintenance status. The corrections file is authoritative
> where it disagrees with the text below. Editions to cite are in
> [`docs/standards-register.md`](../../docs/standards-register.md).

You are building this project from scratch. This file is your standing instruction set.
Read `SPEC.md` (the source of truth) and `BUILD_PLAN.md` (phase order) before writing code.

## What this is

A simulated multi-stage automotive secure boot chain: **BootROM → SBL (bootloader) → Application**,
where each stage cryptographically verifies the next before transferring control. It models a
hardware root of trust (OTP fuses), a simulated HSM that never releases private keys, monotonic
anti-rollback counters, measured boot, and a tamper-evident audit log.

It is a **portfolio + interview artifact** for an automotive cybersecurity engineer. Two audiences:
a hiring manager who will skim the README and run one command, and an interviewer who will ask
"what happens if I flip a bit in the app image?" It must answer that in under 10 seconds of runtime.

## Non-negotiables

1. **It must run with one command on a clean machine.** `uv run secboot demo` (or
   `python -m secboot demo`) produces the full narrated demo with zero setup beyond dependency install.
2. **Every verification decision is logged** with: stage, decision (ACCEPT/REJECT/HALT), a stable
   machine-readable reason code, the SHA-256 measurement, and the counter state at decision time.
3. **Negative paths are first-class features, not tests.** Corrupted image, downgrade attempt,
   unknown key ID, revoked key ID, truncated image, and SVN-rollback each have a dedicated demo
   scenario and a dedicated test.
4. **Private keys never leave the simulated HSM object.** The rest of the codebase may only call
   `hsm.sign(key_id, data)` / `hsm.get_public_key(key_id)`. Enforce this with a test that greps for
   private-key access outside `secboot/hsm.py`.
5. **Determinism.** `--seed` makes runs byte-reproducible so demo output can be committed as a golden file.
6. **No hand-rolled cryptography.** Use `cryptography` (pyca) primitives only. Do not implement
   ECDSA, SHA-256, or CMAC yourself.

## Engineering standards

- Python 3.12+. Type-annotate everything; `mypy --strict` clean on `src/`.
- `ruff` for lint + format. `pytest` for tests, `pytest-cov` with a floor of 85% on `src/secboot`.
- Dependencies pinned in `pyproject.toml`. Use `uv` if available, fall back to `pip`.
- No global mutable state. Boot stages are pure-ish: they take a `Machine` context and return a `BootResult`.
- Errors are values, not exceptions, on the verification path. A failed verify returns a
  `VerifyResult(ok=False, reason=ReasonCode.SIGNATURE_INVALID, ...)`. Reserve exceptions for
  programmer error and I/O.
- Every public function gets a docstring naming the real-world concept it models
  (e.g. "models the OTP fuse read in an EVITA-Medium HSM").

## Verify current facts before coding

Your training data may be stale. Before writing crypto code, check the installed library:

```bash
python -c "import cryptography; print(cryptography.__version__)"
python -c "from cryptography.hazmat.primitives.asymmetric import ec, ed25519; print('ok')"
```

**Post-quantum:** ML-DSA (FIPS 204) support in `cryptography` is version-dependent. Probe for it:

```bash
python - <<'PY'
try:
    from cryptography.hazmat.primitives.asymmetric import ml_dsa
    print("ml_dsa available")
except ImportError:
    print("ml_dsa NOT available - gate the PQ backend behind a feature flag")
PY
```

If ML-DSA is unavailable, implement the PQ backend as an optional extra (`pip install .[pq]` using
a maintained PQ library) and make `--algo ml-dsa-65` fail with a clear, actionable message rather
than crashing. Never fake a PQ signature.

## What "done" looks like

`ACCEPTANCE.md` is the checklist. Do not declare a phase complete until its acceptance criteria pass
and `make check` (lint + types + tests) is green.

## Style of the output the user sees

Console output uses `rich`. The boot chain renders as a tree with per-stage status glyphs, and each
REJECT prints the reason code, the expected vs actual value, and the line of the spec it enforces.
Think "an engineer demoing to another engineer", not "a security product marketing page".
