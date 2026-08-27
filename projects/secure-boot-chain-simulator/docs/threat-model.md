# Threat model

Scoped to what this project models: the boot chain of one ECU, from power-on to
the application reporting a healthy start. Out of scope: the OTA transport, the
backend that signs releases, the rest of the vehicle network, and physical
attacks that do not target the boot decision.

## Assets

| Asset | Why an attacker wants it | Loss if it goes |
|-------|--------------------------|-----------------|
| Application code integrity | Running attacker code on an ECU with bus access | Vehicle function under attacker control |
| Root signing key | Signs anything the chain will accept, on every part in the fleet | Whole-fleet compromise; only revocation and a re-key recover it |
| Application signing key | Signs stage 2 on every part | Fleet-wide, recoverable by revoking one delegated key |
| Monotonic counter state | Lowering it re-enables every patched vulnerability | Silent regression to a known-exploitable release |
| Audit log | Rewriting it hides the intrusion | No incident response |
| Attestation key | Forging quotes makes a compromised part look clean | Fleet monitoring becomes noise |

## Actors

| Actor | Capability assumed | Not assumed |
|-------|--------------------|-------------|
| Remote attacker via a compromised OTA path | Deliver an arbitrary image the device will attempt to boot | Any key; physical access |
| Owner or tuner with physical access | Read and write flash freely; reset the part; power and clock control | The signing keys; breaking the HSM boundary |
| Supply-chain attacker | An old, genuinely signed release, and a way to install it | Producing a *new* signature |
| Key thief | The application signing key | The root key in OTP; the ability to un-revoke |
| Insider at the OEM | The root signing key | Changing burnt fuses on parts already in the field |

## STRIDE

| Threat | Instance in this system | Control | Where |
|--------|------------------------|---------|-------|
| **S**poofing | An image signed by a key that is not the root | Fuse `root_key_hash` compared against `SHA-256(signer_pubkey)` | `verify.py` step 11 |
| | A key not delegated for stage 2 | The bootloader's app-signer allowlist | step 12 |
| | A forged attestation quote | Attestation key is ATTEST-only and lives in the HSM | `hsm.attest` |
| **T**ampering | A bit flipped in the payload | `payload_sha256` inside the signed header | step 14 |
| | The payload replaced and the digest recomputed | Signature over header ‖ payload | step 15 |
| | The image swapped after verification | Load-time re-measure against the verified bytes | `machine._run_stage` |
| | The audit log edited | Hash chain, with the broken sequence number named | `audit.verify` |
| | A counter written downwards | No setter exists; `advance()` refuses | `fuses.advance` |
| **R**epudiation | "Nothing unusual booted" | Every decision logged, passes included, chained | `audit.py` |
| **I**nformation disclosure | Extracting a private key | No API returns one; keystore encrypted at rest; enforced by an AST scan | `hsm.py`, `tests/test_hsm_isolation.py` |
| | A verifier that leaks *why* a signature failed | Every signature failure collapses to one code | `algo.verify_signature` |
| **D**enial of service | A malformed image crashing the ROM | Errors are values; 500 random mutations produce reason codes | `tests/test_malformed_images.py` |
| | Bricking a part by advancing past the good image | Staged advance plus `confirm-boot` | ADR-0002 |
| | Exhausting the fuse counter | `COUNTER_EXHAUSTED`, and an SVN that is not a version number | ADR-0007 |
| **E**levation of privilege | A bootloader image run as the application | `stage_id` inside the signed header | step 6 |
| | Downgrading the algorithm to one the ROM still supports | Policy allowlist | step 10 |
| | Booting a production part with the fuse unburned | `SECURE_BOOT_DISABLED` unless `--allow-insecure` | step 8 |

## Attack trees

### From a compromised OTA server

```
Run attacker code on the ECU
├── Deliver a modified image
│   ├── edit the payload ................... PAYLOAD_DIGEST_MISMATCH
│   ├── edit the payload and fix the digest . SIGNATURE_INVALID
│   └── strip the signature ................. SIGNATURE_INVALID
├── Deliver an image signed by another key
│   ├── the attacker's own key .............. ROOT_KEY_MISMATCH / KEY_NOT_AUTHORIZED_FOR_STAGE
│   └── a stolen, then revoked key .......... KEY_ID_REVOKED
├── Deliver a genuine image in the wrong slot
│   └── the bootloader, as the application .. WRONG_STAGE_ID
├── Deliver a genuine *older* image ......... ROLLBACK_BLOCKED   ← nothing else catches this
└── Ask for a weaker algorithm .............. ALGO_NOT_PERMITTED
```

### From physical flash access

```
Run attacker code on the ECU
├── Everything in the OTA tree above ........ same controls; write access is not signing authority
├── Swap the image between verify and load .. TOCTOU re-check at load time
├── Rewrite the audit log ................... AUDIT_CHAIN_BROKEN at the edited sequence number
├── Lower the monotonic counter ............. no API path exists; OTP fuses are physics
└── Glitch the signature compare ............ NOT BLOCKED — the image runs.
    └── Detected afterwards ................. PCR2 diverges; the attestation quote fails
```

That last leaf is the honest one. Verified boot does not stop a successful
glitch. Measured boot is what turns it from an undetectable compromise into a
detectable one, and that is the entire argument for running both.

## What this model does not cover

* The signing infrastructure itself. A compromised release pipeline signs
  whatever it is told to, and no on-device control can tell the difference.
* Side channels, decapping, and reading key material off the die.
* The bootloader's own code quality. This project verifies images; it does not
  model a buffer overflow in the parser that verifies them. (`image.parse` is
  written as though it were: every length validated before use, no allocation
  from attacker-controlled sizes.)
* Recovery. There is no A/B slot, no rollback-to-golden, no fail-safe image.
  A real design needs all three.
