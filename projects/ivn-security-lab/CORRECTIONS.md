# Corrections — In-Vehicle Network Security Lab

Apply these while building. Full reasoning and provenance: [`docs/spec-corrections.md`](../../docs/spec-corrections.md). Editions to cite: [`docs/standards-register.md`](../../docs/standards-register.md).

## Must fix

- [ ] **UDS: ISO 14229-1:2020 added service 0x29 Authentication** — and you must feature it. It supports certificate-based PKI (APCE) and symmetric challenge-response (ACR), with optional mutual authentication and session-key derivation; positive response SID 0x69. ISO 15765-4 deprecates 0x27 for new designs. The seed/key brute-force scenario stays as an attack on **legacy 0x27** — but **0x29 must appear as the remediation, or the project looks dated.** This is the single highest-value change here.
- [ ] **ISO 11898-1:2024 is the current edition** (now also covers CAN XL). Update any reference to the 2015 edition.
- [ ] **ISO 13400-2:2019 is current for DoIP.** The 2019 edition added secured TLS: TCP 13400 unsecured, **TLS on port 3496**.
- [ ] **ISO 15765-2:2016** is current for ISO-TP.
- [ ] **MACsec is emerging, not universal.** OPEN Alliance TC17 is defining an automotive MACsec/MKA profile including for 10BASE-T1S — a work in progress. Present MACsec as arriving, not as standard practice. TC8 is the current Automotive Ethernet ECU test spec.

## Confirmed correct — write the KATs against these

- [ ] **LIN protected identifier parity:** `P0 = ID0 ⊕ ID1 ⊕ ID2 ⊕ ID4` (even); `P1 = ¬(ID1 ⊕ ID3 ⊕ ID4 ⊕ ID5)` (odd). PID = 6-bit frame ID in bits 0–5, P0 in bit 6, P1 in bit 7.
- [ ] **LIN checksums:** classic covers data bytes only (LIN 1.x); enhanced covers PID plus data (LIN 2.x); frame IDs 0x3C–0x3D always use classic. Use LIN 2.2A §2.3.1.5 examples as known-answer tests.
- [ ] **CAN FD DLC-to-length:** 0–8 → 0–8 bytes; 9 → 12, 10 → 16, 11 → 20, 12 → 24, 13 → 32, 14 → 48, 15 → 64. Classic CAN maps DLC 9–15 all to 8.
- [ ] **ISO-TP frame types:** Single Frame, First Frame, Consecutive Frame, Flow Control. FC carries flow status (CTS / Wait / Overflow), block size and STmin.
- [ ] **DoIP payload types:** vehicle ID, routing activation, alive check, diagnostic message, entity status.

## Add

- [ ] Ground the anomaly detector in what the literature supports: cycle-time and frequency analysis (most robust for periodic CAN traffic), entropy-based, message-interval timing, physical-layer voltage/clock fingerprinting (identifies the transmitting ECU), and ML-based. Be honest that ML approaches often report low false-positive rates in papers but generalise poorly across vehicles — frequency and timing detectors are the pragmatic baseline.
- [ ] Frame the zone-based gateway as **aligned with modern zonal E/E architecture trends** — it is, and saying so shows you know why the design is shaped that way.
- [ ] Cite known SOME/IP-SD attacks — service-discovery hijacking, MITM, forced de-association — and name vsomeip as the open-source reference stack.
- [ ] Use the existing open tooling rather than competing with it: ICSim for the network lab, CaringCaribou's UDS/discovery/fuzzing modules for attack scenarios, can-utils, cantools.

## Soften

- [ ] Do not present MACsec as widely deployed in production vehicles today.
- [ ] Do not imply DoIP TLS is universal. The standard supports it; adoption lags.

## Cite

ISO 11898-1:2024 · ISO 15765-2:2016 · ISO 14229-1:2020 · ISO 13400-2:2019 · LIN 2.2A / ISO 17987 · IEEE 802.1AE · AUTOSAR FO R25-11 PRS SecOcProtocol
