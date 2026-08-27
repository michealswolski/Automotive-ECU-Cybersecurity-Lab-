# Decisions

ADR-style, one entry per choice that was not obvious. Each records what was
decided, what it costs, and what the alternative would have bought — because the
useful part of a decision record is the argument, not the outcome.

---

## ADR-0001 — Python 3.11, not 3.12

`SPEC.md` says 3.12. Nothing in this project uses a 3.12 feature, and the
surrounding repository's tooling and CI floor is 3.11 (`tomllib` landed there,
which is what `labctl` needs). Lowering the floor costs nothing and means one
interpreter version runs the whole repository.

`StrEnum` is the only 3.11-specific dependency, and it is 3.11, not 3.12.

---

## ADR-0002 — An SVN advance is staged, and needs a confirmation

This is the decision `SPEC.md` calls out as the one an interviewer will probe,
and it has no free answer.

**Advance the counter at verification time.** Simple, and the window in which an
old image is acceptable is zero. But if the new image is *signed and broken* —
it verifies, it boots, it panics — the counter has already moved past the
known-good older image, and there is no path back. The part is bricked and the
only recovery is physical.

**Advance after the application reports a healthy start.** Keeps the recovery
path open, at the cost of a confirmation mechanism and a window during which the
older image still boots. An attacker who can prevent the confirmation from
happening can hold a device in that window indefinitely.

Implemented: the second. `Fuses.stage_advance` records `pending`, and
`secboot confirm-boot` — modelling a watchdog or health check reporting a
successful application start — commits it. `tests/test_rollback.py` proves the
older image still boots before confirmation and stops booting after.

The window is the price. A production design would bound it: a boot counter that
forces the confirmation after N unconfirmed starts, or a hardware watchdog that
performs the confirmation itself.

---

## ADR-0003 — Measurements cover the authenticated bytes, not the whole file

`ParsedImage.measurement()` is `SHA-256(signed_header || payload)`, not
`SHA-256(file)`.

Measuring the whole container would make the measurement change whenever the
same content is re-signed — different ECDSA nonce, same bytes — which breaks
golden attestation for no security gain. The signer's key ID and the SHA-256 of
their public key are both *inside* the signed header, so a different signer still
moves the PCR. Nothing an attacker controls falls outside the measured region
except the signature itself, which cannot be forged without one of those keys.

Side benefit: the demo is byte-reproducible, which is what makes a golden file
possible at all.

---

## ADR-0004 — Public key length is derived from the algorithm

The 128-byte header has no `pubkey_len` field and no spare bytes for one — the
28 reserved bytes are a forward-compatibility trap, not a scratchpad. So
`image.parse` looks the length up in the algorithm table.

This is how a ROM would do it anyway: code that knows how to verify ECDSA P-256
necessarily knows that its public key is 65 bytes. The cost is one ordering
wrinkle — the length check at step 7 runs before the unknown-algorithm check at
step 9, so for an unknown `algo_id` it can only bound-check what it knows, and
`UNKNOWN_ALGO` fires at its own step. That is documented in `image.parse` and
tested in `tests/test_verify_order.py::test_unknown_algo`.

ECDSA P-384 (`algo_id = 4`) was added beyond the three the spec fixes. Two
classical algorithms is what makes the policy allowlist demonstrable rather than
theoretical, and P-384 with SHA-384 is the CNSA 2.0 classical floor.

---

## ADR-0005 — SHA-256 in the container, SHA-384 available for signatures

`CORRECTIONS.md` suggests SHA-384 as the default hash, to match CNSA 2.0 posture.
Half of that is taken and half is not, and the split is deliberate:

* **The container's `payload_sha256` field stays SHA-256.** It is a fixed
  32-byte field at a fixed offset in a fixed-size header. Widening it changes the
  container format, and the field is a corruption detector ahead of the
  signature, not the security boundary.
* **The signature hash follows `algo_id`.** `ecdsa-p384` signs under SHA-384, and
  a machine whose policy allows only that algorithm has a SHA-384 signing
  posture end to end.

So a CNSA-2.0-aligned configuration is expressible today, and the honest
statement is that the *container digest* is SHA-256 while the *signature* is
whatever the algorithm says. A container revision would move the digest to
SHA-384 and widen the field; that is a format change, not a policy change.

---

## ADR-0006 — Post-quantum support is probed, never assumed

