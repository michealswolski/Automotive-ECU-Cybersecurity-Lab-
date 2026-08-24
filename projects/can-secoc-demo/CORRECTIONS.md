# Corrections — CAN Bus SecOC Demo

Apply these while building. Full reasoning and provenance: [`docs/spec-corrections.md`](../../docs/spec-corrections.md). Editions to cite: [`docs/standards-register.md`](../../docs/standards-register.md).

## Must fix

- [ ] **AUTOSAR is at R25-11** (released December 2025); R24-11 is the prior release. Update any reference to R20-11 or R21-11. Cite `AUTOSAR_FO_PRS_SecOcProtocol` for the protocol and `AUTOSAR_CP_SWS_SecureOnboardCommunication` for the Classic Platform SWS.
- [ ] **State explicitly that the three profiles are still the only standard profiles.** No numbered profile was added for CAN FD or Ethernet — SecOC is transport-agnostic, so none was needed. Leaving this implicit invites the question.
- [ ] Keep the `DataToAuthenticator` construction exactly as specified: **SecOCDataId (16-bit) ‖ secured part of the Authentic I-PDU ‖ Complete Freshness Value**, big-endian throughout. The *complete* FV enters the MAC even though only truncated bits go on the wire.
- [ ] `SecOCFreshnessValueVerificationAttempts` — verify the literal parameter string against the AUTOSAR SWS ECUC parameter table before quoting it in docs or code comments.
- [ ] python-can: use `interface=`, not `bustype=` (deprecated, removal slated for 5.0). `interface="virtual"` for in-process; `udp_multicast` for cross-process.

## Add

- [ ] Cite the **Toyota RAV4 Prime SecOC key-extraction research** (Willem Melching / icanhack.nl, March 2024). Voltage fault injection past a locked debug port, then bootloader reverse-engineering and a key dump from RAM — because that ECU did not use its HSM to hide keys. Newer vehicles do, and extracting from those is described as unsolved. Model the lesson: **SecOC collapses if the key is recoverable from one compromised ECU.**
- [ ] Discuss the known limitations plainly: authenticates but does not encrypt; truncated 24-bit MAC trades bandwidth for forgery margin; freshness sync is fragile; inherits a key-management and HSM dependency.
- [ ] Position Scapy's automotive layers alongside python-can — python-can for the bus, Scapy for dissection and attack tooling.

## Soften

- [ ] Never imply SecOC provides confidentiality. Authenticity and freshness only.
- [ ] Do not claim the profile set is exhaustive of "all SecOC" — OEMs commonly use custom or adapted freshness schemes. Frame yours as the AUTOSAR-standard profiles.

## Cite

AUTOSAR FO R25-11 PRS SecOcProtocol · RFC 4493 · NIST SP 800-38B · ISO 11898-1:2024
