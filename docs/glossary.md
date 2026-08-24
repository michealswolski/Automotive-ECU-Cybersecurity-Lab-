# Glossary

Automotive product security has a precise vocabulary, and using the wrong term for a concept is the tell that someone has read a blog post rather than thought about the method. Calling a damage scenario a "threat" is the classic example.

These are the terms the six projects use, defined as they are used here.

---

## Threat analysis — ISO/SAE 21434

**Item** — the system under analysis, with its boundary and interfaces defined. Everything downstream is scoped to it. In this portfolio the worked example item is an OTA-capable telematics gateway ECU.

**Asset** — something with a cybersecurity property worth protecting: firmware integrity, key confidentiality, message authenticity.

**Damage scenario** — the *consequence* to road users if an asset's property is violated. "Loss of braking authority at highway speed." Note: to road users, not to the company. A damage scenario written as commercial harm is a common and revealing mistake.

**Threat scenario** — the *way* an asset's property gets violated. "An attacker on the CAN backbone injects a forged brake command." A damage scenario is the outcome; a threat scenario is the mechanism.

**Impact rating** — how bad the damage scenario is, rated across four categories: **safety, financial, operational, privacy**.

**Attack path** — the concrete sequence of steps that realises a threat scenario.

**Attack feasibility** — how achievable the attack path is. Rated here by the **attack-potential method**, which scores five factors explicitly: *elapsed time, specialist expertise, knowledge of the item, window of opportunity, equipment*. Each factor carries a written justification; an unjustified score is a defect the linter flags.

**Risk determination** — impact plus attack feasibility, resolved through a matrix. Computed, never typed. A TARA where an analyst hand-writes "risk = 4" is a spreadsheet with extra steps.

**Risk treatment** — what is done about the risk: avoid, reduce, share, or retain.

**Cybersecurity goal** — a top-level objective that treats a risk.

**Cybersecurity requirement** — a specific, verifiable requirement that satisfies a goal. This is what drives design and test cases, and what supports type approval evidence under **UN R155**.

**CSMS** — Cybersecurity Management System. The organisational process UN R155 requires a manufacturer to operate. This repository is not one and does not simulate one.

---

## Secure boot and root of trust

**Root of trust** — the thing you trust because you have no choice: immutable code and immutable data the chain starts from. Here, BootROM plus OTP fuses.

**OTP fuses** — one-time-programmable memory. Expensive and fixed-width, which is why the *hash* of the root public key goes in the fuses rather than the key itself: a 32-byte digest commits to the key at a fraction of the fuse budget, and the full key rides along in the image where it costs nothing.

**Chain of trust** — each stage verifies the next before transferring control. BootROM → SBL (second-stage bootloader) → application. Break any link and everything after it is untrusted.

**Measured boot** — hashing each stage into a **PCR** (Platform Configuration Register) bank as it loads, producing a record of what actually ran. Distinct from *verified* boot, which decides whether to run it at all. Measured boot enables **attestation**: proving to a remote party what booted.

**SVN** — Security Version Number. Deliberately separate from the marketing version number. It increments only when a fix closes a vulnerability, so the anti-rollback floor does not move every release and benign downgrades stay possible.

**Monotonic counter** — a counter that can only increase, ever. The anti-rollback floor. An image whose SVN sits below the counter is refused *even with a perfectly valid signature from the legitimate signing key* — which is the demonstration at the heart of project `01`.

**HSM** — Hardware Security Module. In automotive terms, an **EVITA**-class security module or an **SHE** module on the ECU. Its defining property: private keys go in and never come out. Code may only ask it to sign, never to hand over the key.

---

## In-vehicle communication

**CAN** — the classic vehicle bus. 8-byte payload, which is why every MAC bit costs a payload bit and why truncation matters so much.

**CAN-FD** — CAN with Flexible Data-rate. Up to 64-byte payloads and a faster data phase. The **DLC** encoding above 8 bytes is *not* linear: values 9–15 map to 12, 16, 20, 24, 32, 48, 64 bytes. Getting that table wrong is instantly visible to anyone in the field.

**LIN** — a cheap single-wire sub-bus for low-speed nodes: door modules, mirrors, seats. It has **no native security** — any node can answer any header. The defence is containment at the gateway, not a fix on the bus.

**Automotive Ethernet** — typically 100BASE-T1 / 1000BASE-T1 on a single twisted pair. Carries the higher-bandwidth traffic.

**SOME/IP** — Scalable service-Oriented MiddlewarE over IP. Service-oriented communication over Automotive Ethernet. **SOME/IP-SD** is its service discovery protocol, and its security-relevant weakness is that an attacker can offer a service already offered and steal its subscribers.

