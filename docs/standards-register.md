# Standards register

The edition each project should cite, when it was last checked, and against what.

This page exists because the fastest way to lose a room in automotive security is to cite a document that has moved. Naming ISO/SAE 21434 Clause 15 is a credibility multiplier; naming AUTOSAR R20-11 in 2026 undoes it in one sentence.

So the register is data, not prose. It lives in `lab.toml`, and `labctl validate` **fails the build** if a project cites a standard that is not declared, or one marked superseded, or if any project cites no standard at all. Run `make standards` to see it in the terminal.

<!-- labctl:begin standards-register -->

### Process & regulation

| Standard | Edition to cite | Status | Cited by | Checked |
|---|---|---|:---:|---|
| **ISO/SAE 21434** — Road vehicles — Cybersecurity engineering | 2021 (first edition) | ● Current | `04` `06` | 2026-08-24 · web |
| **ISO/SAE PAS 8475** — Cybersecurity Assurance Levels (CAL) and Targeted Attack Feasibility (TAF) | PAS, stage 50.20 | ◐ Publication imminent | `04` | 2026-08-24 · web |
| **UN ECE R155** — Cyber security and cyber security management system | Supplement 3 (in force 10 January 2025) | ● Current | `04` | 2026-08-24 · web |
| **UN ECE R156** — Software update and software update management system | current series | ● Current | `01` `03` | 2026-08-24 · web |
| **ISO 24089** — Road vehicles — Software update engineering | 2023, with Amd 1:2024 | ● Current | `01` `03` | 2026-08-24 · web |
| **EU Cyber Resilience Act** — Regulation (EU) 2024/2847 | in force 10 December 2024 | ● Current | `06` | 2026-08-24 · web |

### Communication

| Standard | Edition to cite | Status | Cited by | Checked |
|---|---|---|:---:|---|
| **AUTOSAR SecOC** — FO PRS SecOcProtocol / CP SWS SecureOnboardCommunication | R25-11 | ● Current | `02` `05` | 2026-08-24 · web |
| **ISO 11898-1** — Road vehicles — CAN — Data link layer and physical signalling | 2024 | ● Current | `02` `05` | 2026-08-24 · web |
| **ISO 15765-2** — Road vehicles — Diagnostic communication over CAN — Transport protocol | 2024 | ● Current | `05` `06` | 2026-08-24 · web |
| **ISO 14229-1** — Road vehicles — Unified Diagnostic Services — Application layer | 2020 | ● Current | `05` `06` | 2026-08-24 · web |
| **ISO 13400-2** — Road vehicles — Diagnostic communication over IP (DoIP) | 2025 | ● Current | `05` | 2026-08-24 · web |
| **LIN 2.2A / ISO 17987** — Local Interconnect Network | LIN 2.2A; ISO 17987 series | ● Current | `05` | 2026-08-24 · report |
| **IEEE 802.1AE (MACsec)** — Media Access Control Security | current; OPEN Alliance TC17 automotive profile in progress | ● Current | `05` | 2026-08-24 · report |

### Cryptography

| Standard | Edition to cite | Status | Cited by | Checked |
|---|---|---|:---:|---|
| **RFC 4493** — The AES-CMAC Algorithm | 2006 | ● Current | `02` | 2026-08-24 · report |
| **NIST SP 800-38B** — Recommendation for Block Cipher Modes of Operation: the CMAC Mode | 2005 (updated 2016) | ● Current | `02` | 2026-08-24 · report |
| **NIST SP 800-57 Part 1** — Recommendation for Key Management: General | Revision 5 (May 2020) | ◐ Revision in draft | `03` | 2026-08-24 · web |
| **NIST SP 800-130** — A Framework for Designing Cryptographic Key Management Systems | 2013 | ● Current | `03` | 2026-08-24 · report |
| **NIST SP 800-193** — Platform Firmware Resiliency Guidelines | May 2017 | ● Current | `01` | 2026-08-24 · web |
| **NIST SP 800-208** — Recommendation for Stateful Hash-Based Signature Schemes | 2020 | ● Current | `01` | 2026-08-24 · web |
| **NSA CNSA 2.0** — Commercial National Security Algorithm Suite 2.0 | May 2025 reissue | ● Current | `01` | 2026-08-24 · web |
| **FIPS 204** — Module-Lattice-Based Digital Signature Standard (ML-DSA) | finalized August 2024 | ● Current | `01` | 2026-08-24 · web |
| **SAE J3101** — Hardware Protected Security for Ground Vehicles | J3101_202002 (February 2020) | ● Current | `01` | 2026-08-24 · web |
| **RFC 9162** — Certificate Transparency Version 2.0 | 2021 | ● Current | `03` | 2026-08-24 · report |

