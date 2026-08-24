# Interview talking points - ECU Firmware Security Validation Pipeline

## The 30-second version
"I wrote FreeRTOS firmware in C for an emulated Cortex-M -- a UDS diagnostic server behind an ISO-TP
reassembler -- and planted eight documented vulnerabilities in it. Then I built a validation pipeline
around it: static analysis, sanitizers, coverage-guided fuzzing, SBOM and CVE scanning, and a test
suite traced to security requirements. The output I actually care about is the matrix showing which
tool caught which bug. One of the eight nothing caught -- a TOCTOU on a security-access flag across
two tasks. That's the one I talk about."

## Questions you should be able to answer cold

**"Which bugs did static analysis miss, and why?"**
Have specifics. The use-after-free across an error path, because the static tools couldn't follow the
lifetime through the branch. The TOCTOU, because it's a concurrency property across tasks, not a
property of one function. Static analysis reasons about code; some bugs only exist at runtime or
across threads.

**"How long did the fuzzer take to find each one?"**
Have real numbers. Then talk about the dictionary: a structured protocol fuzzer without a dictionary
of valid service IDs and frame types spends its budget generating garbage the parser rejects at byte
one. With one, it gets past the front door and into the state machine. That difference is usually
orders of magnitude.

**"Why fuzz the parser and not the whole firmware?"**
Because the parser is the attack surface reachable from the CAN bus, and because it compiles for the
host, which means the fuzzer runs at native speed instead of emulator speed. Same source, both
targets — that's the design constraint that makes it valid.

**"What's your coverage?"**
Give the real number, including where coverage is low and why. A candidate who says "87% on the
parsers, and the uncovered branches are the hardware fault handlers I can't reach from the host
harness" is credible. One who says "high coverage" is not.

**"Did you check MISRA?"**
No — and know why. MISRA is a paid standard and full rule checking needs a commercial tool. What you
ran is CERT-C-oriented static analysis with open tooling. Being precise here is a signal in itself;
plenty of people claim MISRA when they've run cppcheck.

**"What about supply chain?"**
SBOM in CycloneDX from the actual build, scanned against a vulnerability database. Note the real
problem: firmware SBOMs are harder than application SBOMs because vendored source and copied headers
don't announce themselves to a scanner.

**"What isn't real here?"**
It's an emulator. No peripheral timing, no transceiver, no electrical layer, no real flash wear. The
software bugs are real bugs and the tooling findings are real findings; the hardware is not.

## Claim discipline

Say: "I wrote FreeRTOS-based ECU firmware in C for an emulated Cortex-M target with a UDS/ISO-TP
diagnostic stack, planted and documented eight vulnerability classes, and built a validation pipeline
using static analysis, sanitizers, coverage-guided fuzzing, and SBOM/CVE scanning, with tests traced
to security requirements."

Do not say: that you have production embedded firmware shipping experience, that you validated
MISRA compliance, or that you did hardware bring-up. And if someone asks whether you've debugged over
JTAG, the honest answer is what you actually did -- emulator gdbstub debugging is real skill, and
naming it accurately costs you nothing while claiming JTAG you haven't done costs you everything.
