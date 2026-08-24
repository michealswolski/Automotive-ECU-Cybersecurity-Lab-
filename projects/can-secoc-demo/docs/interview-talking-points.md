# Interview talking points - CAN SecOC Demo

Fill in with your own numbers after the build.

## The 30-second version
"I implemented AUTOSAR SecOC over a virtual CAN bus -- AES-128 CMAC with a truncated MAC and a
truncated freshness counter, matching the standard profiles. Then I wrote an attacker node that
captures a frame and replays it byte for byte. On the unprotected bus the receiver actuates on the
stale command. With SecOC enabled the same bytes get rejected, because the freshness value is behind
the receiver's counter. I can run both back to back in about ninety seconds."

## Questions you should be able to answer cold

**"Why isn't a MAC alone enough?"**
A MAC proves the message came from someone holding the key. It says nothing about *when*. Replay it
an hour later and it is still a valid MAC over that payload. Freshness binds the message to a point
in the counter sequence. Run the `no-fv` scenario -- Profile 2 has a valid MAC and replay still works.

**"24 bits of MAC. Isn't that weak?"**
Per attempt, forgery is 1 in 2^24. The relevant question is attempts per second on the bus and
whether a receiver rate-limits or logs repeated failures. Give your measured number from the
brute-force scenario. Then note the real constraint: a classic CAN frame is 8 bytes, so every MAC bit
costs a payload bit -- which is why CAN FD changes the calculus.

**"How does the receiver know the full freshness value if you only send 8 bits?"**
It doesn't receive it; it reconstructs it. It keeps its own counter, takes the transmitted low bits,
and searches a small window of candidates ahead of its last accepted value, recomputing the MAC for
each until one matches -- capped, so a bad frame can't cost unbounded CPU.

**"What happens when the receiver resets and loses its counter?"**
Everything fails verification, permanently, until resynchronization. That is the failure mode that
bites people in the field. Show the `desync` scenario and the authenticated sync message.

**"What does SecOC not protect against?"**
Availability. An attacker who floods or suppresses frames wins regardless. It also doesn't help if a
legitimate ECU is compromised and still holds valid keys -- which is exactly why key separation per
Data ID and key rotation matter, and why the lifecycle sits in a separate project.

**"How does this differ from what actually ships?"**
Every OEM configures SecOC differently -- which PDUs are protected, FV construction, sync strategy,
where the key lives. This runs the profiles as publicly specified; a production stack does it in the
AUTOSAR CSM/Crypto stack with the MAC computed in an HSM.

## Claim discipline

Say what is true:
- "I implemented the AUTOSAR SecOC profiles over virtual CAN in Python: AES-128 CMAC authenticator,
  truncated MAC and freshness value, receiver-side freshness reconstruction with an acceptance
  window, freshness resynchronization, and a replay/forgery attacker for validation."
- "I verified the CMAC implementation against the RFC 4493 test vectors."

Do not say:
- That you have production AUTOSAR development experience.
- That this is AUTOSAR-conformant or certified.
- That you have worked on a real OEM SecOC deployment.
