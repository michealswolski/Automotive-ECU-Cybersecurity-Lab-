# Capability coverage

Which project demonstrates what. Generated from `lab.toml` — see [tooling](./tooling.md).

`●` means the project's specification and acceptance criteria cover that capability. `·` means it does not.

Project numbers: `01` Secure Boot · `02` SecOC · `03` Key Lifecycle · `04` TARA · `05` IVN Lab · `06` Firmware Validation.

<!-- labctl:begin coverage-matrix -->

**Embedded trust**

| Capability | `01` | `02` | `03` | `04` | `05` | `06` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Secure boot | ● | · | · | · | · | · |
| Chain of trust | ● | · | · | · | · | · |
| HSM / root of trust | ● | · | · | · | · | · |
| Anti-rollback | ● | · | · | · | · | · |
| Measured boot / attestation | ● | · | · | · | · | · |

**Cryptography**

| Capability | `01` | `02` | `03` | `04` | `05` | `06` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| PKI | ● | · | ● | · | · | · |
| ECDSA / Ed25519 | ● | · | · | · | · | · |
| AES | · | ● | · | · | · | · |
| CMAC / HMAC | · | ● | · | · | · | · |
| Key management | · | · | ● | · | · | · |
| Key derivation (HKDF) | · | · | ● | · | · | · |
| Provisioning ceremony | · | · | ● | · | · | · |
| Key rotation | · | · | ● | · | · | · |
| Revocation | · | · | ● | · | · | · |
| Cryptoperiods | · | · | ● | · | · | · |
| Tamper-evident audit logs | ● | · | ● | · | · | · |

**Automotive networking**

| Capability | `01` | `02` | `03` | `04` | `05` | `06` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| CAN bus | · | ● | · | · | · | · |
| CAN-FD | · | · | · | · | ● | · |
| LIN | · | · | · | · | ● | · |
| Automotive Ethernet | · | · | · | · | ● | · |
| SOME/IP + SD | · | · | · | · | ● | · |
| DoIP | · | · | · | · | ● | · |
| UDS diagnostics | · | · | · | · | ● | ● |
| ISO-TP | · | · | · | · | ● | ● |
| AUTOSAR SecOC | · | ● | · | · | · | · |
| Replay protection | · | ● | · | · | · | · |
| Freshness management | · | ● | · | · | · | · |
| Zone-based segmentation | · | · | · | · | ● | · |
| Anomaly detection | · | · | · | · | ● | · |

**Product security lifecycle**

| Capability | `01` | `02` | `03` | `04` | `05` | `06` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| ISO/SAE 21434 | · | · | · | ● | · | · |
| TARA | · | · | · | ● | · | · |
| Threat modelling | · | · | · | ● | · | · |
| Attack feasibility rating | · | · | · | ● | · | · |
| Risk determination | · | · | · | ● | · | · |
| Cybersecurity requirements | · | · | · | ● | · | · |
| Requirement traceability | · | · | · | ● | · | · |
| UN R155 evidence | · | · | · | ● | · | · |
| Documented test cases | · | · | · | · | · | ● |

**Firmware engineering**

| Capability | `01` | `02` | `03` | `04` | `05` | `06` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Embedded C | · | · | · | · | · | ● |
| RTOS (FreeRTOS) | · | · | · | · | · | ● |
| Static analysis | · | · | · | · | · | ● |
| Sanitizers | · | · | · | · | · | ● |
| Coverage-guided fuzzing | · | · | · | · | · | ● |
| SBOM generation | · | · | · | · | · | ● |
| CVE scanning | · | · | · | · | · | ● |

<!-- labctl:end coverage-matrix -->

---

## Deliberately not claimed

Five capabilities require hardware. No simulation makes them true, so nothing here claims them.

<!-- labctl:begin bench-gaps -->

| Capability | Claimed here? |
|---|---|
| Logic analyzer | No — requires hardware |
| JTAG / SWD on-target debugging | No — requires hardware |
| Oscilloscope | No — requires hardware |
| Vector CANoe | No — requires hardware |
| Physical CAN bus / transceivers | No — requires hardware |

<!-- labctl:end bench-gaps -->

This is enforced rather than stated. Each of these carries `bench_only = true` in `lab.toml`, and `labctl validate` fails the build if any project's capability list claims one. What it costs to close each gap honestly is in [the bench path](./bench-path.md).

---

## How to read this

**A single `●` in a row is not a weakness.** Depth beats breadth here — one project that implements freshness management properly, with a receiver that reconstructs the full value from truncated bits and searches a bounded window, is worth more than five projects that each mention it.

**A row with no `●` should not exist.** `labctl validate` reports any capability declared in the manifest that no project covers, so the matrix cannot quietly accumulate aspirational rows.

**The columns are not equal.** Project `06` covers seven firmware-engineering capabilities because it is the only project with compiled C in it, and it is also the most expensive project by a wide margin. Coverage count is not a proxy for effort or for value — see [build order](./build-order.md) for what each one actually costs.
