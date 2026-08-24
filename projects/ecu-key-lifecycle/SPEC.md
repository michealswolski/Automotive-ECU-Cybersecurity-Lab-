# SPEC - ECU Key Lifecycle Manager

Version 1.0. Source of truth. Deviations recorded in `docs/decisions.md`.

---

## 1. Purpose

Model the complete lifecycle of cryptographic keys across a simulated vehicle ECU fleet, from
generation in a backend key authority through provisioning, use, rotation, revocation, and
destruction -- with auditable evidence for each transition.

In scope: key hierarchy and derivation, a simulated HSM/KMS boundary, a provisioning ceremony over a
simulated transport, lifecycle state machine, cryptoperiod enforcement, rotation with overlap,
revocation and distribution of a signed revocation list, protected storage on the ECU side,
hash-chained audit, and reporting.

Out of scope: real HSM/PKCS#11 integration, real OTA transport, real ECUs, a production PKI.

---

## 2. Actors

| Actor | Module | Role |
|---|---|---|
| **Key Authority (KA)** | `src/ekl/authority/` | Backend. Owns the simulated HSM, generates and derives keys, signs provisioning packages and revocation lists, holds the master audit log. |
| **Simulated HSM** | `src/ekl/authority/hsm.py` | Non-exportable key custody, sign/verify/derive/wrap operations only. |
| **ECU** | `src/ekl/ecu/` | Simulated device. Has a device identity keypair, protected storage, a local key store, and a local audit trail. |
| **Operator** | `src/ekl/cli.py` | The human. Runs ceremonies, inspects state, triggers rotation and revocation. |
| **Attacker** | `src/ekl/attack.py` | Tries to tamper with the audit log, replay a provisioning package, use a revoked key, and downgrade to a retired key generation. |

---

## 3. Key hierarchy

```
Root Signing Key (offline, Ed25519)              generated once, used to sign OEM keys
  └── OEM Fleet Signing Key (Ed25519)            signs provisioning packages, revocation lists
        └── per-ECU Device Identity Key (ECDSA P-256, generated ON the ECU, never leaves)
              └── Device Attestation Cert (signed by OEM key at manufacture)

Symmetric material, derived per (ECU, purpose, generation) via HKDF-SHA256:
  Master Symmetric Key (AES-256, in HSM)
    ├── SecOC MAC key   -- info = "secoc-mac"  || ecu_id || data_id || generation
    ├── Diagnostic key  -- info = "uds-auth"   || ecu_id || generation
    └── Storage KEK     -- info = "storage-kek"|| ecu_id || generation
```

Design points to implement and to be able to defend:
- **Derivation, not per-key storage.** The KA stores one master key and derives the fleet's keys on
  demand. Storing millions of independent keys is a database problem; deriving them is a key
  management problem with a much smaller compromise surface.
- **`generation` in the derivation info string** is what makes rotation cheap: bump the generation,
  every derived key changes, no re-keying of the master.
- **Device identity keys are generated on the device** and never transmitted. The KA only ever sees
  the public half. Say this in the README -- it is the difference between key provisioning and key
  distribution, and it is a question people ask.

---

## 4. Lifecycle state machine

States and the only legal transitions. Implement in `src/ekl/lifecycle.py` as an explicit table.

```
                  ┌────────────┐
                  │ GENERATED  │  key material exists in the KA only
                  └─────┬──────┘
                        │ stage
                  ┌─────▼──────┐
                  │  STAGED    │  packaged and wrapped for a specific ECU, not yet delivered
                  └─────┬──────┘
        provision-fail  │ provision
              ┌─────────┼─────────┐
              │   ┌─────▼──────┐  │
              └──▶│PROVISIONED │  │  delivered, receipt verified, not yet in service
                  └─────┬──────┘  │
                        │ activate│
                  ┌─────▼──────┐  │
        ┌────────▶│  ACTIVE    │  │  in use for its purpose
        │         └─────┬──────┘  │
        │   rotate      │         │
        │         ┌─────▼──────┐  │
        └─────────│ ROTATING   │  both generations accepted (overlap window)
                  └─────┬──────┘
                        │ cutover
                  ┌─────▼──────┐        ┌───────────┐
                  │  RETIRED   │───────▶│ DESTROYED │  material zeroized, only metadata remains
                  └─────┬──────┘        └───────────┘
                        │                     ▲
                  ┌─────▼──────┐              │
                  │  REVOKED   │──────────────┘  compromise; immediate, out-of-band
                  └────────────┘
```

