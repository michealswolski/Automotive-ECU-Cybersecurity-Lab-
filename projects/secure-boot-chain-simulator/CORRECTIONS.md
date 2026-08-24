# Corrections — Secure Boot Chain Simulator

Apply these while building. They correct assumptions in `SPEC.md` and `CLAUDE.md` that were accurate when written and have since moved. Full reasoning and provenance: [`docs/spec-corrections.md`](../../docs/spec-corrections.md). Editions to cite: [`docs/standards-register.md`](../../docs/standards-register.md).

## Must fix

- [ ] **Do not call ML-DSA a CNSA 2.0 firmware-signing root.** CNSA 2.0 specifies **LMS or XMSS** (stateful hash-based, NIST SP 800-208) for firmware and software signing. ML-DSA-87 is named for general signatures. Frame the ML-DSA backend as a *PQC-ready demonstration of FIPS 204*, not as CNSA compliance.
- [ ] **SAE J3101 is published** — J3101_202002, February 2020. Not a draft, not in development.
- [ ] **FIPS 203/204/205 were finalized August 2024.** Remove any wording that treats 204 or 205 as draft.
- [ ] **NIST SP 800-193 is current** (May 2017). The withdrawn document in search results is the initial public draft, not the final.
- [ ] **`cryptography` exposes ML-DSA natively** — added 47.0.0 (`cryptography.hazmat.primitives.asymmetric.mldsa`), broader backends in 48. Pin `cryptography>=48` for the PQ extra. **Caveat that matters:** PQ support needs an AWS-LC or BoringSSL backend and most wheels ship OpenSSL, so probe at runtime and gate the feature behind a clear, actionable error. SLH-DSA is not yet exposed. Never fake a PQ signature.

## Add — these are what read as senior

- [ ] Model the **advance-SVN-before vs after-confirmed-healthy-boot** tradeoff explicitly. Advancing the monotonic counter before confirmation can brick a device with no path back to the known-good lower SVN; advancing only after a confirmed healthy boot needs a confirmation mechanism plus a window where the old image is still acceptable. Implement one, and be able to argue the other.
- [ ] Model real monotonic-counter substrates: OTP/eFuse-backed and secured-flash monotonic counters.
- [ ] Add classic secure-boot attacks as **test cases**: voltage and clock glitching of the verify-compare, TOCTOU between verify and load, signature stripping, stage confusion.
- [ ] Consider **SHA-384** as the hash default, to align with CNSA 2.0 posture.

## Soften

- [ ] "Measured boot = TPM PCR" is wrong for automotive. Most automotive HSMs are SHE/EVITA-style, not TPMs. TCG PCR-extend and SP 800-155 are the model being *emulated*, and there is no dominant automotive attestation standard yet — say so.

## Cite

SAE J3101 · NIST SP 800-193 · NIST SP 800-208 · NSA CNSA 2.0 · FIPS 204 · UN R156 · ISO 24089
