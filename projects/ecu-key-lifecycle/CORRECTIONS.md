# Corrections — ECU Key Lifecycle Manager

Apply these while building. Full reasoning and provenance: [`docs/spec-corrections.md`](../../docs/spec-corrections.md). Editions to cite: [`docs/standards-register.md`](../../docs/standards-register.md).

## Must fix

- [ ] **NIST SP 800-57 Part 1 Revision 5 (May 2020)** is the current published version — cite it as authoritative. Mention that a **Revision 6 initial public draft** was published 5 December 2025 (comments through 5 February 2026), adding the FIPS 203/204/205 algorithms and Ascon. Citing Rev 5 while knowing Rev 6 exists is the combination that shows currency without overclaiming.
- [ ] Use the **real cryptoperiod figures** from Rev 5, Table 1 as the defaults: symmetric data-encryption / authentication / key-wrapping keys — originator-usage period ≤ 2 years, recipient-usage ≤ OUP + 3 years; symmetric master or key-derivation key ~1 year; symmetric key-agreement 1–2 years.
- [ ] **SP 800-130 remains final**, not withdrawn — reference it as the CKMS design framework. SP 800-152 is also final but US-federal-specific; do not overstate its applicability.
- [ ] AUTOSAR **CSM** is the standardised crypto service interface; **KeyM** handles key and certificate management including X.509. They define interfaces and services, not lifecycle policy — that policy layer is what this project adds.

## Add

- [ ] Tie revocation and rollback protection to **UN R156**: integrity and authenticity of software updates, plus software identification (RxSWIN).
- [ ] Compare fleet revocation against **V2X SCMS / IEEE 1609.2**. The transferable lesson: in-vehicle revocation propagation is hard because vehicles are intermittently connected, so lists must be offline-tolerant, signed and rollback-protected.
- [ ] Reference **RFC 9162** (Certificate Transparency v2, Merkle-tree logs) as the model for the tamper-evident log; consider a Merkle-tree option for efficient inclusion proofs.
- [ ] Name the real provisioning context — line-end programming, key injection at manufacture, secure-element personalisation — and mention the **SHE memory-update protocol** (KDF-derived K1/K2 with CMAC) as the canonical symmetric key-injection ceremony being emulated.

## Soften

- [ ] Do not claim the tool "implements AUTOSAR KeyM/CSM" — say it is *modelled on* them.
- [ ] Do not imply NIST cryptoperiods are mandatory for automotive. They are guidance; OEMs tune them.

## Cite

NIST SP 800-57 Part 1 Rev 5 · NIST SP 800-130 · RFC 9162 · UN R156 · ISO 24089