### Firmware quality

| Standard | Edition to cite | Status | Cited by | Checked |
|---|---|---|:---:|---|
| **MISRA C:2023** — Guidelines for the use of the C language in critical systems | consolidates MISRA C:2012 AMD1–AMD4 | ● Current | `06` | 2026-08-24 · web |
| **SEI CERT C** — CERT C Coding Standard | 2nd Edition | ● Current | `06` | 2026-08-24 · web |
| **CycloneDX** — SBOM format | current | ● Current | `06` | 2026-08-24 · report |
| **SPDX** — System Package Data Exchange (ISO/IEC 5962) | ISO/IEC 5962 | ● Current | `06` | 2026-08-24 · report |

<!-- labctl:end standards-register -->

**Status.** `●` current — the edition to cite. `◐` under active revision — cite the current edition and mention what is coming. `✕` superseded — a project citing this fails the build.

**Checked.** The date the row was last verified and how. `web` means a primary or reputable secondary source was consulted on that date. `report` means the row comes from the 2026 spec-validation report and has not been independently rechecked — see [spec corrections](./spec-corrections.md).

---

## Which project implements what

<!-- labctl:begin project-standards -->

| # | Project | Implements |
|---|---|---|
| `01` | [Secure Boot Chain Simulator](../projects/secure-boot-chain-simulator) | SAE J3101, NIST SP 800-193, NIST SP 800-208, NSA CNSA 2.0, FIPS 204, UN ECE R156, ISO 24089 |
| `02` | [CAN Bus SecOC Demo](../projects/can-secoc-demo) | AUTOSAR SecOC, RFC 4493, NIST SP 800-38B, ISO 11898-1 |
| `03` | [ECU Key Lifecycle Manager](../projects/ecu-key-lifecycle) | NIST SP 800-57 Part 1, NIST SP 800-130, RFC 9162, UN ECE R156, ISO 24089 |
| `04` | [ISO/SAE 21434 TARA Workbench](../projects/tara-workbench) | ISO/SAE 21434, ISO/SAE PAS 8475, UN ECE R155 |
| `05` | [In-Vehicle Network Security Lab](../projects/ivn-security-lab) | ISO 11898-1, ISO 15765-2, ISO 14229-1, ISO 13400-2, LIN 2.2A / ISO 17987, IEEE 802.1AE (MACsec), AUTOSAR SecOC |
| `06` | [ECU Firmware Security Validation Pipeline](../projects/ecu-firmware-validation) | ISO/SAE 21434, ISO 14229-1, ISO 15765-2, MISRA C:2023, SEI CERT C, CycloneDX, SPDX, EU Cyber Resilience Act |

<!-- labctl:end project-standards -->

Put the clause number in the project README — "SecOC per AUTOSAR FO R25-11 PRS", "TARA per ISO/SAE 21434 Clause 15", "V&V per Clause 11". That single habit does more for credibility than another feature.

---

## Under active revision

Re-check these before quoting them. A specification at final approval can publish the week after you write your README.

<!-- labctl:begin standards-watchlist -->

| Standard | Cite this today | Where it stands | Affects |
|---|---|---|:---:|
| **ISO/SAE PAS 8475** | PAS, stage 50.20 | Publication imminent | `04` |
| **NIST SP 800-57 Part 1** | Revision 5 (May 2020) | Revision in draft | `03` |

<!-- labctl:end standards-watchlist -->

---

## What each row actually tells you

The register's notes are where the engineering guidance lives — the DLC table, the LIN parity formulas, which UDS service supersedes which, and the one PQC mistake almost everybody makes.

<!-- labctl:begin standards-notes -->

### Process & regulation

**ISO/SAE 21434 — 2021 (first edition)**

Clause 15 is the TARA clause; Clause 11 is verification & validation. Entered ISO systematic review in July 2026; a second edition is expected to start development in 2026 on a roughly three-year timeline. No revision yet — say review has begun. Paywalled: cite public secondary sources for tables rather than reproducing them.

**ISO/SAE PAS 8475 — PAS, stage 50.20**

At final approval as of mid-July 2026, publication expected imminently. Makes CAL prescriptive and redefines the levels as Basic/Intermediate/Advanced, replacing the informative CAL1–CAL4 of ISO/SAE 21434 Annex E. Adds TAF as a design target distinct from descriptive attack feasibility. Supporting it is a forward-looking differentiator; do not present it as published.

**UN ECE R155 — Supplement 3 (in force 10 January 2025)**

Mandatory in the EU for all new vehicles since 7 July 2024 (new types since July 2022). Requires a certified CSMS plus per-type approval against the Annex 5 threat list. Does NOT mandate an SBOM — that is the CRA. Verify the Annex 5 attack-vector count against the current EUR-Lex text; it drifts between consolidated revisions.

