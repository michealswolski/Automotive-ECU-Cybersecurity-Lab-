# Building a project

Every project directory in `projects/` is a complete engineering package: the constraints, the specification, the phase order, and the gate. This is how you take one from that state to a working demo.

---

## What is in a project directory

| File | Role |
|---|---|
| `CLAUDE.md` | Standing constraints — the non-negotiables, the engineering standards, the facts to verify before writing code |
| `SPEC.md` | The source of truth. Byte layouts, state machines, reason codes, scenario tables |
| `BUILD_PLAN.md` | Phase order, each phase with its own acceptance criteria |
| `ACCEPTANCE.md` | The definition of done for the whole project |
| `prompts/kickoff.md` | The prompt that starts the build, plus follow-ups |
| `docs/interview-talking-points.md` | How to talk about it once it exists |

The specification comes first on purpose. It is the difference between *"I built a thing"* and *"I engineered a thing to a requirement and can prove it met one"* — and the second sentence is the one that gets asked about.

---

## The loop

```bash
cd projects/secure-boot-chain-simulator
claude                     # then paste prompts/kickoff.md
```

Then, per phase:

1. **Build one phase.** Not two. The phases are sized so that each one produces something you can run.
2. **Run the demo yourself.** Not the tests — the demo. Watch the output.
3. **Check the phase's acceptance criteria.** They are in `BUILD_PLAN.md` under that phase, and they are specific for a reason.
4. **Read the code.** If you cannot explain a file, ask for an explanation of that file before moving on. An interviewer will ask about `authenticator.py`, not about `SPEC.md`.
5. **Commit.** One commit per phase makes the history readable, and a readable history is itself evidence.

Then, when the whole thing is done:

```bash
make check          # from the repo root — validates the repo describes itself accurately
```

Update the project's `status` in `lab.toml` as you go: `specified` → `building` → `built`. The validation rules will not let `built` stand while `ACCEPTANCE.md` still has unchecked boxes, and they will flag a project still marked `specified` once boxes start getting ticked.

---

## The phases that are real gates

Most phases are checkpoints. A few are gates — do not pass them until they genuinely pass, because everything downstream depends on them being right.

| Project | Gate | Why |
|---|---|---|
| [`02` SecOC](../projects/can-secoc-demo) | **Phase 1** — RFC 4493 known-answer tests for AES-CMAC | If the CMAC is wrong, every result in the project is meaningless. All four vectors pass or nothing proceeds. |
| [`03` Key Lifecycle](../projects/ecu-key-lifecycle) | **Phase 1** — the state machine, before any persistence | The state machine *is* the product. Get the transition matrix right and exhaustively tested first. |
| [`04` TARA](../projects/tara-workbench) | **Phase 7** — stop and think before the worked analysis | Fifteen threat scenarios you argued through beat sixty you did not. This one is a stop-and-check-in, not a run-ahead. |
| [`05` IVN](../projects/ivn-security-lab) | **Before phase 1** — verify LIN parity, both LIN checksums, the CAN-FD DLC table, the SOME/IP header, the DoIP handshake | Getting the DLC table wrong is the kind of error an automotive interviewer spots instantly. Verify, record the sources, then write tests with published values. |
| [`06` Firmware](../projects/ecu-firmware-validation) | **Phase 0** — the toolchain and emulator | Cross-toolchain plus emulator plus FreeRTOS is a real fight. A hello-world bare-metal binary must build and print over semihosting before anything else starts. |

---

## Verify, do not recall

Every project's `CLAUDE.md` has a "verify before coding" section, and it exists because library APIs and standard revisions move faster than anyone's memory of them. The recurring traps:

- **`python-can`** — the constructor keyword is `interface=`, not the older `bustype=`. Two `VirtualBus` instances exchange messages only *within one process*.
- **`cryptography`** — ML-DSA availability is version-dependent. Probe for it; gate the post-quantum backend behind a feature flag; never fake a PQ signature.
- **Standards revisions** — check the current NIST SP 800-57 revision, the current AUTOSAR release for the SecOC specification, and any clause number before citing it. Cite by document name when a clause cannot be confirmed.
- **Tooling invocations** — `cppcheck`, `clang-tidy`, `syft`, `grype`, `osv-scanner` all change flags between releases. Confirm before wiring a pipeline around them.

A wrong version number in a README is a small error. A wrong clause number in a TARA is the tell that the citations are decorative.

---

## Two rules that apply to every project

**No hand-rolled cryptography.** Use `cryptography` (pyca) primitives. Do not implement AES, CMAC, SHA-256 or ECDSA yourself. The projects are about *how cryptography is deployed* — key lifecycle, freshness, rollback protection, trust boundaries — which is the harder and more interesting half.

**Negative paths are features, not tests.** A corrupted image, a downgrade attempt, a revoked key, a replayed frame, a desynchronised counter: each gets a dedicated demo scenario, not just a unit test. The rejection, with its reason code and the state that produced it, is the demonstration.

---

## When you are done

Fill in [the project's talking points](../projects/secure-boot-chain-simulator/docs/interview-talking-points.md) with your own numbers from your own run. They ship as scaffolds deliberately — "give your measured number from the brute-force scenario" is a prompt, not a placeholder. A candidate who says "87% coverage on the parsers, and the uncovered branches are the hardware fault handlers I can't reach from the host harness" is credible. One who says "high coverage" is not.

Then re-read [honest claims](./honest-claims.md) and write the sentence you will actually say out loud.
