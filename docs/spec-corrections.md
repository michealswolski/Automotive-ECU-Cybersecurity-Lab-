# Spec corrections

The six specifications were written against the standards landscape as it stood when they were drafted. Several of those anchors have moved. This page is the delta: what each project must change before or during its build, and why.

Each project also carries its own copy as `CORRECTIONS.md`, and its `CLAUDE.md` points at it — so the corrections reach the build rather than sitting in a document nobody opens.

> **On provenance.** These corrections originate in a 2026 technical validation of the six specs. The load-bearing claims were re-verified against primary and reputable secondary sources on 2026-08-24 before being recorded here; the [standards register](./standards-register.md) marks each row `web` or `report` accordingly. **One correction in the report was itself out of date** — see AUTOSAR below. Treat this page the same way: a snapshot with a date on it, not a permanent truth.

---

## The five that matter most

If nothing else gets fixed, fix these. They are the details an interviewer probes, and each one is checkable in seconds by someone who works in the field.

| # | Was | Is |
|---|---|---|
| 1 | ML-DSA as the post-quantum firmware-signing root | **CNSA 2.0 names LMS or XMSS** (stateful hash-based, NIST SP 800-208) for firmware and software signing. ML-DSA-87 is for general signatures. |
| 2 | UDS security access is 0x27 seed/key | **ISO 14229-1:2020 added service 0x29 Authentication**, and ISO 15765-4 deprecates 0x27 for new designs. Brute-forcing 0x27 is still a valid attack — but 0x29 must appear as the remediation. |
| 3 | AUTOSAR R20-11 / R21-11 | **R25-11**, released December 2025. |
| 4 | SBOM required by UN R155 / ISO/SAE 21434 | **Neither mandates an SBOM.** The EU Cyber Resilience Act does, and it is the first binding SBOM mandate in law. |
| 5 | SAE J3101 is in development | **Published February 2020** as J3101_202002. |

---

## `01` Secure Boot Chain Simulator

**Correct**

- CNSA 2.0 specifies **LMS or XMSS** for firmware and software signing — not ML-DSA. Timeline: support and prefer by 2025, exclusive use by 2030. Do not describe ML-DSA-65 as a "CNSA-2.0-compliant firmware signing root"; frame it as a **PQC-ready demonstration of FIPS 204**.
- **SAE J3101 is published** (J3101_202002, February 2020), not a draft. It is requirements-oriented — a hardware protected security environment acting as a gatekeeper for system data and control access — not implementation-prescriptive.
- **FIPS 203, 204 and 205 were finalized in August 2024.** None is a draft. FIPS 206 (FN-DSA) is expected later, and NSA has said it will not be added to CNSA.
- **NIST SP 800-193 is current** (May 2017). The withdrawn item that surfaces in searches is the initial public draft, not the final. Principles: Protection, Detection, Recovery, founded on roots of trust.
- **Python `cryptography` now exposes ML-DSA** — added in 47.0.0 via `cryptography.hazmat.primitives.asymmetric.mldsa`, with broader backend support in 48. Pin accordingly, and note the caveat: post-quantum support needs an AWS-LC or BoringSSL backend, and most published wheels ship OpenSSL. Probe for it and gate the feature. SLH-DSA is not yet exposed.

**Add**

- Model the **advance-SVN-before versus after-confirmed-healthy-boot tradeoff explicitly.** Best practice is to advance the monotonic counter only after a boot is confirmed healthy, because advancing before confirmation can brick a device with no path back to the known-good lower SVN. This is exactly the nuance that reads as senior.
- Model real monotonic-counter substrates: OTP/eFuse-backed counters and secured-flash monotonic counters. Reference real HSM-bearing silicon families rather than an abstract "HSM".
- Add classic secure-boot attacks as test cases: voltage and clock glitching of the verify-compare, TOCTOU between verify and load, signature stripping, and stage confusion. These map to published research.
- Consider **SHA-384** as the hash default to align with CNSA 2.0 posture. SHA-256 is fine; SHA-384/512 is the quantum-era hedge.

