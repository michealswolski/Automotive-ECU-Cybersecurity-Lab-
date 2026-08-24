# BUILD_PLAN - phase order

This kit has the steepest setup cost (a cross-toolchain and an emulator) and the highest payoff for
the C/C++ and RTOS claims. Do not skip Phase 1 -- if the firmware does not boot, nothing else lands.

## Phase 0 - Toolchain and emulator
Verify and document the working combination: `arm-none-eabi-gcc`, CMake, and QEMU (or Renode) for the
chosen Cortex-M target. Write `docs/toolchain.md` with exact versions and the working invocation,
including macOS and Linux differences.
**Accept:** a hello-world bare-metal binary builds and prints over semihosting in the emulator.
Do not proceed until this works.

## Phase 1 - FreeRTOS boots
Kernel + port for the target, the five tasks from SPEC §1 as stubs, a working tick, and the
memory-mapped CAN peripheral stub.
**Accept:** `make run` boots FreeRTOS in the emulator, all five tasks run, and task output appears on
the console. Screenshot this -- it goes in the README.

## Phase 2 - ISO-TP and UDS, clean
Write both parsers **correctly first**, in the shared source tree that both the firmware and host
builds compile. Unit tests for correct behavior.
**Accept:** a multi-frame ISO-TP exchange and a full UDS session work in the emulator, driven from
the host harness through the CAN stub.

## Phase 3 - Plant the vulnerabilities
Introduce all eight from SPEC §2 into a `vulnerable` build configuration, keeping the `hardened`
build correct. Write `docs/vulns/VULN-nnn.md` for each **at the same time as the code** -- if you
defer the documentation you will not remember your own reasoning.
**Accept:** each vulnerability is reachable from the CAN interface; you can write the input that
triggers it by hand for at least four of them.

## Phase 4 - Static analysis
cppcheck, clang-tidy, flawfinder, compiler warnings. Normalized finding records, deduplicated across
tools.
**Accept:** the normalized output identifies which tool found which vulnerability; false positives
are counted and reported, not hidden.

## Phase 5 - Dynamic analysis
ASan, UBSan, MSan host builds and the corpus replay harness.
**Accept:** every sanitizer trap maps back to a `VULN-nnn`; VULN-005 (use-after-free) is caught by
ASan and confirmed missed by the static tools.

## Phase 6 - Fuzzing
libFuzzer harnesses over the shared parser sources, seed corpus, dictionary, coverage reporting,
crash triage, crashing inputs committed as regression tests.
**Accept:** the fuzzer independently finds at least three planted vulnerabilities; time-to-first-crash
is recorded for each; `make fuzz` in CI passes on the hardened build.

## Phase 7 - Supply chain
syft SBOM in CycloneDX, grype and/or osv-scanner, one deliberately outdated vendored component,
documented.
**Accept:** the scan produces a real, explained finding; the SBOM lists actual component versions.

## Phase 8 - Traceability and reporting
`docs/requirements.md` (security requirements — reuse the TARA project's REQ IDs if you have them),
test header blocks, `make trace`, and the consolidated HTML/markdown report with the tool-comparison
matrix.
**Accept:** `make trace` reports zero unverified requirements and zero orphan tests; the report opens
standalone and the tool-comparison matrix is complete including the misses.

## Phase 9 - CI and documentation
CI runs `make check` on both build configurations and fails on a regression in the hardened build.
- `README.md`: what it is, the emulator screenshot, the eight vulnerabilities in a table, the
  tool-comparison matrix inline, the fuzzing numbers, and the disclaimers.
- `docs/tool-comparison.md`: the analysis, including what each tool missed and why.
- `docs/method.md`: how the pipeline works and what each stage is actually good at.
- `docs/bench-notes.md`: how you would run this same validation against real hardware, and what would
  change. (See `bench-path.md` in the kit bundle.)
**Accept:** a reader can tell, from the README alone, which classes of bug need runtime tooling and
which static analysis catches.

## Phase 10 (optional, high value)
1. **Renode instead of QEMU** if you want a scriptable peripheral model and automated hardware-in-
   emulator tests. Renode's test framework is genuinely closer to how bench validation works.
2. Wire the flash path to the secure boot project: `TransferData` delivers an image, and the secure
   boot verifier accepts or rejects it. Two repos, one attack chain.
3. Add a GDB debugging walkthrough (`docs/debugging.md`) using the emulator's gdbstub -- breakpoints,
   memory inspection, catching the overflow live. This is the closest software equivalent to the JTAG
   experience, and it is honest as long as you call it what it is.
