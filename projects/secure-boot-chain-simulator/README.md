# `01` Secure Boot Chain Simulator

![status](https://img.shields.io/badge/status-Built-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![language](https://img.shields.io/badge/lang-Python-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![tests](https://img.shields.io/badge/tests-131-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![coverage](https://img.shields.io/badge/coverage-97%25-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)
![build order](https://img.shields.io/badge/build_order-first-0A1526?style=flat-square&labelColor=0A1526&color=0F1F35)

A simulated multi-stage automotive secure boot chain — **BootROM → SBL → Application** — where every stage cryptographically verifies the next before transferring control.

Hardware root of trust in OTP fuses, a simulated HSM that never releases private keys, monotonic anti-rollback counters, measured boot with a PCR bank and attestation quote, key revocation, and a hash-chained tamper-evident audit log.

> **This is a simulation.** It models hardware behaviour; it does not touch hardware. The HSM is a Python object and the fuses are a file. It is for education and demonstration, and it must not be used to protect a real device. Nothing here is production-grade, certified, or independently reviewed. See [honest claims](../../docs/honest-claims.md).

---

## Sixty seconds

```bash
cd projects/secure-boot-chain-simulator
make setup      # cryptography, typer, rich, and the dev tools
make demo       # nine scenarios, ~3 seconds, no network
```

Nine attacks, each caught by a different control, each printing the reason code and the rule that fired. Full captured output: [`docs/demo-output.md`](./docs/demo-output.md).

Two of the nine are the reason the project exists.

**The downgrade.** An image signed by the *legitimate* key, refused anyway:

```text
  ├─ ✓ SBL  svn=3  algo=ed25519  measured=bab8e448fad3…
  └─ ✗ APP  ROLLBACK_BLOCKED
       why: security version number is behind the monotonic counter
       counter: svn_app
       counter_svn: 7
       image_svn: 3
       checks that ran: 16 of 16
      control was never transferred
```

Every signature check passed. Authenticity and freshness are different properties, and only the monotonic counter provides the second. Anyone can show a *bad* signature being rejected; showing a good one being rejected, and explaining why that is correct, is a different conversation.

**The glitch.** The signature compare is forced to pass — a voltage or clock glitch on the instruction that consumes the result. Verified boot is defeated and the tampered image runs:

```text
  ├─ ✓ APP  svn=7  algo=ed25519  measured=271e0621c202…
  └─ ✓ application running

  attestation vs golden: match=False — diverged: PCR2 (Application image measurement)
```

The measurement moved anyway. That is the entire argument for running measured boot alongside verified boot, and it is the one demonstration in the project where a control *fails* and something else catches it.

---

## The modeled system

```
   power on
      │
      ▼
┌──────────────┐   verifies    ┌──────────────┐   verifies    ┌──────────────┐
│   BootROM    │──────────────▶│     SBL      │──────────────▶│  Application │
│ (immutable)  │  SBL image    │ (updatable)  │  App image    │  (updatable) │
└──────┬───────┘               └──────┬───────┘               └──────┬───────┘
       │ reads                        │ reads / stages              │ confirms
       ▼                              ▼                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  OTP FUSES (write-once)        MONOTONIC COUNTERS      PCR BANK (measured)  │
│  · root_key_hash (32 B)        · svn_sbl  (eFuse)      · PCR0 fuse state    │
│  · lifecycle_state             · svn_app  (flash)      · PCR1 SBL           │
│  · revoked_key_ids bitmap      advance-only, staged    · PCR2 APP           │
│  · secure_boot_enable          until confirm-boot      · PCR3 policy        │
└────────────────────────────────────────────────────────────────────────────┘
                          ▲
                          │  sign() · attest() · public_key()   — never export()
                  ┌───────┴────────┐
                  │  Simulated HSM │  EVITA-Medium style, keystore encrypted at rest
                  └────────────────┘
```

The BootROM holds no key. It holds the **SHA-256 of the root public key** in fuses, and validates the public key travelling inside the SBL image against that hash — a 32-byte fuse burn is cheap, storing a whole public key in OTP is not.

Stage 2 authority is **delegated**: the bootloader carries its own allowlist of application-signer hashes, so an application signing key can be rotated without touching a write-once fuse.

---

## The nine scenarios

| # | Attack | Attacker capability | Caught by |
|---|--------|--------------------|-----------|
| 1 | none — the reference run | — | `ACCEPTED`, counters staged |
| 2 | one bit flipped in the payload | flash write access | `PAYLOAD_DIGEST_MISMATCH` |
| 3 | an older release, re-signed with the **legitimate** key | an old signed release | `ROLLBACK_BLOCKED` |
| 4 | signed with the attacker's own key | their own signing infrastructure | `KEY_NOT_AUTHORIZED_FOR_STAGE` |
| 5 | the signing key is stolen, then revoked | key theft, then the OEM's response | `KEY_ID_REVOKED` |
| 6 | a bootloader image presented as the application | install access, no modification at all | `WRONG_STAGE_ID` |
| 7 | an algorithm below the machine's policy floor | a key of their choosing | `ALGO_NOT_PERMITTED` |
| 8 | the audit log edited after the fact | write access to the log | `AUDIT_CHAIN_BROKEN`, at the exact sequence number |
| 9 | the signature compare is glitched | physical access, fault injection | **not blocked** — detected by `ATTESTATION_MISMATCH` |

Plus a tenth attack that has no demo scenario but does have a test: swapping the image between verification and load. The bytes that get loaded are re-measured against the bytes that were verified, so a TOCTOU swap is caught at load time.

Each rejection prints the reason code, the expected versus actual values, and how many of the sixteen checks ran before it stopped — which makes the verification *order* visible, not just its outcome.

---

## Driving it yourself

```bash
export PATH="$PWD/.venv/bin:$PATH"          # or just use `python -m secboot`

secboot keygen --slot 0 --algo ed25519      # root key, inside the simulated HSM
secboot keygen --slot 1 --algo ed25519      # application signing key
secboot fuses init --root-slot 0            # burn root_key_hash, enable secure boot
secboot authorize-app-signer --slot 1       # delegate stage-2 authority

secboot build --stage sbl --svn 3 --slot 0 --payload sbl.bin -o images/sbl.sbi
secboot build --stage app --svn 7 --slot 1 --payload app.bin -o images/app.sbi
secboot boot  --sbl images/sbl.sbi --app images/app.sbi
secboot confirm-boot                        # commits the staged SVN advance

secboot-attack downgrade --in images/app.sbi --out images/old.sbi --svn 3 --slot 1
secboot boot --sbl images/sbl.sbi --app images/old.sbi     # ROLLBACK_BLOCKED, exit 2
```

`secboot fuses show`, `secboot slots`, `secboot policy`, `secboot algos`, `secboot inspect`, `secboot attest`, `secboot audit verify|tail|tamper`. Every subcommand has `--help`.

The attacker tooling is a **separate binary** so the intent is never ambiguous: nothing an operator runs can produce a malicious image by accident.

---

## What is enforced, and where

The verifier runs sixteen checks in a fixed order — cheap and structural before expensive and cryptographic. That is not a performance argument: attempting a signature check over lengths that have not been validated is how bootloaders get exploited.

| Step | Check | Step | Check |
|---|---|---|---|
| 1 | `IMAGE_TOO_SHORT` | 9 | `UNKNOWN_ALGO` |
| 2 | `BAD_MAGIC` | 10 | `ALGO_NOT_PERMITTED` |
| 3 | `UNSUPPORTED_HEADER_VERSION` | 11 | `KEY_ID_REVOKED` |
| 4 | `RESERVED_NOT_ZERO` | 12 | `ROOT_KEY_MISMATCH` |
| 5 | `HEADER_CRC_MISMATCH` | 13 | `KEY_NOT_AUTHORIZED_FOR_STAGE` |
| 6 | `WRONG_STAGE_ID` | 14 | `PAYLOAD_DIGEST_MISMATCH` |
| 7 | `LENGTH_OVERFLOW` | 15 | `SIGNATURE_INVALID` |
| 8 | `SECURE_BOOT_DISABLED` | 16 | `ROLLBACK_BLOCKED` → `ACCEPTED` |

Every one is individually reachable and individually tested, and each test asserts that **no later check ran** — the order is observable from the audit log, so it is a property the build can fail on rather than a comment.

Full table with the threat each detects: [`docs/reason-codes.md`](./docs/reason-codes.md).

---

## Standards

| Control implemented | Maps to |
|---|---|
| Chain of trust from immutable ROM, hardware-anchored root key | NIST SP 800-193 (protect / detect / recover), ISO/SAE 21434 |
| Anti-rollback via monotonic counter and SVN | UN ECE R155 Annex 5 (outdated software version), NIST SP 800-193 |
| Key revocation via burned fuse bits | ISO/SAE 21434, R155 CSMS |
| Measured boot and attestation quote | TCG PCR-extend model, NIST SP 800-155 — **emulated**, see the caveat below |
| Crypto-agility allowlist, ECDSA P-384 floor, PQ slot | NSA CNSA 2.0, NIST SP 800-208 (LMS/XMSS), FIPS 204 (ML-DSA) |
| HSM key custody, non-exportable keys, usage flags | SAE J3101 (J3101_202002), EVITA HSM profiles |
| Tamper-evident audit log | ISO/SAE 21434 continuous cybersecurity activities |
| SVN separate from image version, staged advance | UN ECE R156, ISO 24089:2023 + Amd 1:2024 |

Two things this project is careful to get right, because both are commonly stated backwards:

- **CNSA 2.0 specifies LMS or XMSS for firmware signing**, not ML-DSA. The ML-DSA-65 backend here is a FIPS 204 *demonstration*, not a CNSA-compliant firmware-signing configuration. [`docs/post-quantum.md`](./docs/post-quantum.md).
- **Most automotive HSMs are SHE or EVITA class, not TPMs.** The PCR bank emulates the TCG model; there is no dominant automotive attestation standard today. [`docs/verified-vs-measured-boot.md`](./docs/verified-vs-measured-boot.md).

What each standard actually asks for, and which function answers it: [`docs/standards-references.md`](./docs/standards-references.md). Editions are pinned and dated in the lab's [standards register](../../docs/standards-register.md).

---

## Layout

```
secure-boot-chain-simulator/
├── src/secboot/
│   ├── image.py       container pack / parse, structural checks (steps 1–7)
│   ├── verify.py      the verifier (steps 8–16) — the heart of the project
│   ├── machine.py     the ECU: orchestration, measurement, load-time re-check
│   ├── hsm.py         simulated HSM — keys go in, they do not come out
│   ├── algo.py        the algorithm table; no cryptography is implemented here
│   ├── fuses.py       OTP fuses and the two monotonic-counter substrates
│   ├── policy.py      what this machine will accept
│   ├── measure.py     the PCR bank and the attestation quote
│   ├── audit.py       hash-chained JSONL
│   ├── attacks.py     producing malicious images
│   ├── demo.py        the nine scenarios
│   └── cli.py · attack_cli.py · builder.py · render.py · reasons.py
├── tests/             131 tests, 97% coverage, golden demo output
└── docs/              threat model, reason codes, ADRs, standards, PQ
```

Documentation worth reading in order: [threat model](./docs/threat-model.md) → [verified vs measured boot](./docs/verified-vs-measured-boot.md) → [decisions](./docs/decisions.md) → [post-quantum](./docs/post-quantum.md).

---

## Checks

```bash
make check      # ruff · mypy --strict · pytest with an 85% coverage floor
make demo       # the nine scenarios
make clean      # remove runtime state
```

`make check` is exactly what [`.github/workflows/secboot.yml`](../../.github/workflows/secboot.yml) runs. It is not a subset of it — a local gate narrower than the remote one produces confident, wrong pushes.

---

## The decisions worth arguing about

Recorded as ADRs in [`docs/decisions.md`](./docs/decisions.md). The one that matters most:

**When does the monotonic counter actually advance?** Advance it at verification time and a signed-but-broken update bricks the part, because the known-good older image is now below the counter and there is no path back. Advance it only after the application reports a healthy start, and you need a confirmation mechanism plus a window in which the old image still boots — a window an attacker who can suppress the confirmation can hold open.

This implements the second: `stage_advance()` records a pending value and `secboot confirm-boot` commits it. The window is the price, and a production design would bound it with a boot-attempt counter or a hardware watchdog that performs the confirmation itself.

Also worth reading: why measurements cover the authenticated bytes rather than the whole file (ADR-0003), why the public-key length is derived from the algorithm rather than carried in the header (ADR-0004), and why the container digest stays SHA-256 while signatures follow the algorithm (ADR-0005).

---

## Extending it

* **A C reference verifier** (`SPEC.md` §11) — parse the same container with no dynamic allocation, no recursion, fixed buffers and `-Wall -Wextra -Werror -fanalyzer`, plus a libFuzzer target and a cross-check test asserting it agrees with the Python verifier on every fixture. Proves the format is implementable in a ROM-sized environment.
* **Recovery** — the honest gap against NIST SP 800-193. There is no A/B slot and no golden recovery image, and both are what a real design needs.
* **LMS or XMSS signing** via a maintained SP 800-208 library with HSM-resident state. Deliberately not hand-rolled: a state-handling bug in a stateful hash-based scheme is a total break.
* **A boot-attempt counter** that bounds the unconfirmed window in ADR-0002.

---

## Claim discipline

Say: *"I designed and implemented a simulated secure boot chain in Python — a signed image container format, a sixteen-step verification order with individually tested reason codes, monotonic anti-rollback counters with a staged-advance confirmation, key revocation, measured boot with a PCR model and attestation, and a hash-chained audit log. It includes a fault-injection model that defeats verified boot, to show why measured boot is there."*

Do not say that you shipped secure boot on a production ECU, that you have hands-on experience with a vendor HSM you have not used, or that the cryptography has been independently reviewed.

If asked whether it is real hardware, lead with the answer: it is a simulation, and here is precisely which parts map to hardware and which do not.

---

## The kit this was built from

| File | Purpose |
|---|---|
| [`SPEC.md`](./SPEC.md) | The source of truth: byte layouts, verification order, reason codes |
| [`BUILD_PLAN.md`](./BUILD_PLAN.md) | The phase order the build followed |
| [`ACCEPTANCE.md`](./ACCEPTANCE.md) | The definition of done — every box now ticked |
| [`CORRECTIONS.md`](./CORRECTIONS.md) | Standards anchors that had moved since the spec was written |
| [`CLAUDE.md`](./CLAUDE.md) | Standing constraints for the build |
| [`docs/interview-talking-points.md`](./docs/interview-talking-points.md) | How to talk about it |
