# Reason codes

Every decision the chain makes comes back as one of these. They are stable
strings, not messages: a service tool matches on the code, a human reads the
explanation. The order below is the order the verifier evaluates them, and that
order is a security property — see `SPEC.md` section 4 and
`tests/test_verify_order.py`.

## The verification path

| # | Code | Threat it detects | Where it is enforced |
|---|------|-------------------|----------------------|
| 1 | `IMAGE_TOO_SHORT` | A truncated or absent image; indexing a buffer that cannot hold a header | `image.parse` |
| 2 | `BAD_MAGIC` | Something that is not a boot image at all — wrong partition, uninitialised flash | `image.parse` |
| 3 | `UNSUPPORTED_HEADER_VERSION` | A container this ROM cannot parse. Refusing beats guessing at the layout | `image.parse` |
| 4 | `RESERVED_NOT_ZERO` | Data smuggled in unused header bytes, and a forward-compatibility trap: refusing non-zero now is what makes it safe to assign meaning later | `image.parse` |
| 5 | `HEADER_CRC_MISMATCH` | Flash bit-rot. **Not** a security control — an attacker recomputes it | `image.parse` |
| 6 | `WRONG_STAGE_ID` | Stage confusion: a genuine, correctly signed bootloader offered where the application belongs | `image.parse` |
| 7 | `LENGTH_OVERFLOW` | The classic bootloader vulnerability — attacker-controlled lengths used before validation. Also catches bytes hidden after the signature | `image.parse` |
| 8 | `SECURE_BOOT_DISABLED` | A production part whose enable fuse was never burned. Survivable only with `--allow-insecure`, and then loudly | `verify.verify_stage` |
| 9 | `UNKNOWN_ALGO` | An algorithm identifier this verifier does not implement | `verify.verify_stage` |
| 10 | `ALGO_NOT_PERMITTED` | Algorithm downgrade: the verifier *can* run it and the machine's policy refuses to | `verify.verify_stage` |
| 11 | `KEY_ID_REVOKED` | A compromised key, retired by burning its bit in the fuse bitmap. Checked before any signature work, because a revoked key's signature is still mathematically valid | `verify.verify_stage` |
| 12 | `ROOT_KEY_MISMATCH` | Stage 1 signed by anything other than the key whose hash is burned in OTP | `verify.verify_stage` |
| 13 | `KEY_NOT_AUTHORIZED_FOR_STAGE` | Stage 2 signed by a key the bootloader does not delegate to | `verify.verify_stage` |
| 14 | `PAYLOAD_DIGEST_MISMATCH` | Payload corruption or substitution, caught before an HSM operation is spent. Also raised at load time by the TOCTOU re-check | `verify.verify_stage`, `machine._run_stage` |
| 15 | `SIGNATURE_INVALID` | Forgery, a stripped signature, or a payload edited after signing | `verify.verify_stage` |
| 16 | `ROLLBACK_BLOCKED` | A **validly signed** older release. Authenticity and freshness are different properties, and only this control provides the second | `verify.verify_stage` |
| — | `ACCEPTED` | Every control passed | everywhere |

## Fuses and counters

| Code | Meaning |
|------|---------|
| `COUNTER_MONOTONICITY_VIOLATION` | An attempt to write a counter to an equal or lower value. Logged critical: nothing legitimate does this |
| `COUNTER_EXHAUSTED` | The substrate has no advances left — fuse bits burned, or a 32-bit counter at its ceiling |
| `NO_PENDING_ADVANCE` | `confirm-boot` with nothing staged |
| `FUSE_ALREADY_BURNED` | A write-once fuse, or a lifecycle state that only moves forward |
| `FACTORY_RESET_REFUSED` | The demo escape hatch, refused in `PRODUCTION` |

## Everything else

| Code | Meaning |
|------|---------|
| `ALGO_BACKEND_UNAVAILABLE` | The installed `cryptography` build cannot perform this algorithm — almost always ML-DSA over an OpenSSL backend |
| `KEY_SLOT_MISSING` | No key in the slot, or a slot used outside its usage flags |
| `AUDIT_CHAIN_BROKEN` | The audit log hash chain does not verify, with the sequence number where it broke |
| `ATTESTATION_MISMATCH` | A PCR differs from the golden reference |

## Standards mapping

Individual clause numbers are deliberately not asserted here. The controls these
codes enforce map to NIST SP 800-193 (firmware resiliency: protect, detect,
recover), UN ECE R155 Annex 5 (firmware modification and rollback threats),
ISO/SAE 21434 (cybersecurity engineering, including the continuous activities
that make an audit log evidence rather than telemetry) and SAE J3101 (hardware
protected security for ground vehicles). `standards-references.md` says what each
one actually asks for and which function here answers it.