- `REVOKED` is reachable from **any** state except `DESTROYED`. Compromise does not wait for the
  happy path.
- `DESTROYED` is terminal. Any operation on a destroyed key returns `KEY_DESTROYED`.
- Every transition records: actor, timestamp, reason, prior state, new state, and an operator note.
- Illegal transitions return `IllegalTransition(from, to)` and are logged as a WARN audit event -- an
  attempted illegal transition is itself security-relevant information.

**Cryptoperiod:** each key carries `not_before`, `not_after`, and `max_operations`. A key that
exceeds either is auto-flagged `ROTATION_DUE`. `ekl policy check` reports every key in the fleet
past its cryptoperiod. Base the default cryptoperiods on published NIST SP 800-57 Part 1 guidance
for the key type -- verify the current revision and the actual recommended values by search, and cite
them in `docs/policy-basis.md`.

---

## 5. Provisioning ceremony

`ekl provision --ecu ECU-0042 --purpose secoc-mac --data-id 0x101`

```
KA                                              ECU
 │                                               │
 │──1. challenge (32 random bytes, nonce, TTL)──▶│
 │                                               │  2. sign(challenge || ecu_id || timestamp)
 │◀────3. response + device cert ────────────────│     with device identity key
 │                                               │
 │ 4. verify signature against device cert       │
 │    verify cert chains to OEM key              │
 │    verify nonce unused and not expired        │
 │                                               │
 │ 5. derive key, wrap it: AES-256-GCM under a   │
 │    KEK from ECDH(KA ephemeral, device pub)    │
 │    + HKDF; AAD binds ecu_id, purpose,         │
 │    generation, nonce                          │
 │────6. provisioning package (wrapped key,──────▶│
 │       metadata, OEM signature)                 │  7. verify OEM signature
 │                                                │     verify AAD matches own identity
 │                                                │     unwrap, store in protected storage
 │◀───8. signed receipt (key digest, timestamp)───│
 │                                                │
 │ 9. verify receipt, transition STAGED→PROVISIONED
```

Every numbered step is a separate testable function. The failure of each step has its own reason
code and its own test:

`CHALLENGE_EXPIRED`, `NONCE_REPLAYED`, `DEVICE_SIGNATURE_INVALID`, `CERT_CHAIN_INVALID`,
`ECU_NOT_ENROLLED`, `AAD_MISMATCH`, `UNWRAP_FAILED`, `OEM_SIGNATURE_INVALID`, `RECEIPT_INVALID`,
`KEY_DESTROYED`, `KEY_REVOKED`.

The AAD binding is the important detail: it is what stops a package intended for ECU-0042 from being
accepted by ECU-0043. Test that explicitly -- it is a great whiteboard answer.

---

## 6. Protected storage (ECU side)

`src/ekl/ecu/storage.py`. Models an ECU's secure key store.

- Keys at rest are encrypted with AES-256-GCM under a storage KEK derived from a simulated
  device-unique secret (models a PUF or fused device key).
- The store exposes `use(key_id, operation, data)` -- it performs the operation and returns the
  result. There is **no** `get_key()`. This mirrors an HSM boundary and is the single most important
  API decision in the project.
- Slot metadata: purpose, generation, state, counters (`operations_performed`), install timestamp.
- `zeroize(key_id)` overwrites material and transitions to `DESTROYED`, recording the event.
- Model a constrained device: a fixed slot count (default 16). Provisioning into a full store returns
  `NO_FREE_SLOT` and the CLI suggests which retired key to destroy.

