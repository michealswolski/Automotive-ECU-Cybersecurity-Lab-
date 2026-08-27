# Verified boot, measured boot, and why both

The one-line version:

> **Verified boot blocks. Measured boot records.**

They answer different questions and neither substitutes for the other.

## Verified boot

Before a stage runs, check a signature over it. If the check fails, do not
transfer control. That is the whole idea, and it is what `verify.py` implements.

What it gives you: a bad image never executes.

What it cannot give you:

* **Which good image booted.** A device that verified successfully has proved
  "something signed by an authorised key ran". A fleet operator usually wants to
  know *which version*, and a signature check does not answer that.
* **Any evidence at all if the check is defeated.** Glitch the compare — voltage,
  clock, or laser on the branch that consumes the result — and the CPU behaves as
  though the signature verified. Verified boot has now failed silently, which is
  the worst way for a control to fail.

## Measured boot

Before a stage runs, fold a digest of it into a register that only moves
forward:

```
PCR[n] = SHA256(PCR[n] || measurement)
```

The operation is one-way and order-dependent. A stage cannot un-measure itself,
and two stages measured in the wrong order produce a different bank. Later,
something signs the bank — an attestation quote — and a remote party compares it
against what they expected.

What it gives you: an unforgeable record of what actually ran, and therefore a
way for someone off the vehicle to notice.

What it cannot give you: any protection at all in the moment. The bad image ran.

## Together

`tests/test_glitch_toctou.py` is the whole argument in two tests:

1. `test_a_glitched_signature_compare_lets_a_bad_image_run` — verified boot is
   defeated, and the tampered image boots. Uncomfortable and true.
2. `test_measured_boot_records_what_verified_boot_missed` — the PCR moved anyway,
   so the attestation quote diverges from the golden set at exactly PCR2, and a
   remote verifier sees it.

Neither control caught the attack alone. The pair did.

## The register allocation

| Register | Records | Why it is measured |
|----------|---------|--------------------|
| PCR0 | Fuse state digest | A part whose fuses differ is a different part. Measured first, so everything after it is qualified by it |
| PCR1 | Bootloader | The stage the ROM verified |
| PCR2 | Application | The stage the bootloader verified |
| PCR3 | Policy digest | A device that quietly widened its algorithm allowlist or its signer list is as compromised as one running a modified image. Only a measurement makes that visible |

## An honest caveat about the model

The PCR-extend construction comes from the TCG's TPM specifications. Most
automotive HSMs are **not** TPMs — they are SHE or EVITA class, with a different
programming model and no PCR bank in the TPM sense. There is no dominant
automotive attestation standard today.

So what this project implements is an *emulation* of the TCG extend model and of
the firmware-measurement approach NIST SP 800-155 describes, running on a
simulated EVITA-style HSM. It is a faithful model of the idea. It is not a claim
of conformance to anything, and calling a PCR bank "the automotive standard"
would be wrong.