**Soften**

- Do not claim ML-DSA-65 is CNSA 2.0 compliant for firmware signing.
- Soften "measured boot = TPM PCR" for automotive. Most automotive HSMs are SHE/EVITA-style, not TPMs. TCG PCR-extend and SP 800-155 are the conceptual model being *emulated*, and there is no single dominant automotive attestation standard yet — say so.

---

## `02` CAN Bus SecOC Demo

**Correct**

- **AUTOSAR is at R25-11**, released December 2025. The validation report names R24-11 as current; that was correct when the report's sources were gathered and is not correct now. R24-11 is the prior release.
- The **three profiles are still the only standard profiles** — no new numbered profile was added for CAN FD or Ethernet, because SecOC is transport-agnostic. State this explicitly rather than leaving it ambiguous.
- `DataToAuthenticator` construction is confirmed exact: **Data Identifier (SecOCDataId, 16-bit) ‖ secured part of the Authentic I-PDU ‖ Complete Freshness Value**, in that order, big-endian throughout. The *complete* FV is used in the MAC computation even when only a truncated FV is transmitted.
- `SecOCFreshnessValueVerificationAttempts` is a real configuration parameter — the maximum number of verification retries against candidate freshness values before rejecting. Verify the literal parameter string against the AUTOSAR SWS ECUC parameter table before quoting it.
- python-can: `bustype=` is deprecated in favour of `interface=` and is slated for removal in 5.0. The existing spec already says this — keep it.

**Add**

- Cite the **Toyota RAV4 Prime SecOC key-extraction research** (Willem Melching / icanhack.nl, March 2024). The EPS ECU's debug port was locked, so voltage fault injection was used to extract the firmware; the bootloader was then reverse-engineered and the keys dumped from RAM — because that ECU did not use its HSM to hide keys. Newer vehicles do, and extracting keys from those is described as an unsolved problem. This is the perfect real-world limitation to model: **SecOC's security collapses if the key is recoverable from a single compromised ECU.**
- Discuss SecOC's known limitations plainly: it authenticates but does not encrypt; a truncated 24-bit MAC trades bandwidth for a smaller forgery margin; freshness synchronisation is fragile; and it inherits a key-management and HSM dependency.
- Position Scapy alongside python-can — python-can for the bus, Scapy's automotive layers for protocol dissection and attack tooling.

**Soften**

- Do not imply SecOC provides confidentiality. It provides authenticity and freshness only.
- Do not claim the profile set is exhaustive of "all SecOC". OEMs frequently use custom or adapted freshness schemes; frame these as the AUTOSAR-standard profiles.

---

## `03` ECU Key Lifecycle Manager

**Correct**

- **NIST SP 800-57 Part 1 Revision 5 (May 2020) is the current published version.** An initial public draft of Revision 6 was published 5 December 2025 with comments through 5 February 2026, adding the FIPS 203/204/205 algorithms and Ascon. Cite Rev 5 as authoritative and mention Rev 6 — that combination shows currency without overclaiming.
- Use the real cryptoperiod figures from Rev 5, Table 1: symmetric data-encryption, authentication and key-wrapping keys — originator-usage period ≤ 2 years, recipient-usage ≤ OUP + 3 years; symmetric master or key-derivation key ~1 year; symmetric key-agreement 1–2 years.
- **SP 800-130 remains final** and is the right CKMS design framework to reference. SP 800-152 is also final but is US-federal-specific — do not overstate its applicability.
- AUTOSAR **CSM** provides the standardised crypto service interface; **KeyM** handles key and certificate management including X.509. These are the AUTOSAR-native counterparts to this CLI — they define interfaces and services, not a lifecycle policy, which is the layer this project adds.

**Add**