---

## 7. Rotation

`ekl rotate --purpose secoc-mac --overlap-hours 72 [--ecu ECU-0042 | --fleet]`

1. KA bumps `generation`, derives generation N+1 keys.
2. Keys are staged and provisioned to each reachable ECU. Unreachable ECUs are tracked as `PENDING`.
3. Both generation N and N+1 are accepted during the overlap window (`ROTATING` state).
4. At cutover: generation N transitions to `RETIRED`; any ECU still on generation N is reported.
5. `ekl rotate status` shows fleet-wide progress: how many ECUs on which generation, how many pending,
   time remaining in the window.

Model the realistic failure: some ECUs are asleep or out of coverage. `--simulate-offline 20%` makes
a fifth of the fleet unreachable so the demo shows a *partial* rotation and how the system handles
it. That partial state is the interesting engineering problem and most demos skip it.

---

## 8. Revocation

`ekl revoke --key-id K --reason compromise --note "..."`

- Produces a **signed revocation list** (monotonically versioned, signed by the OEM key, with an
  `issued_at` and `next_update`).
- ECUs fetch and verify the list; a stale list past `next_update` is a policy decision the ECU logs
  (fail-open vs fail-closed is configurable and the tradeoff belongs in `docs/decisions.md`).
- A revoked key immediately fails `use()` with `KEY_REVOKED`, even if the ECU has not yet fetched the
  updated list -- and the demo shows the difference between the ECU's local view and the KA's view.
  This gap is the real-world problem: revocation is not instantaneous across a fleet.
- Revocation list rollback is blocked by version number. Test it: replaying an older list must fail.

---

## 9. Audit log

`src/ekl/audit.py`. Append-only, hash-chained, one JSON object per line.

```json
{"seq":42,"ts":"2026-08-19T14:03:11.412Z","actor":"operator:mw","event":"KEY_STATE_CHANGE",
 "key_id":"secoc-mac/ECU-0042/0x101/gen3","from":"ACTIVE","to":"ROTATING","reason":"scheduled",
 "key_digest":"sha256:9f86d0…","prev_hash":"c3d4…","hash":"e5f6…"}
```

- `hash = SHA256(prev_hash || canonical_json(record without hash))`. Canonical JSON: sorted keys,
  no whitespace, UTF-8.
- `ekl audit verify` walks the chain and reports the first divergent sequence number.
- `ekl audit tamper --seq N --field reason --value "..."` mutates a record so detection can be
  demonstrated. It prints a warning that it exists only for demonstration.
- `ekl audit export --format csv|json --since ...` for evidence packaging.
- **Never log key material.** A test scans every emitted line for any byte sequence matching known
  key material and fails if found.

Optional but high-value: sign each audit record, or periodically sign a checkpoint of the chain head,
with an HSM-held audit key -- so tampering is not merely detectable by someone holding the original,
but cryptographically attributable.

---

## 10. CLI surface

```
ekl init                                       # create root + OEM keys, initialize the store
ekl ecu enroll --id ECU-0042 --model BCM       # ECU generates device key, KA issues a cert
ekl ecu list | ekl ecu show ECU-0042
ekl key generate --purpose secoc-mac --data-id 0x101
ekl key list [--state ACTIVE] [--purpose ...] [--expiring-within 30d]
ekl key show <key-id>                          # full lifecycle timeline for one key
ekl provision --ecu ECU-0042 --purpose secoc-mac --data-id 0x101
ekl activate --key-id K
ekl rotate --purpose secoc-mac --overlap-hours 72 [--fleet] [--simulate-offline 20%]
ekl rotate status
ekl revoke --key-id K --reason compromise
ekl crl show | ekl crl publish | ekl crl fetch --ecu ECU-0042
ekl policy check                               # cryptoperiod + rotation-due report
ekl audit verify | tail | tamper | export
ekl use --ecu ECU-0042 --key-id K --op mac --data 0011223344   # exercise a key through the boundary
ekl demo [--scenario all|happy|rotate|revoke|tamper|replay|offline]
ekl serve                                      # optional FastAPI, read-only fleet dashboard
```

