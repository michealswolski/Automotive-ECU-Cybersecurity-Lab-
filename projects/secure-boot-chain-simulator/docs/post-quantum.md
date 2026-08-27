# Post-quantum signing

## The correction that matters

**CNSA 2.0 does not specify ML-DSA for firmware signing.** It specifies the
stateful hash-based signature schemes — **LMS and XMSS**, per NIST SP 800-208 —
for firmware and software signing, and names that as the *first* migration
target. ML-DSA (FIPS 204) is named for general-purpose signatures.

This is the single most common error in post-quantum-for-automotive writing, and
getting it backwards is a visible tell. So, precisely:

| Use | CNSA 2.0 names | Standard |
|-----|----------------|----------|
| Firmware and software signing | **LMS or XMSS** | NIST SP 800-208 |
| General-purpose signatures | ML-DSA-87 | FIPS 204 |
| General-purpose key establishment | ML-KEM-1024 | FIPS 203 |

FIPS 203, 204 and 205 were finalised in **August 2024**. None of them is a draft.

## Why firmware signing is the first migration target

Two reasons, and the second is the automotive one.

**Signature lifetime.** A vehicle programmed today may still be taking updates in
twenty years. A firmware signature has to remain trustworthy for the whole
service life of the part, so the migration deadline is not "when a cryptanalytic
quantum computer exists" — it is "service life before that date", which has
already started for long-lived platforms.

**Root of trust immutability.** The verification key for the first boot stage is
anchored in OTP or in mask ROM. It is the one key in the system that *cannot* be
rotated in the field. Everything else can be migrated later; this one has to be
right at production.

## Why stateful hash-based, and why that is uncomfortable

LMS and XMSS rest on nothing but the security of a hash function. No lattice
assumption, no new mathematics — which is exactly what you want for a key that
must hold for two decades and cannot be replaced.

The cost is that they are **stateful**. Each one-time key may be used exactly
once, and reusing one destroys the security of the scheme. That pushes the burden
onto the signing infrastructure: the HSM must hold the state, never roll back,
never be restored from a backup that resurrects a used index, and never be
duplicated for redundancy. That is a hard operational problem, and it is the real
reason adoption is slow.

For a signing operation performed a few thousand times over a platform's life —
which is what firmware release signing is — the trade is worth it. For a
high-volume online signer it would not be.

## What this project actually implements

`algo_id = 3` is **ML-DSA-65 (FIPS 204)**. It is a demonstration of a
post-quantum signature in the container's crypto-agility slot. It is **not** a
CNSA 2.0 firmware-signing configuration, and the code does not claim to be one.

LMS/XMSS is not implemented, for a specific reason: `cryptography` does not
expose it, and hand-rolling a stateful hash-based signature scheme — where a
state-handling bug is a total break — would violate the project's own "no
hand-rolled cryptography" rule far more seriously than implementing ECDSA would.
A real implementation would use a maintained SP 800-208 library with
HSM-resident state.

## Backend availability, and why it is probed

`cryptography` exposes ML-DSA from **47.0.0** as
`cryptography.hazmat.primitives.asymmetric.mldsa`, with broader backend coverage
in 48. The caveat that bites: **the module imports cleanly over an OpenSSL
backend and then fails at key generation.** ML-DSA needs an AWS-LC or BoringSSL
backed build, and most wheels ship OpenSSL.

So `algo.available()` generates a key to find out, rather than reading a version
number:

```
$ secboot algos
  1  ecdsa-p256   available    ECDSA on NIST P-256 with SHA-256
  2  ed25519      available    Ed25519 (EdDSA over Curve25519)
  3  ml-dsa-65    available    ML-DSA-65 (FIPS 204) — post-quantum, backend-dependent
  4  ecdsa-p384   available    ECDSA on NIST P-384 with SHA-384 — the CNSA 2.0 classical floor
```

If the backend cannot do it, `keygen --algo ml-dsa-65` fails with
`ALGO_BACKEND_UNAVAILABLE` and a message naming the cause. It never falls back,
and it never fabricates a signature.

SLH-DSA (FIPS 205) is not exposed by `cryptography` at all, so it is not offered.

## What changes in the container

Almost nothing, which is the point of having an algorithm table.

| | ECDSA P-256 | ML-DSA-65 |
|---|---|---|
| Public key | 65 bytes | 1952 bytes |
| Signature | ~71 bytes | 3309 bytes |
| Header | unchanged | unchanged |

The header carries `algo_id` and `sig_len`, and the public-key length comes from
the algorithm table (ADR-0004), so a post-quantum image is the same container
with bigger fields. What it costs is flash: roughly 5 KB more per image, per
stage. On a part with a 64 KB bootloader partition that is a real budget
conversation, and it is the conversation to have *before* the OTP is burned.