- Tie the revocation and rollback-protection story to **UN R156**, which requires manufacturers to ensure the integrity and authenticity of software updates and to manage software identification (RxSWIN).
- Compare against **V2X SCMS / IEEE 1609.2** for fleet revocation at scale. The lesson that transfers: in-vehicle revocation propagation is hard because vehicles are intermittently connected, so revocation lists must be offline-tolerant, signed and rollback-protected — which this design already does.
- Reference **RFC 9162** (Certificate Transparency v2, Merkle-tree logs) as the model for the tamper-evident log, and consider a Merkle-tree option for efficient inclusion proofs.
- Name **line-end programming / key injection at manufacture / secure-element personalisation** as the real provisioning context, and mention the **SHE memory-update protocol** (KDF-derived K1/K2 with CMAC) as the canonical symmetric key-injection ceremony being emulated.

**Soften**

- Do not claim the tool "implements AUTOSAR KeyM/CSM" — say it is *modelled on* them.
- Do not imply NIST cryptoperiods are mandatory for automotive. They are guidance; OEMs tune them.

---

## `04` ISO/SAE 21434 TARA Workbench

**Correct**

- **ISO/SAE 21434:2021 is still the current edition.** It entered ISO systematic review in July 2026, and a second edition is expected to start development on a roughly three-year timeline. Say review has begun; do not imply a revision exists.
- **CAL is informative, not normative, in 21434:2021** (Annex E). The workbench should treat it as optional.
- **ISO/SAE 8475 (CAL and TAF)** is at final approval as a PAS and publication is expected imminently. It makes CAL prescriptive and redefines the levels as **Basic / Intermediate / Advanced**, replacing the informative CAL1–CAL4. Supporting it is a genuine forward-looking differentiator.
- **Attack feasibility has three approaches in Clause 15**, not one: attack-potential-based, CVSS-based, and attack-vector-based. Support all three, or at minimum name them.

**Add**

- Reference the alternative TARA methods so a reader knows the method was chosen rather than assumed: HEAVENS and HEAVENS 2.0, EVITA (severity × attack probability), SAHARA (safety + security), and ETSI TVRA. HEAVENS 2.0 and attack-potential are the most common in ISO 21434 practice.
- Add **TAF (Targeted Attack Feasibility)** as a design-target attribute distinct from descriptive attack feasibility.
- Know the competitive landscape: commercial tools are itemis SECURE, ThreatGet and Ansys medini analyze; open tools are Microsoft Threat Modeling Tool, OWASP Threat Dragon, pytm, threagile, OVVL and taralizer. Most open tools are generic STRIDE/DFD threat modelling — **very few do a full ISO/SAE 21434 TARA with attack-potential feasibility, S-F-O-P impact and 1–5 risk determination.** That gap is precisely where this project's value sits.

**Soften**

- Do not present CAL as normative or required — it is informative in 21434 and only becomes prescriptive under ISO/SAE 8475.
- The standard is paywalled. Cite public secondary sources for the tables rather than reproducing copyrighted matrices, and note the paywall explicitly.

---

## `05` In-Vehicle Network Security Lab

**Correct**

- **LIN protected identifier parity**, confirmed: `P0 = ID0 ⊕ ID1 ⊕ ID2 ⊕ ID4` (even parity); `P1 = ¬(ID1 ⊕ ID3 ⊕ ID4 ⊕ ID5)` (odd parity). PID is the 6-bit frame ID in bits 0–5, P0 in bit 6, P1 in bit 7. Classic checksum covers data bytes only (LIN 1.x); enhanced covers PID plus data (LIN 2.x); frame IDs 0x3C–0x3D always use classic.
- **CAN FD DLC-to-length**, confirmed: DLC 0–8 → 0–8 bytes; 9 → 12, 10 → 16, 11 → 20, 12 → 24, 13 → 32, 14 → 48, 15 → 64. Classic CAN maps DLC 9–15 all to 8.
- **ISO 11898-1:2024 is the current edition** and now also covers CAN XL. Update any reference to the 2015 edition.
- **ISO 15765-2:2016** is current for ISO-TP. Frame types: Single Frame, First Frame, Consecutive Frame, Flow Control; FC carries flow status (CTS/Wait/Overflow), block size and STmin.
- **ISO 13400-2:2019** is current for DoIP; the 2019 edition added secured TLS communication — TCP 13400 unsecured, **TLS on port 3496**.
- **UDS: ISO 14229-1:2020 added service 0x29 Authentication.** Feature it. It supports certificate-based PKI (APCE) and symmetric challenge-response (ACR), with optional mutual authentication and session-key derivation; positive response SID 0x69. The seed/key brute-force scenario remains valid as an attack on legacy 0x27 — but **0x29 must be shown as the remediation or the project looks dated.**
- **MACsec (IEEE 802.1AE)** adoption in vehicles is emerging, not universal. OPEN Alliance TC17 is defining an automotive MACsec/MKA profile, including for 10BASE-T1S — a work in progress. TC8 is the current Automotive Ethernet ECU test specification.