**UN ECE R156 — current series**

The update-integrity companion to R155: manufacturers must ensure the integrity and authenticity of software updates and manage software identification (RxSWIN). The natural regulatory hook for anti-rollback and revocation.

**ISO 24089 — 2023, with Amd 1:2024**

The engineering standard underpinning UN R156.

**EU Cyber Resilience Act — in force 10 December 2024**

The first binding SBOM mandate in law: a machine-readable SBOM covering at least top-level dependencies (Annex I Part II(1), Art. 13). Reporting duties apply from 11 September 2026; full application 11 December 2027. Type-approved whole vehicles are exempt under Art. 2(2)(c) — components, diagnostic and development tools and aftermarket devices are in scope.

### Communication

**AUTOSAR SecOC — R25-11**

R25-11 was released in December 2025 and is current; R24-11 is the prior release. The 2026 validation report names R24-11 as current — it is not, and that correction is the point of this register. The three standard profiles (1: 24Bit-CMAC-8Bit-FV, 2: 24Bit-CMAC-No-FV, 3: JASPAR) remain the only numbered profiles; SecOC is transport-agnostic so CAN FD and Ethernet needed no new profile.

**ISO 11898-1 — 2024**

The 2024 edition also covers CAN XL (data fields to 2048 bytes). Update any reference to the 2015 edition. CAN FD DLC-to-length above 8: 9→12, 10→16, 11→20, 12→24, 13→32, 14→48, 15→64; classic CAN maps DLC 9–15 all to 8.

**ISO 15765-2 — 2024**

ISO-TP. The fourth edition (April 2024) replaced the 2016 edition — the 2026 validation report names 2016, which is stale. Frame types: Single Frame, First Frame, Consecutive Frame, Flow Control. Flow Control carries flow status (CTS / Wait / Overflow), block size and STmin. A reassembler handling attacker-controlled length fields is the right fuzzing target.

**ISO 14229-1 — 2020**

The 2020 edition introduced service 0x29 Authentication as the modern replacement for 0x27 SecurityAccess: certificate-based PKI (APCE) and symmetric challenge-response (ACR), with optional mutual authentication and session-key derivation; positive response SID 0x69. 0x27 remains in the standard but ISO 15765-4 deprecates it for new designs. A seed/key brute-force scenario is still a valid attack on legacy 0x27 — but 0x29 must appear as the remediation or the project reads as dated.

**ISO 13400-2 — 2025**

DoIP. ISO 13400-2:2019 and its Amd 1:2023 are both withdrawn; the 2025 edition is current and carries DoIP protocol version 4 — the 2026 validation report names 2019, which is stale. Secured (TLS) communication arrived in the 2019 edition: TCP 13400 unsecured, TLS on 3496. Real-world TLS adoption still lags — do not imply it is universal.

**LIN 2.2A / ISO 17987 — LIN 2.2A; ISO 17987 series**

Protected identifier parity: P0 = ID0 ⊕ ID1 ⊕ ID2 ⊕ ID4 (even); P1 = ¬(ID1 ⊕ ID3 ⊕ ID4 ⊕ ID5) (odd). PID is the 6-bit frame ID in bits 0–5, P0 in bit 6, P1 in bit 7. Classic checksum covers data bytes only (LIN 1.x); enhanced checksum covers PID plus data (LIN 2.x); frame IDs 0x3C–0x3D always use classic. LIN has no native security — contain it at the gateway rather than inventing a fix.

**IEEE 802.1AE (MACsec) — current; OPEN Alliance TC17 automotive profile in progress**

Automotive adoption is emerging, not universal. OPEN Alliance TC17 is defining an automotive MACsec/MKA profile including for 10BASE-T1S — a work in progress. Present MACsec as arriving, not as standard practice. TC8 is the current Automotive Ethernet ECU test specification.

### Cryptography

**RFC 4493 — 2006**

The AES-CMAC reference and the source of the four known-answer test vectors that gate the SecOC project's phase 1. Consistent with NIST SP 800-38B.

**NIST SP 800-38B — 2005 (updated 2016)**

The CMAC mode specification. Cite alongside RFC 4493, not instead of it.

**NIST SP 800-57 Part 1 — Revision 5 (May 2020)**

Rev 5 is the current published version and the one to cite. An initial public draft of Revision 6 was published 5 December 2025 with comments through 5 February 2026; it adds the FIPS 203/204/205 algorithms and Ascon, and replaces the algorithm-approval timeframes with references to SP 800-131A. Cryptoperiods (Rev 5, Table 1): symmetric data-encryption / authentication / key-wrapping keys — originator-usage period ≤ 2 years, recipient-usage ≤ OUP + 3 years; symmetric master or key-derivation key ~1 year; symmetric key-agreement 1–2 years. These are guidance, not automotive mandates.

