# Paste this into Claude Code from the repo root

```
Read CLAUDE.md, SPEC.md, BUILD_PLAN.md, and ACCEPTANCE.md in full before writing any code.

Then:
1. Web-search to confirm the ISO/SAE 21434 Clause 15 TARA workflow: the step names and their
   order, the four impact categories and their rating scale, the attack-potential factors, the
   shape of the risk matrix, and the four risk treatment options. Report what you confirmed and
   what you could not. Do not reproduce any text or table from the standard itself -- it is a
   paid document. Anything you cannot verify, we cite by document name and mark our own
   thresholds as project conventions.
2. Summarize the domain model and the traceability chain back to me. Flag anything in the spec
   that is ambiguous or that you would model differently.
3. Build Phases 0 through 6. Run `make check` after each and wait for my go-ahead.

Then STOP before Phase 7 and check in with me. Phase 7 is the worked TARA and it is the actual
deliverable -- I want to shape the item definition with you before you start generating analysis
content, and I want to review the first five threat scenarios before you write the rest.

What matters most:
- Risk is computed, never typed.
- Traceability runs both directions and the linter enforces it.
- No fabricated clause numbers.
```

## Follow-up prompts worth having ready

- `Let's do Phase 7 together. Start with the item definition only: the boundary, the interfaces, the architecture graph, and the assumptions. Show me that before touching assets.`
- `Write the first five threat scenarios with full attack paths and feasibility justifications. Then critique them yourself: which of these would a reviewer at an OEM push back on, and why?`
- `Build the three multi-step attack chains that cross from an external interface to a safety-relevant domain. I want the cellular-to-brake-domain path fully worked, step by step, with the feasibility justified at each hop.`
- `Run tara trace on the five requirements that link to my other repos and paste the output. This is what I want to show in an interview.`
- `Review the whole worked example as a hostile assessor. Where is the analysis thin, where are the justifications hand-wavy, and which risk ratings would you challenge? Write it to docs/self-review.md.`
