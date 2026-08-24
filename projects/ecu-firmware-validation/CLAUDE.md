# CLAUDE.md - ECU Firmware Security Validation Pipeline

> **Read [`CORRECTIONS.md`](./CORRECTIONS.md) before writing any code.** Several
> standards anchors in this file and in `SPEC.md` have moved since they were
> written — AUTOSAR release, UDS security services, the post-quantum firmware
> signing story, tool maintenance status. The corrections file is authoritative
> where it disagrees with the text below. Editions to cite are in
> [`docs/standards-register.md`](../../docs/standards-register.md).

You are building this project from scratch. Read `SPEC.md` and `BUILD_PLAN.md` first.

## What this is

Real embedded C firmware -- a FreeRTOS application running on an emulated ARM Cortex-M, implementing
a UDS diagnostic server over a simulated CAN transport -- that contains **deliberately planted,
documented vulnerabilities**, wrapped in a security validation pipeline that finds them: static
analysis, compiler sanitizers, coverage-guided fuzzing, SBOM generation, CVE scanning, and a
documented test suite traced to requirements.

The story it tells: *here is embedded C, here are the classes of bug that get shipped in it, here is
the tooling that catches each class, and here is what each tool missed.* That last part is the
valuable one. Anyone can run cppcheck. Knowing which bug clang-tidy caught, which one only ASan
caught at runtime, and which one only the fuzzer found after 40,000 executions is what an interviewer
is actually probing for.

## Non-negotiables

1. **Real C, really compiled, really running.** FreeRTOS on QEMU (or Renode) emulating a Cortex-M
   target. Not a Linux process pretending to be firmware.
2. **Vulnerabilities are planted deliberately and documented.** Each lives in `docs/vulns/VULN-nnn.md`
   with the CWE, the exact source line, the class of bug, which tool finds it, and the fix. There is
   a `vulnerable` build and a `hardened` build, and the pipeline runs against both.
3. **Report what the tools miss.** `docs/tool-comparison.md` is a matrix: vulnerability by tool,
   found or missed, with the time-to-find for the fuzzer. A tool that missed something is a finding,
   not an embarrassment.
4. **Every test traces to a requirement.** Test IDs map to security requirements; if the TARA project
   exists, map them to its requirement IDs. This is what "documented test cases" means to an
   automotive employer and it is the part most portfolios skip.
5. **The pipeline runs in CI on every push** and fails the build on a regression in the hardened
   configuration.
6. **Do not plant a vulnerability you cannot explain.** For each one you must be able to say, out
   loud, how it is reached, what an attacker gains, and why a real developer would plausibly have
   written it.

## Verify before coding

Web-search rather than recall:
- Current QEMU support for the target board and whether Renode is the better fit for the peripheral
  set you need. Verify the exact invocation before building around it.
- Current FreeRTOS LTS version and the demo/port structure for the chosen Cortex-M target.
- Current invocation and flags for `cppcheck`, `clang-tidy`, `flawfinder`, and the sanitizers.
- Current SBOM tooling: `syft` for generation, `grype` and `osv-scanner` for scanning, CycloneDX vs
  SPDX. Confirm what the current recommended pairing is before wiring the pipeline.
- Whether `clang-tidy` MISRA-adjacent checks come from the CERT-C check set or need a plugin.
  Do not claim MISRA compliance -- MISRA is a paid standard and full checking needs a commercial tool.
  Claim CERT-C-oriented static analysis, which is what the open tooling actually gives you.

## Engineering standards

- C11, `-Wall -Wextra -Werror`, CMake. Host-side test and fuzz harnesses build natively; the firmware
  builds for the target.
- Python 3.12+ for the pipeline orchestration and reporting.
- The parsers under test must be compilable **both** for the target and for the host, so the same
  code that runs in firmware is the code the fuzzer exercises. If the fuzzer tests a different
  implementation than the firmware runs, the whole project is theater.