**Add**

- Ground the anomaly detector in what the literature actually supports: cycle-time and frequency analysis (most robust for periodic CAN traffic), entropy-based, message-interval timing, physical-layer voltage/clock fingerprinting (which identifies the transmitting ECU), and ML-based. Note honestly that ML approaches often report low false-positive rates in papers but generalise poorly across vehicles — frequency and timing detectors are the pragmatic baseline.
- Frame the zone-based gateway as **aligned with modern zonal E/E architecture trends**, which it is.
- Cite known SOME/IP-SD attacks — service-discovery hijacking, MITM, forced de-association — and name vsomeip as the open-source reference stack.

**Soften**

- Do not present MACsec as widely deployed in production vehicles today.
- Do not imply DoIP TLS is universal. The standard supports it; real-world adoption lags.

---

## `06` ECU Firmware Security Validation Pipeline

**Correct**

- **FreeRTOS LTS is at 202604.00-LTS** (released 29 April 2026), also distributed as a CMSIS Pack, with security and critical bug fixes until April 2028. Kernel v11.3.0 adds hardware ports, security hardening and expanded MPU support. Update from any older LTS.
- **libFuzzer is in maintenance-only mode** (since late 2022). It still works and is fine as a first fuzzer, but for a 2026 project the stronger primary is **AFL++** (active, multi-core, persistent mode, QEMU mode for binary-only targets) or **LibAFL**. Recommendation: AFL++ as primary, keep a libFuzzer harness for portability, and state the maintenance status explicitly — that nuance signals current awareness.
- **QEMU versus Renode:** Renode is the better fit for a security validation lab because it models multi-node systems, peripherals and sensor buses deterministically and scriptably, which suits fault injection and protocol testing. QEMU is lighter and excellent for single-MCU FreeRTOS demos and CI smoke tests. Name the working targets rather than leaving the choice abstract.
- **MISRA:** the current edition is MISRA C:2012 with Amendments 1/2/3, plus the 2023 consolidated re-issue. No fully free tool can certify compliance. cppcheck has a MISRA add-on covering a subset; clang-tidy does not check MISRA at all. Be precise: *"cppcheck's MISRA add-on covers many rules; full MISRA compliance requires a commercial tool."*
- **Static-analysis tooling status:** cppcheck and clang-tidy are actively maintained; use the `bugprone-*`, `cert-*`, `clang-analyzer-*` and `misc-*` check sets. flawfinder is lightly maintained and pattern-matching only — keep it, but do not overrate it.
- **SBOM/CRA:** the EU Cyber Resilience Act (Regulation (EU) 2024/2847) legally requires an SBOM in a commonly used, machine-readable format covering at least top-level dependencies. Reporting obligations apply from 11 September 2026; full application 11 December 2027. Type-approved whole vehicles are exempt under Art. 2(2)(c); components, diagnostic and development tools and aftermarket devices are in scope.

**Add**

