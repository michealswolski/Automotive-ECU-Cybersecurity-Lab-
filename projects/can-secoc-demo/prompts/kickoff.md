# Paste this into Claude Code from the repo root

```
Read CLAUDE.md, SPEC.md, BUILD_PLAN.md, and ACCEPTANCE.md in full before writing any code.

Then:
1. Summarize back to me: the DataToAuthenticator construction, the three profiles' truncation
   parameters, and how the receiver reconstructs the complete freshness value. Flag anything in
   the spec that is ambiguous, wrong, or that you would design differently -- I want that before
   you build.
2. Check the installed python-can and cryptography versions. Web-search the current python-can
   API (interface= vs bustype=, virtual bus semantics) and the current AUTOSAR SecOC release
   identifier. Do not cite a document number you have not verified.
3. Build Phase 0, then Phase 1. Do not go past Phase 1 until the RFC 4493 known-answer tests
   pass -- if the CMAC is wrong, nothing else in this repo means anything. Show me the KAT output.
4. Then continue phase by phase, running `make check` after each and waiting for my go-ahead.

What matters most:
- The replay attack must be a real replay of captured bytes, not a simulated flag.
- baseline accepts the replay, replay rejects it, no-fv accepts it. Those three lines are the
  entire point of the project.
- The SecOC core must not import python-can.
```

## Follow-up prompts worth having ready

- `Run scenario baseline then scenario replay back to back and paste the raw terminal output. This is what I'll show in an interview -- tell me if the narration is clear to someone who has never heard of SecOC.`
- `Write docs/how-secoc-works.md with a worked byte-level example: take one real frame from the demo and walk through Data ID, payload, complete FV, the full 16-byte CMAC, the truncation to 24 bits, and the final 8 bytes on the wire. Show the actual hex.`
- `Run secoc-demo bench and tell me the per-frame MAC verify cost, then compute the maximum sustainable frame rate on a 500 kbit/s bus and how that compares to a 20 ms cycle time.`
- `Implement the desync scenario and make the recovery visible: I want to see the exact frame where verification starts failing and the exact frame where the sync message restores it.`
- `Review this as a hostile reviewer who implements SecOC for an OEM. Where does my implementation differ from what ships in a real vehicle, and which of those differences would embarrass me in an interview? Write it to docs/gaps.md.`
