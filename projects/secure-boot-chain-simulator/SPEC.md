# SPEC — Secure Boot Chain Simulator

Version 1.0. This document is the source of truth. If code and spec disagree, fix one of them
deliberately and note it in `docs/decisions.md`.

---

## 1. Purpose and scope

Model, in software, the chain of trust an automotive ECU establishes at power-on, plus the two
controls that most often decide whether that chain actually holds in the field: **rollback
protection** and **key revocation**.

In scope: image format, signature verification, OTP/fuse model, monotonic counters, measured boot,
audit logging, key revocation, an attacker CLI that produces malicious images.

Out of scope: real hardware, real HSM drivers, actual code execution of loaded payloads (payloads
are opaque blobs), OTA transport, UDS/diagnostics.

---

## 2. The modeled system

```
   power on
      │
      ▼
┌──────────────┐   verifies    ┌──────────────┐   verifies    ┌──────────────┐
│   BootROM    │──────────────▶│     SBL      │──────────────▶│  Application │
│ (immutable)  │  SBL image    │ (updatable)  │  App image    │  (updatable) │
└──────┬───────┘               └──────┬───────┘               └──────────────┘
       │                              │
       │ reads                        │ reads / advances
       ▼                              ▼
┌───────────────────────────────────────────────────────────┐
│  OTP FUSES (write-once)          MONOTONIC COUNTERS       │
│  - root_key_hash (32 B)          - svn_sbl                │
│  - lifecycle_state               - svn_app                │
│  - revoked_key_ids bitmap        (increment only, never   │
│  - secure_boot_enable             decrement, persisted)   │
└───────────────────────────────────────────────────────────┘
                          ▲
                          │ sign() / verify() / get_pubkey()   (private keys never exported)
                  ┌───────┴────────┐
                  │  Simulated HSM │
                  └────────────────┘
```

**BootROM** is immutable: it is code, not data, and it is trusted by axiom. It holds no key — it
holds the **SHA-256 hash** of the root public key in fuses, and validates the root public key
embedded in the SBL image against that hash. This is the standard pattern (a 32-byte fuse burn is
cheap; storing a whole public key in OTP is not).

---

## 3. Image container format

All multi-byte integers are **big-endian** (automotive convention, matches AUTOSAR SecOC byte order).
The header is fixed-size, 128 bytes, so a ROM can parse it without dynamic allocation.

| Offset | Size | Field              | Notes |
|--------|------|--------------------|-------|
| 0x00   | 4    | `magic`            | ASCII `SBI1` (0x53424931) |
| 0x04   | 2    | `header_version`   | 0x0001 |
| 0x06   | 2    | `stage_id`         | 1 = SBL, 2 = APP |
| 0x08   | 4    | `svn`              | Security Version Number — rollback protection input |
| 0x0C   | 4    | `image_version`    | Informational only (e.g. 0x01_02_0003 = 1.2.3). **Never** used for rollback decisions |
| 0x10   | 4    | `payload_len`      | bytes |
| 0x14   | 4    | `load_address`     | modeled only; not dereferenced |
| 0x18   | 2    | `algo_id`          | 1 = ECDSA-P256-SHA256, 2 = Ed25519, 3 = ML-DSA-65 |
| 0x1A   | 2    | `key_id`           | index into the key slot table; used for revocation |
| 0x1C   | 32   | `payload_sha256`   | digest of payload bytes |
| 0x3C   | 4    | `sig_len`          | |
| 0x40   | 32   | `signer_pubkey_sha256` | for stage 1 this must equal the fuse `root_key_hash` |
| 0x60   | 28   | `reserved`         | zero-filled; verifier MUST reject non-zero (forward-compat trap) |
| 0x7C   | 4    | `header_crc32`     | integrity of header only — a *detection* aid, never a security control |

Then: `payload` (`payload_len` bytes), `signer_pubkey` (DER/raw per algo), `signature` (`sig_len` bytes).

**Signed data** = `header[0x00:0x7C]` (header excluding CRC) `||` `payload`. The public key travels
with the image and is bound to the chain by hash, not by the signature.

Implement as `secboot/image.py` with `pack()` / `unpack()` and exhaustive bounds checks. Every parse
failure returns a distinct reason code — never a Python traceback.

---

## 4. Verification algorithm (the core of the project)

