# Build order

The recommended sequence, and the reasoning behind each position.

<!-- labctl:begin build-order -->

| Order | Project | Why here | Effort |
|:---:|---|---|---|
| 1 | [Secure Boot Chain Simulator](../projects/secure-boot-chain-simulator) | Highest credibility per hour, and it stands alone. | a long weekend |
| 2 | [CAN Bus SecOC Demo](../projects/can-secoc-demo) | The most memorable demo; the authenticator is reused twice later. | a long weekend |
| 3 | [ECU Key Lifecycle Manager](../projects/ecu-key-lifecycle) | Provisions the MAC keys project 02 consumes — build the bridge. | a week of evenings |
| 4 | [ISO/SAE 21434 TARA Workbench](../projects/tara-workbench) | Needs real requirements to point at, so it wants the first three built. | a week of evenings |
| 5 | [In-Vehicle Network Security Lab](../projects/ivn-security-lab) | Reuses the SecOC enforcement point; building CAN-FD twice is waste. | a week of evenings |
| 6 | [ECU Firmware Security Validation Pipeline](../projects/ecu-firmware-validation) | The most expensive by far. Do it when the rest are shipping. | two weeks of evenings |

<!-- labctl:end build-order -->

Effort figures assume evenings, not full days, and assume you are reading the code as it is written rather than accepting it. If you cannot explain a file, ask for an explanation of that file before moving on — an interviewer will ask about the code, not the specification.

---

## Why this order

### 1 · Secure Boot Chain Simulator — start here

Highest credibility per hour of any project in the set, and it depends on nothing.

Secure boot is the topic most likely to come up in an automotive product-security interview, the rollback-protection demo is genuinely uncommon in portfolios, and the project is self-contained: no protocol simulation, no emulator, no cross-toolchain. Nine phases and a working demo.

It is also the project with the clearest link to prior professional work — internship research covering chain-of-trust verification and TPM-based attestation maps directly onto what this builds. "I researched this, then I built something I can demonstrate" is a stronger sentence than either half alone.

### 2 · CAN Bus SecOC Demo — the demo people remember

Two reasons for second place.

The **memorable demo**: the same replay attack, run twice, against an unprotected bus and a SecOC-protected one. Identical bytes. Different outcome, with the rejection reason and the searched freshness window printed on screen. That is a ninety-second demonstration that answers "why isn't a MAC enough?" better than any explanation.

The **reuse**: this project's authenticator becomes the gateway's SecOC enforcement point in project `05`, and the keys it consumes come from project `03`. Building it early means the later projects have something real to plug into rather than a stub.

> **Do not let phase 1 slide.** Phase 1 is the RFC 4493 known-answer tests for AES-CMAC. If the CMAC is wrong, every result downstream in the project is meaningless. That phase is a gate, not a checkpoint.

### 3 · ECU Key Lifecycle Manager — and build the bridge

Third because it completes the pair. Its optional final phase includes an export bridge that provisions the MAC keys the SecOC project consumes, and that hour of work is what turns two demos into one system.

The project's own thesis is worth internalising because it is also the answer to a common interview question: *most engineers can name the algorithms; far fewer can describe what happens to a key between the day it is generated and the day the vehicle is scrapped.* That gap is the whole project.

> **Do phase 1 before touching a database.** The lifecycle state machine is the product. Get the transition matrix right and exhaustively tested — including every illegal edge — before persistence exists. A lifecycle modelled as a status string is a CRUD app with extra steps.

### 4 · TARA Workbench — once there is something to point at

The TARA workbench covers the most résumé ground of any project here, and it is the connective tissue for the whole portfolio. So why fourth?

Because its value is the **worked example**, and the worked example is dramatically stronger when its requirements trace to real test cases in repositories that exist. A TARA whose requirements point at running code is an artefact. A TARA whose requirements point at nothing is a schema.

> **Stop before phase 7 and think.** Phase 7 is the worked analysis and it is the real work. Fifteen threat scenarios you argued through beat sixty you did not. Unsupervised generation here produces filler you cannot defend at a table.

### 5 · In-Vehicle Network Security Lab — after SecOC, not before

Explicitly after project `02`. The gateway's SecOC enforcement point reuses that work, and building CAN-FD twice is a wasted week.

This is also the project that covers the protocol breadth the first three leave open — LIN, Automotive Ethernet, CAN-FD — plus UDS and ISO-TP, which you want anyway.

> **Verify the protocol details before writing code.** LIN's PID parity and both checksum variants, the CAN-FD DLC table above 8 bytes (it is not linear), the SOME/IP header layout, and the DoIP routing activation sequence. Getting the DLC table wrong is exactly the kind of error an automotive interviewer spots instantly. Verify, cite the source, then write a unit test with published values.

### 6 · Firmware Validation Pipeline — last, and honestly the hardest

The most expensive project by a wide margin, and the one with a phase 0 that can genuinely fight you: cross-toolchain, plus emulator, plus FreeRTOS, plus a fuzzing harness, before a line of security code gets written.

The payoff is that it is the only project that puts real compiled C and a real RTOS on the table with something to show, and its tool-comparison matrix — which tool caught which planted bug, and which bug nothing caught — is the single most valuable artefact in the portfolio for a firmware-security conversation.

Do it when the other five are shipping and you have the appetite for a fight with a toolchain.

---

## If you only have one weekend

Build project `01`. It stands alone, it produces a demo in under twenty seconds of runtime, and it is the topic most likely to come up.

## If you have three weekends

`01`, `02`, and the bridge from `03`. Two projects that plug into each other beat three that do not, and the pair covers secure boot, applied cryptography, CAN, and key management — the four things most likely to be asked about.

## If someone asks which one to read first

Send them to [`01`](../projects/secure-boot-chain-simulator) and tell them to run the rollback scenario.