**NIST SP 800-130 — 2013**

Still a final publication, not withdrawn. The right CKMS design framework to reference. SP 800-152 (US federal CKMS profile, 2015) is also final but is US-federal-specific — do not overstate its applicability.

**NIST SP 800-193 — May 2017**

Current, not withdrawn — the withdrawn item that surfaces in searches is the initial public draft, not the final. Three principles: Protection, Detection, Recovery, founded on roots of trust (RTU / RTD / RTRec).

**NIST SP 800-208 — 2020**

Specifies LMS and XMSS — the schemes CNSA 2.0 names for firmware and software signing. Stateful: one-time-use keys demand careful state management, which is itself worth modelling.

**NSA CNSA 2.0 — May 2025 reissue**

For software and firmware signing CNSA 2.0 specifies the stateful hash-based schemes LMS or XMSS — NOT ML-DSA. ML-DSA-87 is named for general signatures, ML-KEM-1024 for key establishment, SHA-384/512 and SHA3-384/512 for internal hardware functions. Timeline: support and prefer by 2025, exclusive use by 2030 for firmware signing. Treating ML-DSA as the CNSA-2.0 firmware signing root is the single most common PQC-for-firmware error.

**FIPS 204 — finalized August 2024**

Finalized alongside FIPS 203 (ML-KEM) and FIPS 205 (SLH-DSA) in August 2024 — none of the three is a draft. Python `cryptography` added ML-DSA-44/65/87 in 47.0.0 and broadened backend support in 48; post-quantum support requires an AWS-LC or BoringSSL backend, and most published wheels ship OpenSSL, so gate the feature and probe for it rather than assuming. SLH-DSA is not yet exposed.

**SAE J3101 — J3101_202002 (February 2020)**

Published, not in development. Defines requirements via fundamental use cases for a hardware protected security environment acting as a gatekeeper for system data and control access. Requirements-oriented, not implementation-prescriptive.

**RFC 9162 — 2021**

The Merkle-tree log model to reference for a tamper-evident audit log. A hash chain proves nobody edited the log; a Merkle tree adds efficient inclusion proofs; signing the head with an HSM-held key makes it attributable rather than merely detectable.

### Firmware quality

**MISRA C:2023 — consolidates MISRA C:2012 AMD1–AMD4**

Paid standard. MISRA C:2023 is the current consolidated document, rolling up Amendment 2, Technical Corrigendum 2, Amendment 3 and Amendment 4 — the last of which (March 2023) added multithreading and atomics guidance for C11/C18. The 2026 validation report says AMD1/2/3; it is AMD1–4. No fully free tool can certify compliance: cppcheck has a MISRA add-on (`--addon=misra`) covering a subset; clang-tidy does not check MISRA at all. Say 'checks a subset of MISRA rules via cppcheck', never 'MISRA compliant'.

**SEI CERT C — 2nd Edition**

What the open static-analysis toolchain actually gives you. clang-tidy's `cert-*` check set plus `bugprone-*`, `clang-analyzer-*` and `misc-*` is the honest claim: CERT-C-oriented static analysis. MISRA C:2023 Addendum 3 maps its guidelines against CERT C 2nd Edition, which is a useful cross-reference when arguing coverage.

**CycloneDX — current**

Generated by syft; scanned by grype or osv-scanner. Both CycloneDX and SPDX satisfy the CRA's 'commonly used, machine-readable format'. Firmware SBOMs are harder than application SBOMs because vendored source and copied headers do not announce themselves to a scanner — say so.

**SPDX — ISO/IEC 5962**

The ISO-standardised SBOM format; the alternative to CycloneDX, not a replacement.

<!-- labctl:end standards-notes -->

---

## Maintaining it

1. Re-check anything in the watchlist, plus anything whose `verified` date is more than a year old. `make standards` lists both.
2. Update `edition`, `status`, `verified` and `source` in `lab.toml`.
3. `make render`, then `make check`.

When a standard is genuinely superseded, mark it `superseded` rather than deleting it. The build will then fail on every project still citing it, which is exactly the prompt you want — a silent deletion just moves the stale claim somewhere you cannot see it.

## A note on paywalls

ISO/SAE 21434, ISO 14229, ISO 13400, ISO 11898-1, ISO 15765-2, ISO 17987, MISRA C and the AUTOSAR Classic Platform SWS documents are paid or partly paid publications. This repository reproduces none of their text or tables.

Where a table is needed, cite a public secondary source and mark any threshold chosen here as a project convention. Where a clause number cannot be confirmed, cite by document name instead. A wrong clause number is worse than no clause number — it signals that the rest of the citations are decorative too.