`verify_stage(machine, image_bytes, expected_stage_id) -> VerifyResult`, executed in this order.
Order matters and must be tested — cheap checks before expensive ones, and structural before
cryptographic:

1. `IMAGE_TOO_SHORT` — buffer smaller than 128-byte header.
2. `BAD_MAGIC` — magic mismatch.
3. `UNSUPPORTED_HEADER_VERSION`.
4. `RESERVED_NOT_ZERO`.
5. `HEADER_CRC_MISMATCH`.
6. `WRONG_STAGE_ID` — an SBL image presented as an app (prevents stage-confusion attacks).
7. `LENGTH_OVERFLOW` — `payload_len + sig_len + pubkey_len` exceeds the buffer.
8. `SECURE_BOOT_DISABLED` — fuse check; if disabled, log a loud WARN and continue (models a
   development part) — but only if `--allow-insecure` was passed, else `HALT`.
9. `UNKNOWN_ALGO` / `ALGO_NOT_PERMITTED` — algorithm not in the machine's policy allowlist.
   (Models crypto-agility policy: a fielded ECU should refuse a downgraded algorithm.)
10. `KEY_ID_REVOKED` — key ID bit set in the fuse revocation bitmap.
11. `ROOT_KEY_MISMATCH` (stage 1 only) — `SHA256(signer_pubkey) != fuse.root_key_hash`.
12. `KEY_NOT_AUTHORIZED_FOR_STAGE` (stage 2) — SBL holds an embedded allowlist of app signer key hashes.
13. `PAYLOAD_DIGEST_MISMATCH` — computed SHA-256 of payload vs header field.
14. `SIGNATURE_INVALID` — the actual signature check. **Constant-time comparison for any digest
    equality on this path** (`hmac.compare_digest`).
15. `ROLLBACK_BLOCKED` — `image.svn < counter.svn(stage)`.
16. Accept.

On accept, the loader **measures** the stage (see §6), then advances the monotonic counter if
`image.svn > counter.svn(stage)` (see §5), then transfers control.

Every step emits an audit event, including the ones that pass. A verifier that only logs failures is
useless for forensics.

---

## 5. Anti-rollback / monotonic counters

- Counters live in `secboot/fuses.py`, persisted to a JSON file under a state directory.
- The API is deliberately hostile to misuse:
  - `read(name) -> int`
  - `advance(name, to: int) -> Result` — succeeds only if `to > current`. Any attempt to write an
    equal or lower value returns `COUNTER_MONOTONICITY_VIOLATION` and is logged as a **critical**
    audit event. There is no `set()` and no `reset()` in the production API.
  - A separate `secboot fuses factory-reset --i-understand` exists **only** in the CLI for demo
    reruns, is refused when `lifecycle_state == PRODUCTION`, and logs a CRITICAL event.
- Counter advance policy: advance **after** a successful verify and **before** control transfer.
  Document the tradeoff in `docs/decisions.md`: advancing before the new image has proven itself
  bricks a device on a bad-but-signed update; advancing after first successful application boot
  requires a confirmation step. Implement the safer variant: mark `pending_svn`, and require an
  explicit `secboot confirm-boot` (models a watchdog/health-check confirmation) before the counter
  is permanently advanced. This nuance is exactly what an interviewer will probe.
- Counter width is 32-bit; model exhaustion by refusing to advance past `0xFFFFFFFE` with
  `COUNTER_EXHAUSTED`.

---

## 6. Measured boot

Alongside verified boot, maintain a simulated PCR bank (`secboot/measure.py`):

```
PCR[n] = SHA256(PCR[n] || measurement)
```

- PCR0: BootROM configuration (fuse state digest)
- PCR1: SBL image digest
- PCR2: App image digest
- PCR3: policy digest (allowed algorithms, revocation bitmap)

`secboot attest` prints the final PCR bank and a JSON quote structure signed by an HSM-held
attestation key. Provide `secboot attest --verify quote.json --expected golden.json` which diffs
actual vs expected PCRs and names which stage diverged. This is what turns "I built secure boot"
into "I built secure boot *and* remote attestation", and it costs about 80 lines.

Document the distinction in `docs/verified-vs-measured-boot.md`: verified boot **blocks**, measured
boot **records**. Production designs use both.

---

## 7. Simulated HSM

`secboot/hsm.py`. Models an EVITA-Medium style hardware security module.

