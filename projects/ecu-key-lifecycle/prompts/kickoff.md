# Paste this into Claude Code from the repo root

```
Read CLAUDE.md, SPEC.md, BUILD_PLAN.md, and ACCEPTANCE.md in full before writing any code.

Then:
1. Draw the lifecycle state machine back to me as a transition table (from-state, event,
   to-state) and list the nine steps of the provisioning ceremony. Flag anything in the spec
   that is ambiguous, internally inconsistent, or that you would design differently -- I want
   that pushback before you build.
2. Verify by web search: the current NIST SP 800-57 Part 1 revision and its cryptoperiod
   guidance, the scope of SP 800-130, and whether the installed `cryptography` version exposes
   ML-DSA. Do not assert a clause number you have not verified -- cite by document name instead.
3. Build Phase 0, then Phase 1. Phase 1 is the pure state machine with no persistence; generate
   the illegal-transition test set programmatically so no edge is missed. Show me the transition
   matrix coverage before moving on.
4. Continue phase by phase, running `make check` after each and waiting for my go-ahead.

What matters most:
- The lifecycle is the product. Anyone can call AES; the state machine, the overlap window, and
  the revocation divergence are what make this worth showing.
- No API anywhere returns key material. Storage exposes use(), never get_key().
- The audit chain must catch tampering and name the record.
```

## Follow-up prompts worth having ready

- `Run ekl demo and paste the raw output. Then tell me which scenario is the most impressive to a hiring manager and whether the narration makes that obvious.`
- `Write docs/lifecycle.md: for each state, what it corresponds to physically on a vehicle (line-end programming, dealer reflash, OTA campaign, scrappage) and the specific failure that happens when a program gets that state wrong.`
- `Implement the offline-fleet rotation scenario properly. I want to see the partial state: how many ECUs on gen N, how many on gen N+1, how many unreachable, and what happens at cutover to the stragglers.`
- `Show me the revocation divergence window concretely: the KA has revoked the key, one ECU has fetched the new CRL and one has not. What can the un-updated ECU still do, and for how long?`
- `Review this as a hostile reviewer who runs key management for an OEM. What have I modeled naively? Write it to docs/gaps.md and be specific.`
- `Add the interop bridge to my CAN SecOC project: export a provisioned secoc-mac key in that project's key file format, and write the two commands that demonstrate the two repos composing.`
