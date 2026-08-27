# Standards references

One entry per control. Each says what the standard actually asks for, and which
function in this repository answers it.

Editions are the ones in the lab's [standards register](../../../docs/standards-register.md);
that register carries the provenance and the last-verified date. Clause numbers
are cited only where they are verified — where they are not, the standard is
cited by name, which is the honest form.

---

## SAE J3101 — Hardware protected security for ground vehicles

**Edition:** J3101_202002, February 2020. Published, not a draft — a common
error worth stating plainly.

**What it asks for:** requirements for hardware-protected security environments
in ground vehicles: a root of trust anchored in hardware, secure storage for key
material, and a secure boot capability that a non-secure application cannot
subvert. It is a requirements document, not a protocol.

**What answers it here:** `hsm.py` models the protected environment — keys are
generated inside it, `sign()` is the only way to use one, and no API returns
private material (enforced by an AST scan in `tests/test_hsm_isolation.py`).
`fuses.py` models the hardware anchor: a write-once `root_key_hash` that flash
write access cannot change.

**What is not modelled:** tamper resistance, side-channel hardening, and secure
key injection at the silicon vendor. Those are physical properties.

---

## NIST SP 800-193 — Platform Firmware Resiliency Guidelines

**Edition:** May 2017, current. (Search results sometimes surface a withdrawn
document; that is the initial public draft, not the final publication.)

**What it asks for:** three properties for platform firmware — **protection**
(firmware and critical data are updated only through an authenticated mechanism),
**detection** (corruption is detected before the firmware executes), and
**recovery** (a corrupted platform can be restored to a known-good state). It
also calls for a root of trust for update, for detection, and for recovery.

**What answers it here:**

* *Protection* — `verify.verify_stage` steps 12 to 16: no image executes without
  a signature from an authorised key, and `fuses.advance` refuses to lower a
  counter through any public path.
* *Detection* — `image.parse` catches structural corruption, the payload digest
  catches content corruption, and `measure.py` records what ran whether or not
  anyone asks.
* *Recovery* — **partially, and this is the honest gap.** ADR-0002's staged
  counter advance keeps the previous image bootable until a healthy start is
  confirmed, which is a recovery *path*. There is no A/B slot and no golden
  recovery image, both of which SP 800-193 would expect.

---

## UN ECE R155 — Cyber security and cyber security management system

**Edition:** Supplement 3, in force 10 January 2025.

**What it asks for:** a certified cybersecurity management system, and that the
vehicle type has mitigations for the threats enumerated in Annex 5. Two Annex 5
entries land squarely on this project: unauthorised modification of vehicle
software, and use of an outdated or obsolete software version.

**What answers it here:** the first is signature verification, steps 12 to 15.
The second is `ROLLBACK_BLOCKED` — and it is the one people forget, because a
downgraded release carries a perfectly valid signature. `tests/test_rollback.py`
makes that the project's headline test.

R155 also requires that the manufacturer can detect and respond to incidents.
`audit.py` is the on-device half of that: hash-chained records that make a quiet
edit impossible, so an investigator can trust what the part reports.

---

## UN ECE R156 and ISO 24089 — Software update management

**Editions:** R156 current series; ISO 24089:2023, with Amendment 1:2024.

**What they ask for:** R156 requires a certified software update management
system, protection of the update process against manipulation, and the ability to
identify the software version on a vehicle (the RxSWIN construct). ISO 24089 is
the engineering standard underneath it — how to actually engineer a software
update capability.

**What answers it here:** the container's `svn` field and the monotonic counter
are the anti-rollback half. The distinction between `svn` and `image_version` is
the interesting part and it is deliberate: `image_version` is informational and
**never** used for a security decision, while `svn` is the freshness input. They
move at different rates — most releases do not increment the SVN, because fuse
bits are finite (ADR-0007).

---

## NSA CNSA 2.0, NIST SP 800-208, FIPS 204 — post-quantum posture

**Editions:** CNSA 2.0 as reissued May 2025; SP 800-208 (2020); FIPS 204
finalised August 2024.

**What they ask for:** CNSA 2.0 names firmware and software signing as the
**first** migration target, and specifies **LMS or XMSS** (SP 800-208, stateful
hash-based) for it. ML-DSA-87 (FIPS 204) is named for general-purpose signatures.
The classical floor is ECDSA P-384 with SHA-384.

**What answers it here:** `algo_id = 4` is ECDSA P-384/SHA-384, and the demo's
policy allowlist is set to it plus Ed25519 — so the "algorithm below the policy
floor" scenario is a real CNSA-posture refusal rather than an invented one.
`algo_id = 3` is ML-DSA-65, framed in `post-quantum.md` as a **FIPS 204
demonstration and not a CNSA 2.0 firmware-signing configuration.**

LMS/XMSS is not implemented, and the reason is in `post-quantum.md`: a
state-handling bug in a stateful hash-based scheme is a total break, so
hand-rolling one would violate this project's no-hand-rolled-cryptography rule
far more seriously than anything else in it.

---

## ISO/SAE 21434 — Road vehicles: cybersecurity engineering

**Edition:** 2021, first edition.

**What it asks for:** cybersecurity engineering across the lifecycle —
including the continuous activities (monitoring, event assessment, vulnerability
management) that keep working after the vehicle ships, and the requirement that
cybersecurity claims be supported by evidence rather than assertion.

**What answers it here:** the audit log is the evidence-production mechanism, and
the reason every *passing* decision is logged and not only the failures — an
incident asks "what was running", which a failure-only log cannot answer. More
broadly, this repository's habit of making claims executable is the same idea:
`tests/test_verify_order.py` turns "the checks run in this order" from a sentence
in a specification into something that fails a build.

---

## TCG PCR-extend and NIST SP 800-155 — the measured-boot model

**What they describe:** SP 800-155 covers BIOS integrity measurement; the TCG
specifications define the extend construction `PCR[n] = H(PCR[n] || measurement)`
and the quote structure over a PCR bank.

**What answers it here:** `measure.py`, and `machine.attest`.

**The caveat, stated because it matters:** most automotive HSMs are SHE or EVITA
class, **not** TPMs, and there is no dominant automotive attestation standard
today. What this project implements is an emulation of the TCG model on a
simulated EVITA-style HSM. Calling it "the automotive standard" would be wrong,
and `verified-vs-measured-boot.md` says so at length.
