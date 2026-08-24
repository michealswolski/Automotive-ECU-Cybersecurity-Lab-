# ACCEPTANCE - the definition of done

## Hard gates
- [ ] `make firmware` cross-compiles clean with `-Wall -Wextra -Werror`.
- [ ] `make run` boots FreeRTOS in the emulator and all five tasks produce output.
- [ ] `make check` green on the hardened build and runs in CI on every push.
- [ ] `docs/toolchain.md` lets someone else reproduce the build on a clean machine.

## Firmware gates
- [ ] The parsers under test compile from the **same source** for both the target and the host. The
      fuzzer exercises the code the firmware runs.
- [ ] A multi-frame ISO-TP exchange and a full UDS session work end to end through the CAN stub.
- [ ] All eight vulnerabilities are reachable from the CAN interface in the vulnerable build.
- [ ] Each has a `docs/vulns/VULN-nnn.md` with CWE, location, trigger, impact, and fix.

## Tooling gates
- [ ] Static analysis output is normalized across tools and deduplicated by (file, line, CWE).
- [ ] False positives are counted and reported, not suppressed silently.
- [ ] ASan catches VULN-005; the static tools are documented as missing it.
- [ ] The fuzzer independently finds at least three vulnerabilities, with time-to-first-crash recorded.
- [ ] Crashing inputs are committed as regression tests and rerun in CI.
- [ ] Coverage over the parsers is measured and the real number reported.
- [ ] The SBOM lists actual component versions; the CVE scan produces at least one explained finding.

## Traceability gates
- [ ] Every test carries a header block naming its requirement, the vulnerability it verifies, the
      method, and the pass criteria.
- [ ] `make trace` reports zero unverified requirements and zero orphan tests.

## Honesty gates
- [ ] The tool-comparison matrix includes the misses, and VULN-007 is documented as caught by review
      rather than by tooling.
- [ ] No MISRA compliance claim anywhere. CERT-C-oriented analysis is what is claimed.
- [ ] The vulnerable build is clearly labeled as deliberate.
- [ ] The emulation disclaimer names what is not modeled: peripheral timing, transceiver, electrical layer.
- [ ] The deliberately outdated vendored component is explained.