`cryptography` exposes ML-DSA (FIPS 204) from 47.0.0 at
`hazmat.primitives.asymmetric.mldsa`. But the module imports cleanly over an
OpenSSL backend and only fails when a key is generated — PQ support needs AWS-LC
or BoringSSL, and most wheels ship OpenSSL.

So `algo.available()` proves the backend by generating a key rather than reading
a version number, `secboot algos` reports what the installed build can actually
do, and `keygen --algo ml-dsa-65` fails with a message that names the cause. A
faked post-quantum signature would be worse than no support at all.

See `post-quantum.md` for why ML-DSA is framed as a FIPS 204 demonstration and
*not* as CNSA 2.0 firmware signing.

---

## ADR-0007 — Two counter substrates, because they fail differently

`svn_sbl` is modelled as an OTP eFuse counter and `svn_app` as a replay-protected
flash counter. Not decoration:

* An eFuse counter is thermometer-coded across a fixed number of fuse bits. It is
  monotonic by physics, and it genuinely **runs out** — modelled here at 64
  advances. A part that can take only 64 security-relevant updates in a
  fifteen-year service life is a real design constraint, and it is why an SVN is
  not a version number.
* A secured-flash counter is a 32-bit value whose monotonicity comes from the
  storage protocol, not from physics. It does not run out in practice, and it is
  only as good as the replay protection underneath it.

`tests/test_rollback.py` exercises exhaustion on both.

---

## ADR-0008 — Errors are values on the verification path, exceptions elsewhere

Every input to `verify.py` and `image.parse` comes from flash, which is to say
from whoever can write to flash. A traceback on any of them is the bug, so those
functions return `VerifyResult` / `ParseResult` and never raise.

The HSM API is the opposite: asking slot 9 to sign when nothing was ever
generated there is programmer error, not attacker input, so it raises `HsmError`.
Mixing the two conventions in one codebase is a smell; splitting them on
"is this input attacker-controlled" is the line that makes it not one.

---

## ADR-0009 — A fault-injection model, at twenty lines

`Fault(force_signature_pass=True)` makes the verifier act as though the signature
compared equal when it did not. That is a simulation of a voltage or clock glitch
landing on the instruction that consumes the comparison result — the classic way
to defeat secure boot without touching the cryptography.

It earns its place because it is the only thing in the project that shows *why
measured boot exists*. Verified boot is defeated and the image runs; the PCR
moved anyway, and the attestation quote diverges. Without the fault model,
measured boot is a feature with no demonstrated purpose.

---

## ADR-0010 — The attacker is a separate binary

`secboot-attack` rather than `secboot attack`. Nothing an operator runs can
produce a malicious image by accident, and a reader looking at the entry points
in `pyproject.toml` can see which half of the project is the adversary.

---

## ADR-0011 — ECDSA signatures are fixed-width `r || s`, not DER

Added after a CI failure, which is the honest provenance.

`sig_len` lives inside the signed header, so it has to be known *before*
signing. DER-encoded ECDSA does not oblige: `r` and `s` are encoded as signed
integers, so each gains a 0x00 pad byte whenever its top bit is set. A P-256
signature is therefore 70, 71 or 72 bytes — and that is a property of the
individual signature's nonce, **not** of the key.

The first implementation signed, checked the length, and re-signed against a
corrected header, up to eight times. That looks like it converges and does not:
each retry draws a fresh nonce, so it is a coin flip every round, with about a
0.5% chance of exhausting the retries per call. The local run passed. CI, on the
same commit, did not — which is exactly the failure mode a local-only green is
supposed to catch and did not.

The fix re-encodes ECDSA signatures as fixed-width `r || s`, big-endian,
zero-padded to the curve's coordinate size: 64 bytes for P-256, 96 for P-384.
`sig_len` becomes a constant per algorithm, the retry loop disappears, and the
builder asserts the length rather than negotiating it.

This is also the better container design, and consistent with a choice already
made elsewhere: the public key travels as a raw X9.62 point for the same reason.
No boot ROM should need an ASN.1 parser to boot, and a fixed-width field is one
fewer variable-length parse on the path before the signature is checked.

`tests/test_image_roundtrip.py::test_signature_length_is_a_constant_per_algorithm`
takes sixty signatures over sixty messages. Under DER the odds of all sixty
landing on one length are about 1 in 10^19.
