# Demo output

Captured from `make demo` at seed 1337. Every key, measurement, PCR and audit
hash below is derived from that seed, so this file is reproducible rather than
illustrative — `tests/test_demo_golden.py` fails the build if the demo drifts
from it.

Regenerate with `python tests/test_demo_golden.py --write`, and read the diff
before committing it.

```text

───────────────────────────────── Secure Boot Chain Simulator ──────────────────────────────────

  A simulation, for education and demonstration. It models the controls;
  it does not protect anything. Do not put it near a real device.

  seed 1337 — every key, measurement and audit hash below is
  derived from it, so this output is byte-for-byte reproducible.


──────────────────────────────────────── 1. Clean boot ─────────────────────────────────────────

  attacker capability: none — the reference run
  control under test:  every control passed

  power on
  │
  ├─ BootROM (immutable, trusted by axiom)
  ├─ ✓ SBL  svn=3  algo=ed25519  measured=bab8e448fad3…  svn advance staged → 3
  ├─ ✓ APP  svn=7  algo=ed25519  measured=09c692333dc4…  svn advance staged → 7
  └─ ✓ application running

  The SVN advance is staged, not burned. Until the application
  reports a healthy start, the previous image is still bootable.
  counters before confirm: svn_app=0
  counters after  confirm: svn_app=7

  outcome: ACCEPTED  (as expected, expected ACCEPTED)

──────────────────────── 2. One bit flipped in the application payload ─────────────────────────

  attacker capability: flash write access, no signing key
  control under test:  payload does not match the digest in the signed header

  power on
  │
  ├─ BootROM (immutable, trusted by axiom)
  ├─ ✓ SBL  svn=3  algo=ed25519  measured=bab8e448fad3…  svn advance staged → 3
  └─ ✗ APP  PAYLOAD_DIGEST_MISMATCH
       why: payload does not match the digest in the signed header
       computed: f4343f2993749e4c
       header: fe0e7498019c2b05
       checks that ran: 14 of 16
      control was never transferred

  outcome: PAYLOAD_DIGEST_MISMATCH  (as expected, expected PAYLOAD_DIGEST_MISMATCH)

──────────────────── 3. An older release, re-signed with the legitimate key ────────────────────

  attacker capability: an old signed release plus install access
  control under test:  security version number is behind the monotonic counter

  The image below is signed by the legitimate application key.
  Every signature check passes. Only freshness fails.

  power on
  │
  ├─ BootROM (immutable, trusted by axiom)
  ├─ ✓ SBL  svn=3  algo=ed25519  measured=bab8e448fad3…
  └─ ✗ APP  ROLLBACK_BLOCKED
       why: security version number is behind the monotonic counter
       counter: svn_app
       counter_svn: 7
       image_svn: 3
       checks that ran: 16 of 16
      control was never transferred

  outcome: ROLLBACK_BLOCKED  (as expected, expected ROLLBACK_BLOCKED)

──────────────────────────── 4. Signed with the attacker's own key ─────────────────────────────

  attacker capability: the attacker's signing infrastructure
  control under test:  signer is not on the bootloader's app-signer allowlist

  power on
  │
  ├─ BootROM (immutable, trusted by axiom)
  ├─ ✓ SBL  svn=3  algo=ed25519  measured=bab8e448fad3…  svn advance staged → 3
  └─ ✗ APP  KEY_NOT_AUTHORIZED_FOR_STAGE
       why: signer is not on the bootloader's app-signer allowlist
       authorized_signers: 1
       image_signer: a3b01872310f53d3
       checks that ran: 13 of 16
      control was never transferred

  outcome: KEY_NOT_AUTHORIZED_FOR_STAGE  (as expected, expected KEY_NOT_AUTHORIZED_FOR_STAGE)

─────────────────────── 5. The signing key is compromised, then revoked ────────────────────────

  attacker capability: key theft, followed by the OEM's response
  control under test:  the signing key ID is set in the fuse revocation bitmap

  a moment ago: booted=True
  the application signing key is reported compromised and revoked

  power on
  │
  ├─ BootROM (immutable, trusted by axiom)
  ├─ ✓ SBL  svn=3  algo=ed25519  measured=bab8e448fad3…
  └─ ✗ APP  KEY_ID_REVOKED
       why: the signing key ID is set in the fuse revocation bitmap
       key_id: 1
       checks that ran: 11 of 16
      control was never transferred

  outcome: KEY_ID_REVOKED  (as expected, expected KEY_ID_REVOKED)

────────────────────── 6. A bootloader image presented as the application ──────────────────────

  attacker capability: install access, no modification at all
  control under test:  image is for a different boot stage (stage-confusion attack)

  Nothing is modified. The bytes are a genuine, correctly signed
  bootloader image — presented where the application belongs.

  power on
  │
  ├─ BootROM (immutable, trusted by axiom)
  ├─ ✓ SBL  svn=3  algo=ed25519  measured=bab8e448fad3…  svn advance staged → 3
  └─ ✗ APP  WRONG_STAGE_ID
       why: image is for a different boot stage (stage-confusion attack)
       actual: SBL
       expected: APP
       checks that ran: 6 of 16
      control was never transferred

  outcome: WRONG_STAGE_ID  (as expected, expected WRONG_STAGE_ID)

─────────────────────── 7. An algorithm below the machine's policy floor ───────────────────────

  attacker capability: a signing key of the attacker's choosing
  control under test:  algorithm is not on the machine's policy allowlist

  This machine's policy allows Ed25519 and ECDSA P-384 — the CNSA 2.0
  classical floor. The image asks for P-256, which the verifier can
  perform and refuses to.

  power on
  │
  ├─ BootROM (immutable, trusted by axiom)
  ├─ ✓ SBL  svn=3  algo=ed25519  measured=bab8e448fad3…  svn advance staged → 3
  └─ ✗ APP  ALGO_NOT_PERMITTED
       why: algorithm is not on the machine's policy allowlist
       algo: ecdsa-p256
       allowed: ['ECDSA_P384_SHA384', 'ED25519']
       checks that ran: 10 of 16
      control was never transferred

  outcome: ALGO_NOT_PERMITTED  (as expected, expected ALGO_NOT_PERMITTED)

──────────────────────────── 8. The audit log edited after the fact ────────────────────────────

  attacker capability: write access to the log
  control under test:  the audit log hash chain does not verify

  chain before: 8 records, ok=True
  an attacker edits record 6 to say the boot was clean
  chain after:  ok=False, broken at seq=6
  record contents do not match their recorded hash

  outcome: AUDIT_CHAIN_BROKEN  (as expected, expected AUDIT_CHAIN_BROKEN)

────────────── 9. The signature compare is glitched, and measured boot catches it ──────────────

  attacker capability: physical access and fault injection
  control under test:  a PCR differs from the golden reference

  power on
  │
  ├─ BootROM (immutable, trusted by axiom)
  ├─ ✓ SBL  svn=3  algo=ed25519  measured=bab8e448fad3…
  ├─ ✓ APP  svn=7  algo=ed25519  measured=271e0621c202…
  └─ ✓ application running

  Verified boot was defeated: the compare was glitched and the
  forged image ran. Measured boot still recorded what actually ran.
  attestation vs golden: match=False — diverged: PCR2 (Application image measurement)

  outcome: ATTESTATION_MISMATCH  (as expected, expected ATTESTATION_MISMATCH)

─────────────────────────────────────────── Summary ────────────────────────────────────────────

  ACCEPTED                         Clean boot
  PAYLOAD_DIGEST_MISMATCH          One bit flipped in the application payload
  ROLLBACK_BLOCKED                 An older release, re-signed with the legitimate key
  KEY_NOT_AUTHORIZED_FOR_STAGE     Signed with the attacker's own key
  KEY_ID_REVOKED                   The signing key is compromised, then revoked
  WRONG_STAGE_ID                   A bootloader image presented as the application
  ALGO_NOT_PERMITTED               An algorithm below the machine's policy floor
  AUDIT_CHAIN_BROKEN               The audit log edited after the fact
  ATTESTATION_MISMATCH             The signature compare is glitched, and measured boot catches 
it

  Two of these are the reason the project exists: the downgrade, which
  every signature check passes, and the glitch, which no signature
  check can catch at all.

```

## How to read it

The two scenarios that carry the project are 3 and 9.

**Scenario 3, the downgrade.** The image is signed by the legitimate application
key. Every signature check passes. It is refused because its security version
number is behind the monotonic counter — authenticity and freshness are different
properties, and only the counter provides the second.

**Scenario 9, the glitch.** The signature compare is forced to pass, modelling a
voltage or clock glitch on the instruction that consumes the result. Verified
boot is defeated and the tampered image runs. The measurement moved anyway, so
the attestation quote diverges from the golden set at exactly PCR2 — which is the
entire reason measured boot exists alongside verified boot.