- Key slots identified by `key_id` (int) with metadata: algorithm, usage flags
  (`SIGN` | `VERIFY` | `ATTEST`), exportable=False, creation time.
- Public API: `generate(slot, algo)`, `sign(slot, data) -> bytes`, `public_key(slot) -> bytes`,
  `revoke(slot)`, `slots() -> list[SlotInfo]`.
- Private key material is stored in a module-private structure. **No accessor returns it.**
- Persisted to an encrypted-at-rest keystore file: AES-256-GCM with a key derived from a
  passphrase via Scrypt (`n=2**15, r=8, p=1`). Models "keys protected by the HSM boundary".
  If no passphrase is supplied, use a dev-mode passphrase and print a loud warning.
- Add a simulated `--hsm-latency-ms` so the demo can show that signature verification is not free —
  useful for the "what's your boot-time budget?" conversation.

---

## 8. Audit log

`secboot/audit.py`. JSON Lines, one event per line, append-only.

```json
{"seq":14,"ts":"2026-08-19T14:03:11.412Z","stage":"SBL","event":"VERIFY","decision":"REJECT",
 "reason":"ROLLBACK_BLOCKED","detail":{"image_svn":3,"counter_svn":5},"key_id":2,
 "measurement":"9f86d0…","pcr2":"a1b2…","prev_hash":"c3d4…","hash":"e5f6…"}
```

- Each record includes `prev_hash` and `hash = SHA256(prev_hash || canonical_json(record_without_hash))`,
  forming a hash chain. `secboot audit verify` walks the chain and reports the exact sequence number
  where tampering occurred. Include a demo command `secboot audit tamper --seq 7` that edits a record
  so the verification failure can be shown live.
- Reason codes live in a single `ReasonCode` StrEnum and are documented in `docs/reason-codes.md`
  with, for each code, the threat it detects and the standard clause it maps to.

---

## 9. CLI surface

Use `typer`. Command groups:

```
secboot keygen --slot 0 --algo ecdsa-p256        # create keys in the simulated HSM
secboot fuses init --root-slot 0                 # burn root key hash, enable secure boot
secboot fuses show
secboot build --stage sbl --svn 3 --slot 0 --payload build/sbl.bin -o images/sbl.sbi
secboot build --stage app --svn 7 --slot 1 --payload build/app.bin -o images/app.sbi
secboot boot --sbl images/sbl.sbi --app images/app.sbi
secboot confirm-boot                             # commits pending SVN advance
secboot attest [--verify quote.json]
secboot audit verify | secboot audit tail | secboot audit tamper --seq N
secboot revoke --key-id 1
secboot demo [--scenario all|happy|corrupt|downgrade|revoked|stage-confusion|algo-downgrade]
```

Attacker tooling (deliberately separate binary name so the intent is obvious):

```
secboot-attack corrupt      --in images/app.sbi --out images/app_corrupt.sbi --byte-offset 200 --bit 3
secboot-attack downgrade    --in images/app_v7.sbi --out images/app_v3.sbi   # re-sign an older SVN with a valid key
secboot-attack strip-sig    --in images/app.sbi --out images/app_nosig.sbi
secboot-attack swap-stage   --in images/sbl.sbi --out images/fake_app.sbi
secboot-attack forge        --in images/app.sbi --out images/app_forged.sbi  # sign with an attacker key
```

---

## 10. Demo scenarios (the deliverable an interviewer sees)

`secboot demo` runs these in order, narrating each. Each must render in under 2 seconds.

| # | Scenario | Expected outcome |
|---|----------|------------------|
| 1 | Clean boot, valid SBL + valid App | ROM→SBL→APP accepted, PCRs extended, counters advanced after confirm |
| 2 | Single bit flipped in app payload | REJECT `PAYLOAD_DIGEST_MISMATCH` at stage 2, control never transfers, PCR2 diverges from golden |
| 3 | Attacker re-signs an older app (SVN 3) with the *legitimate* key | REJECT `ROLLBACK_BLOCKED` — signature is valid, freshness is not. This is the money slide. |
| 4 | Attacker signs with their own key | REJECT `ROOT_KEY_MISMATCH` / `KEY_NOT_AUTHORIZED_FOR_STAGE` |
| 5 | Signing key compromised, then revoked | Image that booted a minute ago now REJECTs `KEY_ID_REVOKED` |
| 6 | SBL image presented as app image | REJECT `WRONG_STAGE_ID` |
| 7 | Image requests a weaker algorithm than policy allows | REJECT `ALGO_NOT_PERMITTED` |
| 8 | Audit log record edited after the fact | `audit verify` fails at the exact sequence number |

