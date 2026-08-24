# CLAUDE.md - ECU Key Lifecycle Manager

> **Read [`CORRECTIONS.md`](./CORRECTIONS.md) before writing any code.** Several
> standards anchors in this file and in `SPEC.md` have moved since they were
> written — AUTOSAR release, UDS security services, the post-quantum firmware
> signing story, tool maintenance status. The corrections file is authoritative
> where it disagrees with the text below. Editions to cite are in
> [`docs/standards-register.md`](../../docs/standards-register.md).

You are building this project from scratch. Read `SPEC.md` (source of truth) and `BUILD_PLAN.md`
(phase order) before writing code.

## What this is

A CLI plus optional local service that models the **full cryptographic key lifecycle** for a fleet
of simulated ECUs: generation, provisioning, protected storage, use, rotation with an overlap
window, revocation, and destruction -- with a hash-chained, tamper-evident audit log over every
transition.

The thesis of this project, and the line to put in the README: *most engineers can name the
algorithms; far fewer can describe what happens to a key between the day it is generated and the day
the vehicle is scrapped.* This project is about the second thing.

## Non-negotiables

1. **The lifecycle is a real state machine**, not a status string. Illegal transitions are rejected
   by the model with a named error, and there is a test for every illegal edge.
2. **Keys are never printed, logged, or returned in plaintext.** The audit log records key *IDs* and
   *digests*, never key material. Enforce with a test that scans all log output for key bytes.
3. **The audit log is hash-chained and verifiable.** `ekl audit verify` finds tampering and names
   the exact record. `ekl audit tamper` exists so you can demonstrate the detection live.
4. **Provisioning is a challenge-response ceremony**, not a copy. The ECU proves possession of its
   device identity key before it receives anything, and returns a signed receipt afterward.
5. **Rotation has an overlap window.** A design where the new key becomes valid at the instant the
   old one dies cannot survive a fleet where some ECUs are asleep. Model the overlap explicitly.
6. **No hand-rolled cryptography.** `cryptography` (pyca) only.

## Verify current facts before coding

```bash
python -c "import cryptography; print(cryptography.__version__)"
python -c "from cryptography.hazmat.primitives.asymmetric import ed25519, ec; print('ok')"
python -c "from cryptography.hazmat.primitives.kdf.hkdf import HKDF; print('ok')"
```

Web-search rather than recall for: current NIST SP 800-57 Part 1 revision and its cryptoperiod
guidance, current SP 800-130 title/scope, whether `cryptography` exposes ML-DSA in the installed
version, and any ISO/SAE 21434 or UN R156 clause number you intend to cite. **Do not assert a clause
number you have not verified.** Cite by document name if you cannot confirm the clause.

## Engineering standards

- Python 3.12+, `mypy --strict` clean, `ruff`, `pytest` ≥85% coverage on `src/ekl`.
- SQLite via SQLAlchemy 2.x typed ORM. Migrations with Alembic (a key management system that cannot
  evolve its schema is a toy -- and the migration story is a good interview answer).
- Domain layer (`lifecycle.py`, `policy.py`) has no database imports. Persistence is a repository
  interface. This separation is the thing that makes the project read as systems engineering rather
  than as a CRUD app.
- Time is injected, never `datetime.now()` inline -- cryptoperiod and rotation logic must be testable
  by advancing a fake clock.
- Every state transition is a single function that takes the current state and an event and returns
  the new state or an error. No transition logic scattered across the CLI.

## Style of the output the user sees

`rich` tables for key inventory, a lifecycle timeline view per key, and a fleet dashboard showing
which ECUs hold which key generation. `ekl demo` narrates the full story end to end.
