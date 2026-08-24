# Paste this into Claude Code from the repo root

```
Read CLAUDE.md, SPEC.md, BUILD_PLAN.md, and ACCEPTANCE.md in full before writing any code.

Then:
1. Confirm your understanding by listing the eight demo scenarios and the verification order
   from SPEC section 4 back to me in one short block. Flag anything in the spec that is
   ambiguous, internally inconsistent, or that you think is a bad design decision -- I want the
   pushback before you build, not after.
2. Check the installed version of `cryptography` and probe for ML-DSA support as described in
   CLAUDE.md. Web-search for anything where your training data may be stale (library APIs,
   standard clause numbers, current AUTOSAR/NIST document revisions). Do not assert a clause
   number you have not verified.
3. Execute Phase 0 through Phase 7 of BUILD_PLAN.md, one phase at a time. After each phase, run
   `make check`, report the result, and wait for my go-ahead before the next phase.

Constraints I care about most:
- Negative paths are features. Scenario 3 (valid signature over a stale SVN) is the centerpiece.
- Private keys never leave hsm.py.
- The demo must be readable by an interviewer who has never seen the code.
- Do not invent standards citations.
```

## Follow-up prompts worth having ready

- `Run the full demo and paste the raw output. Then tell me the three questions an interviewer is most likely to ask about it, and where in the code the answer lives.`
- `Write docs/threat-model.md as a STRIDE table anchored on two attack trees: compromised OTA signing server, and physical SPI-flash access. Map each leaf to a control in this repo -- and be explicit about the leaves this project does NOT mitigate.`
- `Add Phase 8 (C reference verifier). Fuzz the parser for 60 seconds and fix anything it finds.`
- `Review your own code as a hostile security reviewer. Where is the verification order exploitable? Where could a length field cause an over-read? Write findings to docs/self-review.md and fix the real ones.`
- `Generate a one-page PDF-ready summary of this project suitable for attaching to a job application: what it does, the architecture, the eight scenarios, and the standards mapping.`