Each scenario prints: the attack performed, the stage that caught it, the reason code, and the
one-line explanation of the control that fired.

---

## 11. Optional Phase 6 — C reference verifier

A small C program (`c_ref/`, built with CMake, no external deps beyond a vendored SHA-256 and
`libtomcrypt`-style ECDSA *or* mbedTLS if available) that parses the same `.sbi` container and
performs the same verification order, printing the same reason codes. Purpose: show the format is
implementable in a ROM-sized environment, and give an embedded-C talking point.

Constraints if implemented: no dynamic allocation, no recursion, fixed-size buffers, all lengths
validated before use, `-Wall -Wextra -Werror -fanalyzer`, and a fuzz target
(`c_ref/fuzz_parse.c` with libFuzzer) run for 60 seconds in CI. Cross-check: a pytest that builds
the C binary and asserts it produces the same verdict as the Python verifier for all fixtures.

---

## 12. Standards mapping (put this in the README — it is why this project reads as senior)

| Control implemented | Maps to |
|---|---|
| Chain of trust from immutable ROM, hardware-anchored root key | NIST SP 800-193 (Protect/Detect/Recover), ISO/SAE 21434 Clause 10 (Product development) |
| Anti-rollback via monotonic counter + SVN | UN ECE R155 Annex 5 threat set (firmware modification / rollback), NIST SP 800-193 |
| Key revocation | ISO/SAE 21434 Clause 9 (Concept), R155 CSMS requirements |
| Measured boot / attestation quote | NIST SP 800-155 style firmware measurement, TCG PCR-extend model |
| Crypto-agility policy allowlist, PQ-ready signature slot | NSA CNSA 2.0 (firmware signing first), NIST SP 800-208 (LMS/XMSS), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA) |
| HSM key custody, non-exportable keys | EVITA HSM profiles, SAE J3101 (hardware-protected security for ground vehicles), AUTOSAR CSM / Crypto stack |
| Tamper-evident audit log | ISO/SAE 21434 Clause 8 (Continuous cybersecurity activities) — evidence for incident response |

Write `docs/standards-references.md` with one paragraph per row explaining *what the standard
actually asks for* and *which function in this repo satisfies it*. Verify clause numbers with a web
search before asserting them; if you cannot verify a clause number, cite the standard by name only.

---

## 13. Repository layout

```
secure-boot-chain-simulator/
├── README.md               # what it is, the GIF/asciinema, one-command demo, standards table
├── pyproject.toml
├── Makefile                # make setup | check | demo | clean
├── src/secboot/
│   ├── __init__.py  __main__.py  cli.py  attack_cli.py
│   ├── image.py            # container pack/unpack
│   ├── verify.py           # §4 — the heart
│   ├── hsm.py              # §7
│   ├── fuses.py            # §5
│   ├── measure.py          # §6
│   ├── audit.py            # §8
│   ├── policy.py           # algorithm allowlist, lifecycle state
│   ├── reasons.py          # ReasonCode StrEnum
│   ├── machine.py          # Machine context object, boot orchestration
│   └── render.py           # rich output
├── tests/
│   ├── test_image_roundtrip.py     test_verify_order.py
│   ├── test_rollback.py            test_revocation.py
│   ├── test_audit_chain.py         test_hsm_isolation.py
│   ├── test_malformed_images.py    # fuzz-ish: random mutations must never traceback
│   └── test_demo_golden.py         # golden output comparison with --seed
├── docs/
│   ├── threat-model.md  reason-codes.md  standards-references.md
│   ├── verified-vs-measured-boot.md  decisions.md
├── examples/ images/ (gitignored build artifacts)
└── .github/workflows/ci.yml
```

---

## 14. Explicit non-goals

- Do not claim this is a security product. The README says, in the first paragraph, that this is a
  simulation for education and demonstration and must not be used to protect real devices.
- Do not implement real HSM PKCS#11 integration.
- Do not add a web UI. A terminal demo is more credible for this audience.