- **Neither UN R155 nor ISO/SAE 21434 explicitly mandates an SBOM** — the CRA is the first binding mandate. But SBOM is a de-facto requirement for R155/21434 vulnerability management, and OEMs are flowing SBOM delivery down to Tier-1 suppliers contractually at scale. Making the CycloneDX SBOM a headline feature and explaining this regulatory nuance demonstrates business awareness, not just tooling.
- **ISO/SAE 21434 Clause 11 is verification and validation**; fuzz testing and penetration testing are expected there, and CAL scales the rigour. Tie the fuzzing and sanitizer stages to Clause 11 and cite Clause 15 for the TARA that justifies *which* parsers to fuzz. This is the cheapest credibility available.
- **Map the eight planted vulnerabilities to specific CWEs** — for example CWE-787 out-of-bounds write, CWE-125 out-of-bounds read, CWE-190 integer overflow, CWE-476 NULL dereference, CWE-457 uninitialised, CWE-134 format string, CWE-20 improper input validation, CWE-416 use-after-free. There is no single official "automotive CWE view"; the CWE Top 25 plus MISRA plus CERT C is the pragmatic embedded-C set.

**Soften**

- Do not claim the pipeline "proves MISRA compliance" — say it checks a subset of MISRA rules via cppcheck.
- Do not call libFuzzer state-of-the-art — acknowledge maintenance mode.
- Do not imply the CRA applies to whole vehicles — state the Art. 2(2)(c) exemption and the component/tool scope.

---

## Cross-cutting

**Regulatory landscape to be aware of**

UN R155/R156 have been mandatory in the EU for all new vehicles since 7 July 2024, enforced via type-approval authorities; R155 requires a certified CSMS plus per-type approval against the Annex 5 threat list. Consolidated text is Supplement 3, in force 10 January 2025. Beyond Europe: **China GB 44495-2024** is a mandatory national automotive cybersecurity standard under China's own type-approval regime — China has not adopted R155. **India AIS-189** is aligned with R155 concepts. **NIS2**, as transposed in Germany, brings larger vehicle and parts manufacturers into scope as important entities.

**Competitive landscape**

The open automotive tooling that already exists — CaringCaribou, ICSim, CANToolz, cantools, can-utils, Kali NetHunter CARsenal — should be *used* by these projects rather than competed with. The differentiation is that almost none of them provide SecOC, a structured 21434-native TARA, or a signed-boot and key-lifecycle story. The thesis to lead with: most open tools are single-purpose and generic; this portfolio is **automotive-specific, standards-traceable, and end-to-end** — boot → comms → keys → risk → network → firmware CI.

**What entry-level automotive-cyber postings actually ask for**

C/C++ and Python; UDS (ISO 14229-1); ISO/SAE 21434 process and TARA literacy; UNECE R155/R156 familiarity; Classic AUTOSAR and its tooling; CAN and Automotive Ethernet; secure boot, secure update and secure diagnostics; static analysis and fuzzing; ASPICE. These six projects hit nearly all of it. AV firms opening architect roles at 0–3 years — explicitly listing static and dynamic analysis, fuzz testing, C/C++, attack-surface analysis and ISO 26262/21448/21434 — are the realistic entry point in the Metro Detroit and AV space.

---

## Caveats

**Paywalled standards.** ISO/SAE 21434, ISO 14229, ISO 13400, ISO 11898-1, ISO 15765-2, ISO 17987, MISRA C and the AUTOSAR Classic Platform SWS documents were not read in full. The details here are corroborated via freely published AUTOSAR PDFs and reputable secondary sources. Verify exact tables and wording against the purchased standards before publishing any compliance claim.

**Figures that drift.** The UN R155 Annex 5 attack-vector count drifts between consolidated revisions — verify against the current EUR-Lex text. Sources differ on the CRA's exact entry-into-force date (10 December 2024 is most widely cited); the staged application dates are consistent.

**Anything under active revision** — SP 800-57 Rev 6, the ISO/SAE 21434 second edition, ISO/SAE 8475, the OPEN Alliance MACsec profile — should be treated as provisional and re-checked at publication. `make standards` lists exactly which rows those are.
