# SPEC - ECU Firmware Security Validation Pipeline

Version 1.0. Source of truth.

---

## 1. The firmware under test

`firmware/` — a FreeRTOS application for an emulated ARM Cortex-M target.

Tasks:
| Task | Priority | Responsibility |
|---|---|---|
| `can_rx_task` | high | Receives frames from the simulated CAN peripheral, feeds the ISO-TP reassembler |
| `uds_task` | medium | Parses reassembled diagnostic requests, dispatches UDS services |
| `flash_task` | medium | Handles the RequestDownload/TransferData sequence into a staging buffer |
| `telemetry_task` | low | Formats and emits periodic status strings |
| `watchdog_task` | highest | Monitors task liveness |

The CAN peripheral is a memory-mapped stub the host harness can drive, so frames can be injected from
outside the emulator.

The attack surface is the ISO-TP reassembler and the UDS parser. That is deliberate: it is the
realistic attack surface of a real ECU, and it is a byte-oriented parser, which is exactly what
fuzzers are good at.

---

## 2. Planted vulnerabilities

Minimum eight, spanning classes that different tools catch. Each documented in `docs/vulns/`.

| ID | Class | CWE | Where | Expected finder |
|---|---|---|---|---|
| `VULN-001` | Stack buffer overflow — `memcpy` with attacker-controlled length into a fixed buffer | CWE-121 | ISO-TP reassembly | clang-tidy / cppcheck (static), ASan (runtime) |
| `VULN-002` | Off-by-one on an array index bound (`<=` instead of `<`) | CWE-193 | UDS DID lookup table | ASan; static analysis may miss it |
| `VULN-003` | Integer overflow in a length calculation leading to an undersized allocation | CWE-190 | TransferData sizing | UBSan; fuzzer reaches it |
| `VULN-004` | Format string — attacker-controlled data passed to a `printf`-family function | CWE-134 | telemetry task | flawfinder / compiler `-Wformat-security` |
| `VULN-005` | Use-after-free — buffer released on an error path, then used | CWE-416 | ISO-TP error handling | ASan only; static analysis misses it |
| `VULN-006` | Missing bounds check on a service identifier before a jump-table index | CWE-129 | UDS dispatch | fuzzer + ASan |
| `VULN-007` | Time-of-check/time-of-use on a security-access state flag across tasks | CWE-367 | UDS SecurityAccess | none of the above reliably — this one is found by review, and that is the point |
| `VULN-008` | Hardcoded seed/key constant | CWE-798 | SecurityAccess | secret-scanning / grep-class tooling, plus review |

`VULN-007` earns its place by being the one the tools do not catch. Say so in the report. Being able
to name the limits of your tooling is worth more in an interview than a clean scan.

Optional additions if you want more depth: an uninitialized-read (CWE-457, MSan), a null-deref on an
unchecked return (CWE-476), and a stack-exhaustion path via unbounded recursion (CWE-674, and
relevant to RTOS stack sizing).

---

## 3. The pipeline

`pipeline/` — Python orchestration producing a single consolidated report.

### 3.1 Static analysis
- `cppcheck` with the full check set, plus its CERT-oriented addons.
- `clang-tidy` with a curated check list: `bugprone-*`, `cert-*`, `clang-analyzer-*`,
  `readability-*` where it aids review.
- `flawfinder` as the fast lexical first pass, with its false-positive rate reported honestly.
- Compiler warnings as a tool in their own right: `-Wall -Wextra -Wconversion -Wformat-security`,
  and note which vulnerabilities the compiler alone catches. People forget this is free.

Normalize every tool's output into a common finding record: tool, rule ID, CWE, file, line, severity,
message. Deduplicate across tools by (file, line, CWE) and report which tools agreed.

### 3.2 Dynamic analysis
- Host build with ASan, UBSan, and MSan (separate builds — ASan and MSan do not combine).
- A replay harness that drives the recorded test corpus through the parsers under each sanitizer.
- Report every sanitizer trap with its stack trace, mapped back to a `VULN-nnn`.

### 3.3 Fuzzing
- libFuzzer harnesses (`fuzz/fuzz_isotp.c`, `fuzz/fuzz_uds.c`) over the **same parser source** the
  firmware compiles.
- A seed corpus of valid ISO-TP and UDS exchanges, plus a dictionary of service identifiers and
  frame type codes — a fuzzer with a good dictionary finds structured-protocol bugs orders of
  magnitude faster, and knowing that is a real skill signal.
