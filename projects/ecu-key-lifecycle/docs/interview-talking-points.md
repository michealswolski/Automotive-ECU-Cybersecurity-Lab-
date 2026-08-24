# Interview talking points - ECU Key Lifecycle Manager

Fill in with your own numbers after the build.

## The 30-second version
"Most cryptography projects stop at 'I used AES-256'. This one is about everything that happens
after: how a key gets generated in a backend HSM, how it gets provisioned to a specific ECU in a way
that another ECU can't accept, how it rotates across a fleet where a fifth of the vehicles are
asleep, what happens between the moment you declare a compromise and the moment the last ECU learns
about it, and how you prove any of it happened afterward. Every state transition lands in a
hash-chained audit log, and I can tamper with a record live and have the tool name the exact
sequence number."

## Questions you should be able to answer cold

**"Why derive keys instead of storing them?"**
One master key in the HSM and an HKDF info string beats a database of millions of independent
secrets: smaller compromise surface, no key database to protect, and rotation becomes a generation
bump rather than a re-keying campaign.

**"What binds a provisioning package to one specific ECU?"**
The AAD on the AES-GCM wrap includes the ECU ID, purpose, generation, and nonce. A package captured
in transit and replayed at a different ECU fails authentication, because the AAD does not match. I
have a test for exactly that.

**"Why generate the device identity key on the device?"**
So it never exists anywhere else. The backend only ever sees the public half. That's the line
between provisioning and distribution, and it changes your entire threat model for the production line.

**"Why does rotation need an overlap window?"**
Because a fleet is not atomic. Vehicles are parked, out of coverage, or mid-drive. Without an overlap
you either brick communication for the stragglers or you never actually cut over. Show the partial
rotation state.

**"How fast is revocation?"**
It isn't. That's the point of scenario 3. The authority revokes instantly; a given ECU learns about
it when it next fetches the list. The interesting design questions live in that gap -- how long the
list stays valid, and whether an ECU with a stale list fails open or fails closed. Have your answer
and your reasoning for it.

**"What does the audit log actually prove?"**
On its own, that nobody edited it without breaking the chain. If you also sign the chain head with an
HSM-held key, it becomes attributable, not just detectable. Know which one you built.

**"What doesn't this stop?"**
A compromised key authority. A device key physically extracted from silicon. An insider with
legitimate operator credentials -- though the audit log makes their actions attributable, which is a
different kind of control.

## Claim discipline

Say what is true:
- "I designed and implemented a simulated ECU key lifecycle manager covering generation, derivation,
  a challenge-response provisioning ceremony, protected storage, fleet rotation with an overlap
  window, signed revocation lists with rollback protection, cryptoperiod enforcement, and a
  hash-chained tamper-evident audit log."
- "I based the lifecycle model and cryptoperiod defaults on published NIST key management guidance."

Do not say:
- That you have production KMS or PKCS#11/HSM integration experience.
- That you have managed keys for a real vehicle fleet.
- That this is a KMS. It is a simulation of one, and the simulated HSM provides no hardware guarantees.

## The composability angle worth mentioning

If you also build the CAN SecOC demo: this project provisions the very MAC keys that project
consumes. Two repos that plug into each other demonstrate systems thinking in a way that two
unrelated repos never will. Build the export bridge (Phase 10 item 2) and lead with it.
