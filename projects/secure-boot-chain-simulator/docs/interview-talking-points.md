# Interview talking points - Secure Boot Chain Simulator

Fill these in **after** the build, with real numbers from your own run. This is a scaffold for your
own answers, not a script to memorize.

## The 30-second version
"I built a simulated multi-stage boot chain -- ROM to bootloader to application -- where each stage
verifies the next before handing off. The interesting part isn't the signature check; it's the
rollback protection. I can show you an image with a perfectly valid signature from the legitimate
signing key that the chain still refuses to boot, because its security version number is behind the
monotonic counter in the fuses."

## Questions you should be able to answer cold

**"Why hash the root public key into fuses instead of storing the key itself?"**
OTP is expensive and fixed-width. A 32-byte digest commits to the key at a fraction of the fuse
budget, and the full key rides along in the image where it costs nothing.

**"Why is SVN separate from the version number?"**
Marketing versions go up for reasons unrelated to security. SVN increments only when a fix closes a
vulnerability, so the anti-rollback floor doesn't move every release and you keep the ability to
ship a benign downgrade.

**"When do you advance the counter?"**
This is the tradeoff to talk through out loud: advance before the image proves itself and one bad
signed update bricks the ECU with no path back; advance only after a confirmed healthy boot and you
need a confirmation mechanism plus a window where the old image is still acceptable. Explain which
you implemented and why.

**"What does this NOT protect against?"**
A compromised signing key before revocation propagates. A ROM bug. Physical glitching of the compare
instruction. Anything after the app is running. Naming your limits is what separates you from
someone reciting a diagram.

**"How would this change on real hardware?"**
The HSM object becomes an EVITA-Medium core or an SHE module; fuses become real OTP; the counter
becomes a hardware monotonic counter; the verify loop lives in ROM you cannot patch.

**"Why did you pick ECDSA P-256, and what happens in ten years?"**
Current automotive practice, hardware-accelerated, small signatures. For a vehicle on the road into
the 2040s the firmware-signing root is the first thing to migrate -- hash-based signatures
(LMS/XMSS) are the conservative option that is deployable today, ML-DSA the general-purpose one.
That is why the container has an algorithm ID field and a policy allowlist instead of a hardcoded
algorithm.

## Claim discipline

Say what is true:
- "I designed and implemented a simulated secure boot chain in Python: a signed image container
  format, staged signature verification, monotonic anti-rollback counters, key revocation, measured
  boot with a PCR model, and a hash-chained audit log."
- "I researched secure boot and HSM key management during my internship; this project is where I
  turned that research into something I can build and demonstrate."

Do not say:
- That you shipped secure boot on a production ECU.
- That you have hands-on experience with a specific vendor HSM you have not used.
- That this is production-grade or that the cryptography has been independently reviewed.

If asked whether it's real hardware, lead with the answer: it's a simulation, and here is precisely
which parts map to hardware and which don't.