---

## 11. Demo scenarios

`ekl demo` narrates these in order.

| # | Scenario | Shows |
|---|----------|-------|
| 1 | `happy` | Enroll 8 ECUs, generate, provision, activate, use a key. Full lifecycle in one screen. |
| 2 | `rotate` | Fleet rotation with a 72-hour overlap and 20% of ECUs offline. Partial state, then completion. |
| 3 | `revoke` | Compromise declared. Signed revocation list published. One ECU has not fetched it yet -- show the divergence, then convergence. |
| 4 | `tamper` | Edit an audit record. `audit verify` names the sequence number. |
| 5 | `replay` | Replay a captured provisioning package at a different ECU. Rejected `AAD_MISMATCH`. Replay at the same ECU. Rejected `NONCE_REPLAYED`. |
| 6 | `downgrade` | Present a retired generation-N key after cutover. Rejected. Publish an older revocation list. Rejected on version. |
| 7 | `expiry` | Advance the injected clock past a cryptoperiod. `policy check` flags it; `use()` refuses. |
| 8 | `full-store` | Provision into an ECU with all 16 slots occupied. `NO_FREE_SLOT`, with the CLI suggesting which retired key to destroy. |

---

## 12. Repository layout

```
ecu-key-lifecycle/
├── README.md  pyproject.toml  Makefile  alembic.ini
├── src/ekl/
│   ├── __init__.py  cli.py  attack.py
│   ├── lifecycle.py        # state machine - NO db imports
│   ├── policy.py           # cryptoperiods, algorithm policy - NO db imports
│   ├── reasons.py          # ReasonCode StrEnum
│   ├── audit.py            # hash-chained log
│   ├── clock.py            # injectable time source
│   ├── authority/  hsm.py  derive.py  provision.py  crl.py  service.py
│   ├── ecu/        device.py  storage.py  agent.py
│   ├── persistence/ models.py  repo.py  migrations/
│   └── render.py
├── tests/
│   ├── test_lifecycle_transitions.py   # every legal AND illegal edge
│   ├── test_provisioning.py            # one test per failure reason code
│   ├── test_rotation_overlap.py        test_revocation.py
│   ├── test_audit_chain.py             test_no_key_material_in_logs.py
│   ├── test_storage_boundary.py        # asserts no get_key() path exists
│   ├── test_cryptoperiod.py            # fake clock
│   └── test_scenarios.py
├── docs/  examples/  .github/workflows/ci.yml
```

---

## 13. Standards mapping for the README

| Implemented | Maps to |
|---|---|
| Full lifecycle state machine, cryptoperiods, rotation, revocation, destruction | NIST SP 800-57 Part 1 (key management recommendation) -- verify current revision |
| Documented key management system design: roles, states, transitions, audit | NIST SP 800-130 (framework for designing cryptographic key management systems) |
| HKDF-SHA256 derivation with domain-separated info strings | NIST SP 800-56C / RFC 5869 |
| AES-256-GCM key wrapping with AAD binding | NIST SP 800-38D |
| Provisioning ceremony, revocation distribution, evidence retention | ISO/SAE 21434 (cite by name unless you verify the clause) |
| Rotation and revocation as part of software update integrity | UN ECE R156 (software update management systems) |
| ECU-side non-exportable storage boundary | EVITA HSM profiles, SAE J3101, AUTOSAR Key Manager (KeyM) / CSM concepts |

Write `docs/standards-references.md` with one paragraph per row: what the document actually asks for,
and which function here satisfies it. Verify every document number and revision by search first.

---

## 14. Explicit non-goals and honesty requirements

- README states plainly that this is a simulation of a key management system, not a KMS, and that
  the simulated HSM provides no hardware guarantees.
- Do not claim PKCS#11, real HSM, or production KMS experience.
- Demo keys and generated material live under a gitignored `state/` directory, never committed.