- CI runs a short time-boxed fuzz (60s per harness) for regression; a `make fuzz-long` target runs
  longer locally.
- Record and report: executions, coverage reached, unique crashes, and **time-to-first-crash per
  vulnerability**. Commit the crashing inputs as regression tests.
- Structural coverage report (`llvm-cov`) over the parsers, with the honest number.

### 3.4 Supply chain
- `syft` generating a CycloneDX SBOM of the firmware's third-party components (FreeRTOS kernel and
  any vendored libraries), with versions.
- `grype` and/or `osv-scanner` against the SBOM.
- Deliberately vendor one **outdated** third-party component so the scan produces a real finding
  rather than an empty report. Document the choice; do not vendor anything with a live critical
  vulnerability you would be embarrassed to have in a public repo — pick something with a known,
  patched, low-severity issue and say why you chose it.

### 3.5 Consolidated report
`make report` produces `out/report.html` and `out/report.md`:
- Findings by tool, by CWE, by severity.
- **The tool-comparison matrix**: every planted vulnerability against every tool, found or missed.
- Fuzzing statistics with time-to-crash.
- SBOM and CVE summary.
- Requirements traceability: which test verifies which security requirement.
- A vulnerable-vs-hardened diff showing the findings that disappear after the fixes.

---

## 4. Test suite and traceability

`tests/` — host-buildable unit and integration tests (Unity or a minimal custom harness; verify the
current recommended option for embedded C before choosing).

Every test carries a header block:

```c
/* TEST-014
 * Requirement: REQ-SEC-007 - The ISO-TP reassembler shall reject any first frame
 *              declaring a total length greater than the reassembly buffer size.
 * Verifies:    VULN-001
 * Method:      Boundary value analysis
 * Criteria:    Reassembler returns ISOTP_ERR_LENGTH; no write past buffer end (ASan clean).
 */
```

`pipeline/traceability.py` extracts these into a matrix. `make trace` prints requirements with no
verifying test, and tests verifying no requirement. If you built the TARA project, use its `REQ-nnn`
IDs directly — a firmware test suite that traces back to a threat analysis is a genuinely strong
combination and almost nobody at entry level has it.

---

## 5. Repository layout

```
ecu-firmware-validation/
├── README.md  Makefile  CMakeLists.txt
├── firmware/
│   ├── src/  main.c  can_hal.c  isotp.c  uds.c  flash.c  telemetry.c
│   ├── include/
│   ├── freertos/          # kernel + port for the chosen target
│   └── cmake/toolchain-arm-none-eabi.cmake
├── host/                   # same parser sources, host build, for tests and fuzzing
├── fuzz/  fuzz_isotp.c  fuzz_uds.c  corpus/  dict/
├── tests/  test_isotp.c  test_uds.c  test_flash.c
├── pipeline/  static_analysis.py  dynamic.py  fuzzing.py  sbom.py  traceability.py  report.py
├── docs/
│   ├── vulns/VULN-001.md … VULN-008.md
│   ├── tool-comparison.md  requirements.md  method.md  bench-notes.md
├── out/  .github/workflows/ci.yml
```

---

## 6. CLI / Make targets

```
make firmware            # build for the target
make run                 # boot the firmware in QEMU/Renode, semihosting output to console
make host                # host build of the shared parser sources
make test                # unit + integration tests
make asan | ubsan | msan # sanitizer builds and corpus replay
make fuzz                # 60s per harness
make fuzz-long TIME=600
make static              # cppcheck + clang-tidy + flawfinder, normalized output
make sbom                # syft + grype
make trace               # requirements traceability matrix
make report              # consolidated HTML + markdown
make check               # everything CI runs
```

`make run` must actually boot the firmware and print output. A reviewer who can watch FreeRTOS come
up in an emulator believes the rest of the repo.

---

## 7. Honesty requirements

- The vulnerable build is clearly labeled and its purpose stated. Never let a reader wonder whether
  the bugs were accidental.
- Do not claim MISRA compliance. Claim CERT-C-oriented static analysis with open tooling and say why
  full MISRA checking requires a commercial tool.
- Report false positives and tool misses. The tool-comparison matrix is the most credible artifact in
  the repo precisely because it admits gaps.
- The emulated target is emulated. Say what that means: no real peripheral timing, no real
  transceiver, no electrical layer.
- If you vendor an outdated component to make the CVE scan meaningful, say that you did it on
  purpose and why you chose that one.
