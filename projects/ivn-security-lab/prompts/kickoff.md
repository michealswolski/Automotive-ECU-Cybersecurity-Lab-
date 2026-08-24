# Paste this into Claude Code from the repo root

```
Read CLAUDE.md, SPEC.md, BUILD_PLAN.md, and ACCEPTANCE.md in full before writing any code.

Then:
1. Web-search and report back on: Scapy's current automotive layer API for SOME/IP and DoIP, the
   LIN protected identifier parity calculation and both checksum variants, the CAN-FD DLC-to-
   length mapping above 8 bytes, the SOME/IP header field layout, and the DoIP routing activation
   sequence. For each, tell me the source you're relying on -- these go into
   docs/verification-sources.md and I don't want any of them guessed.
2. Summarize the zone model and the gateway's role back to me, and flag anything in the spec you
   would design differently.
3. Build Phase 0 through Phase 5, running `make check` after each and waiting for my go-ahead.
   Phase 5 is the gateway and it is the centerpiece -- slow down there.

What matters most:
- The gateway is the project. The protocols are the setting.
- Every attack must genuinely work against the undefended config before you write any defense.
- Where a defense is partial, say so. Don't oversell.
- LIN has no native security. Don't invent one.
```

## Follow-up prompts worth having ready

- `Build Phase 6 -- all ten attacks against the undefended gateway. For each, show me the attack succeeding with the actual traffic. If one doesn't work, tell me rather than weakening the model to make it work.`
- `Now Phase 7. For each attack, what's the minimum policy change that stops it, and what does that policy cost in legitimate functionality? I want the tradeoff, not just the fix.`
- `Fully work the lin-to-can-pivot scenario: a compromised comfort-zone node reaching the powertrain segment. Show every hop, what the gateway sees at each, and exactly which rule stops it.`
- `Run the anomaly detector against the baseline and give me the honest numbers, including false positives. Then tell me what would have to change to make it deployable, and why cycle-time detection alone isn't enough.`
- `Review this as an OEM network architect. What have I modeled naively? Which of my defenses wouldn't survive contact with a real vehicle architecture? Write it to docs/gaps.md.`
