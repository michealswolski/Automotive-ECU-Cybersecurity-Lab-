# Paste this into Claude Code from the repo root

```
Read CLAUDE.md, SPEC.md, BUILD_PLAN.md, and ACCEPTANCE.md in full before writing any code.

Then:
1. Web-search and report: current QEMU support for Cortex-M targets vs Renode for this use case,
   the current FreeRTOS LTS version and its port structure, current invocations for cppcheck /
   clang-tidy / flawfinder, the current recommended SBOM + CVE scanner pairing (syft/grype/
   osv-scanner, CycloneDX vs SPDX), and whether clang-tidy's CERT checks cover what I need.
   Tell me what you verified and what you couldn't.
2. Recommend the target board and emulator, with your reasoning. I want your opinion, not a
   menu -- but tell me the tradeoff you're making.
3. Do Phase 0 and stop. I want to see a bare-metal hello-world print over semihosting before we
   build anything on top of it. If the toolchain fights us, we solve that first.

What matters most:
- The parsers must compile from one source for both target and host. If the fuzzer tests
  different code than the firmware runs, the project is worthless.
- Vulnerabilities get documented as they're written, not after.
- Report what the tools MISS. That matrix is the most valuable thing in the repo.
- No MISRA compliance claims.
```

## Follow-up prompts worth having ready

- `Phase 1: get FreeRTOS booting with all five tasks. Show me the console output.`
- `Phase 3: plant the eight vulnerabilities. For each, write the doc first -- CWE, exact trigger, what an attacker gains, why a real developer might plausibly write this -- then the code. Then hand me the raw bytes that trigger four of them so I can verify by hand.`
- `Phase 6: run the fuzzer for ten minutes per harness and give me the real numbers -- executions, coverage, unique crashes, and time-to-first-crash per vulnerability. Then tell me which planted bugs it did NOT find and why.`
- `Build the tool-comparison matrix and be brutal about it. Which tools produced findings that were pure noise? What was the false-positive rate on flawfinder? Which vulnerability did nothing catch?`
- `Write docs/debugging.md: a GDB walkthrough over the emulator's gdbstub that catches VULN-001 live -- breakpoint, inspect the stack, watch the overflow happen. Be explicit that this is emulator-based debugging, not JTAG on hardware.`
- `Review this as an embedded security engineer at a tier-1. What's naive about my firmware? What would a real ECU do differently in the ISO-TP layer? Write it to docs/gaps.md.`
