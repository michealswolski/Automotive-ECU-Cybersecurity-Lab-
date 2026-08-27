# Corrections — Secure Boot Chain Simulator

Apply these while building. They correct assumptions in `SPEC.md` and `CLAUDE.md` that were accurate when written and have since moved. Full reasoning and provenance: [`docs/spec-corrections.md`](../../docs/spec-corrections.md). Editions to cite: [`docs/standards-register.md`](../../docs/standards-register.md).

## Must fix

- [x] **Do not call ML-DSA a CNSA 2.0 firmware-signing root.** CNSA 2.0 specifies **LMS or XMSS** (stateful hash-based, NIST SP 800-208) for firmware and software signing. ML-DSA-87 is named for general signatures. Frame the ML-DSA backend as a *PQC-ready demonstration of FIPS 204*, not as CNSA compliance.
- [x] **SAE J3101 is published** — J3101_202002, February 2020. Not a draft, not in development.
- [x] **FIPS 203/204/205 were finalized August 2024.** Remove any wording that treats 204 or 205 as draft.
- [x] **NIST SP 800-193 is current** (May 2017). The withdrawn document in search results is the initial public draft, not the final.
- [x] **`cryptography` exposes ML-DSA natively** — added 47.0.0 (`cryptography.hazmat.primitives.asymmetric.mldsa`), broader backends in 48. Pin `cryptography>=48` for the PQ extra. **Caveat that matters:** PQ support needs an AWS-LC or BoringSSL backend and most wheels ship OpenSSL, so probe at runtime and gate the feature behind a clear, actionable error. SLH-DSA is not yet exposed. Never fake a PQ signature.

## Add — these are what read as senior

- [x] Model the **advance-SVN-before vs after-confirmed-healthy-boot** tradeoff explicitly. Advancing the monotonic counter before confirmation can brick a device with no path back to the known-good lower SVN; advancing only after a confirmed healthy boot needs a confirmation mechanism plus a window where the old image is still acceptable. Implement one, and be able to argue the other.
- [x] Model real monotonic-counter substrates: OTP/eFuse-backed and secured-flash monotonic counters.
- [x] Add classic secure-boot attacks as **test cases**: voltage and clock glitching of the verify-compare, TOCTOU between verify and load, signature stripping, stage confusion.
- [x] Consider **SHA-384** as the hash default, to align with CNSA 2.0 posture.

## Soften

- [x] "Measured boot = TPM PCR" is wrong for automotive. Most automotive HSMs are SHE/EVITA-style, not TPMs. TCG PCR-extend and SP 800-155 are the model being *emulated*, and there is no dominant automotive attestation standard yet — say so.

## Cite

SAE J3101 · NIST SP 800-193 · NIST SP 800-208 · NSA CNSA 2.0 · FIPS 204 · UN R156 · ISO 24089

---

## How each was applied

- **ML-DSA is not framed as CNSA 2.0.** `docs/post-quantum.md` states the split
  explicitly: CNSA 2.0 specifies LMS or XMSS (SP 800-208) for firmware signing;
  ML-DSA-87 is named for general signatures. `algo_id = 3` is presented as a
  FIPS 204 demonstration in the crypto-agility slot, nothing more.
- **SAE J3101, NIST SP 800-193, FIPS 204/205 editions** are cited from the lab's
  standards register in `docs/standards-references.md`, with the withdrawn-draft
  trap for SP 800-193 called out in the text.
- **`cryptography` ML-DSA support is probed, not assumed.** `algo.available()`
  generates a key to find out, because the module imports cleanly over an
  OpenSSL backend and only fails at key generation. `secboot algos` reports what
  the installed build can actually do, and an unavailable algorithm fails with
  `ALGO_BACKEND_UNAVAILABLE` and a message naming the cause. No signature is
  ever fabricated. ADR-0006.
- **The advance-before vs advance-after-confirmation tradeoff** is ADR-0002,
  implemented as `stage_advance` plus `secboot confirm-boot`, and tested from
  both sides: the older image still boots before confirmation and stops after.
- **Both counter substrates are modelled** — an OTP eFuse counter that runs out
  of fuse bits and a replay-protected flash counter that does not. ADR-0007.
- **Glitching, TOCTOU, signature stripping and stage confusion are test cases**,
  in `tests/test_glitch_toctou.py` and `tests/test_verify_order.py`. The glitch
  is also demo scenario 9, because it is the only one where a control fails and
  a different control catches it.
- **SHA-384 is available for signatures** (`ecdsa-p384`, `algo_id = 4`) and is
  half of the demo's policy allowlist, so the algorithm-floor scenario is a real
  CNSA-posture refusal. The container's `payload_sha256` field stays SHA-256 for
  the reason in ADR-0005 — it is a fixed-width field in a fixed-size header, and
  widening it is a format change rather than a policy one.
- **"Measured boot = TPM PCR" is softened everywhere it appears.**
  `docs/verified-vs-measured-boot.md` says plainly that most automotive HSMs are
  SHE or EVITA class rather than TPMs, that there is no dominant automotive
  attestation standard today, and that what is implemented is an emulation of
  the TCG extend model rather than conformance to anything.