**DoIP** — Diagnostics over IP. Tunnels diagnostic sessions to ECUs on entirely different segments through the gateway, which makes it a bridge from a potentially remote-reachable network into a bus that should not be reachable. Hence the importance of routing activation authentication.

**UDS** — Unified Diagnostic Services (ISO 14229). The diagnostic protocol: session control, security access, read/write memory, request download, transfer data.

**ISO-TP** — ISO 15765-2. The transport layer that reassembles UDS messages larger than a single frame. A reassembler is a parser handling attacker-controlled length fields, which is exactly why it is the fuzzing target in project `06`.

---

## SecOC

**SecOC** — Secure Onboard Communication. The AUTOSAR mechanism for authenticating messages on the in-vehicle bus.

**Authenticator** — the MAC over the message. Here AES-128 **CMAC**, computed over `SecOCDataID || authentic_payload || complete_freshness_value`, big-endian throughout.

**Truncated MAC** — only the leading bits of the MAC go on the wire, because an 8-byte CAN frame has no room for 16 bytes of authenticator. 24 bits is typical: forgery is 1 in 2²⁴ *per attempt*, which makes the interesting question "how many attempts per second does the bus allow, and does the receiver rate-limit?"

**Freshness value (FV)** — a counter binding a message to a point in a sequence. This is what a MAC alone does not provide: a MAC proves *who*, the freshness value proves *when*. Replay a valid MAC an hour later and it is still a valid MAC.

**Truncated freshness value** — only the low bits of the FV are transmitted. The receiver **reconstructs** the full value from its own counter plus the transmitted bits, searching a bounded window of candidates ahead of its last accepted value. Transmitting the full FV would defeat the entire design, and is the first thing a reviewer notices.

**Acceptance window** — how far ahead of its own counter a receiver will search. Bounded, so a bad frame cannot cost unbounded CPU.

**Resynchronisation** — what happens after a receiver resets and loses its counter. Without it, everything fails verification permanently. This is the failure mode that bites people in the field.

---

## Key lifecycle

**Key derivation** — deriving many keys from one master secret via **HKDF** with domain separation, rather than storing millions of independent secrets. Smaller compromise surface, no key database to protect, and rotation becomes a generation bump.

**Provisioning** vs **distribution** — provisioning is a *ceremony*: the ECU proves possession of its device identity key before it receives anything, and returns a signed receipt. Distribution is a copy. The distinction changes the entire production-line threat model.

**AAD** — Additional Authenticated Data on an AEAD wrap. Binding the ECU id, purpose, generation and nonce into the AAD is what stops a provisioning package captured in transit from being replayed at a different ECU.

**Overlap window** — the period during which both the old and the new key are valid during rotation. A fleet is not atomic; vehicles are parked, out of coverage, or mid-drive. Without an overlap you either brick the stragglers or never actually cut over.

**Cryptoperiod** — how long a key may remain in use. Enforced here against an injectable clock so the policy is testable by advancing a fake clock rather than waiting.

**Revocation** — declaring a key untrusted. The interesting part is that it is *not instant*: the authority revokes immediately, but a given ECU learns about it when it next fetches the list. The design questions live in that gap — how long a list stays valid, and whether an ECU with a stale list fails open or closed.

**Hash-chained audit log** — each record commits to its predecessor's digest, so any edit breaks the chain and the verifier can name the exact sequence number that broke. On its own this proves *nobody edited it*. Sign the chain head with an HSM-held key and it becomes attributable as well as detectable — know which one you built.

---

## Firmware validation

**Static analysis** — reasoning about code without running it. `cppcheck`, `clang-tidy`, `flawfinder`. Good at local defects, structurally blind to concurrency properties across tasks.

**Sanitizers** — **ASan** (addresses), **UBSan** (undefined behaviour), **MSan** (uninitialised reads). Runtime instrumentation, so they catch bugs that only exist when the code executes.

**Coverage-guided fuzzing** — libFuzzer and friends, mutating inputs and steering by code coverage. A **protocol dictionary** of valid service IDs and frame types is the difference between a fuzzer stuck at byte one and a fuzzer reaching the state machine — usually orders of magnitude in time-to-first-crash.

**SBOM** — Software Bill of Materials, in CycloneDX or SPDX. Firmware SBOMs are harder than application SBOMs because vendored source and copied headers do not announce themselves to a scanner.

**CERT-C** vs **MISRA C** — both are C coding standards for safety and security. MISRA is a paid standard and full rule checking needs a commercial tool. Open tooling gives CERT-C-oriented analysis. Claiming MISRA compliance after running `cppcheck` is a specific and checkable overstatement.

**Traceability** — every test maps to a security requirement, and every requirement has a test. `make trace` reporting zero unverified requirements and zero orphan tests is what "documented test cases" means to an automotive employer, and it is the part most portfolios skip entirely.
