# The bench path — what software cannot make true

Six projects cover most of an automotive product-security skill set. Five capabilities they cannot cover at all, because those capabilities mean *sitting at a bench with hardware*, and no amount of generated software makes that claim true.

This document is the honest alternative to pretending otherwise: what each gap is, what closing it costs, and what it converts a claim into.

---

## The claim in question

> "Worked through bench-debugging exercises covering CANoe, JTAG, logic analyzers, and oscilloscopes."

That sentence reads, to any automotive hiring manager, as *I have sat at a bench with hardware*. It is a hands-on claim. It belongs in one of three places depending on what actually happened.

**If it genuinely happened** — in a lab course, at an employer, on your own hardware — the claim stays, but it needs specifics. "Traced a CAN fault to a missing termination resistor using a scope and a logic analyzer" is worth ten times "worked through bench-debugging exercises covering…". It is falsifiable, specific, and it survives follow-up.

**If it came from coursework, videos, or a study plan** — it comes out of the experience section. Not because exposure is worthless, but because the sentence as written overstates it, and an interviewer will find the seam in about two questions. Where it can honestly go is a *tool familiarity* line under an explicitly labelled awareness-level heading, never inside a bullet that begins with "Completed." The distinction that matters: "I know what a logic analyzer is for and when I'd reach for one" is true and useful. "I worked through bench-debugging exercises covering logic analyzers" implies you drove one.

**If neither** — the rest of this document is how to make it true, cheaply.

---

## The five gaps

`lab.toml` marks each of these `bench_only = true`, and `labctl validate` fails the build if any project claims one.

| Capability | Roughly what it costs | What it converts |
|---|---|---|
| Physical CAN bus | One USB-CAN adapter | "simulated CAN" → "CAN over a real transceiver" |
| Logic analyzer | One 8-channel USB analyzer | nothing → a real protocol-decode skill |
| JTAG / SWD | One debug probe + a Cortex-M board | "emulator gdbstub" → "on-target debugging" |
| Oscilloscope | The expensive one — defer it | nothing → physical-layer measurement |
| Vector CANoe | Not purchasable — see below | — |

---

## Closing them

### Physical CAN — the highest-value purchase

A USB-CAN adapter that presents as SocketCAN. The CANable family and similar open-hardware adapters are the usual recommendation; check current availability and Linux support before buying.

Plug it into a Linux box, bring up `can0` instead of `vcan0`, and **every CAN project in this repository runs on real hardware over a real transceiver**. The [SecOC demo](../projects/can-secoc-demo) and the [network lab](../projects/ivn-security-lab) both support this — the network lab's final optional phase exists precisely for it. Cheapest possible upgrade from "simulated" to "hardware".

A **second adapter** buys a two-node bus with real termination, which means arbitration, bus-off behaviour and error frames become things you have observed rather than things you have read about. That is where CAN physical-layer questions start getting answered from experience.

### Logic analyzer

A cheap 8-channel USB logic analyzer plus PulseView from the sigrok project decodes CAN, LIN, SPI, I²C and UART. Capture your own bus, decode the frames, and compare them against what your software says it sent. That is a real logic-analyzer skill and it costs about the same as lunch.

### JTAG / SWD

An ST-Link or Black Magic Probe with any cheap Cortex-M dev board. Flash it, halt the core, set a breakpoint, inspect memory.

The specific move worth making: build the [firmware validation project](../projects/ecu-firmware-validation), then port the firmware from the emulator to the real board and catch one of the planted overflows on actual silicon. That converts "emulator gdbstub debugging" into genuine on-target debugging, which is a materially different claim and one nobody can take away from you afterwards.

### Oscilloscope

The expensive one, and the one to skip or defer. A used entry-level scope or a pocket scope will show CAN differential signalling and let you measure bit timing. Worth doing if you find one cheap or get bench access; not worth going into debt for. Be aware that a very cheap scope's bandwidth may not do CAN-FD's faster data phase justice — check before buying.

### CANoe

This one probably cannot be bought. It is expensive licensed Vector software with no hobbyist tier. The options that actually exist:

- A student or evaluation licence, if Vector offers one for your situation. Worst case they say no.
- Access through an employer or a university lab.
- The honest substitute: `can-utils` (`candump`, `cansend`, `cangen`), SavvyCAN for a GUI, `cantools` for DBC decoding, and Wireshark for the Ethernet side. In a learning context that stack does much of what CANoe would be used for.

**Do not list CANoe unless you have actually driven it.** It is specific, expensive, and instantly checkable. Naming a Vector tool you have never opened is one of the fastest ways to lose a room.

---

## Bench access beats bench purchases

Metro Detroit has more automotive bench hardware per square mile than anywhere else on the continent. An hour on someone else's properly equipped bench, with someone who knows it, is worth more than a shelf of adapters.

Worth asking about: whether university labs remain accessible to recent graduates, whether anyone in your professional network can arrange bench time, and whether local meetups or industry groups lead anywhere. The ask is small and specific enough that people say yes to it: *"Can I get an hour on a bench with a CAN setup and a scope?"*

---

## What changes in this repository when a gap closes

Nothing automatic — and that is the point. When one of these becomes true, the change is explicit:

1. Remove `bench_only = true` from that skill in `lab.toml`.
2. Add the skill id to the `covers` list of the project that now demonstrates it.
3. Run `make check`. The validation rule that previously *rejected* the claim now *requires* a project to back it.
4. Write down what you actually did, with specifics, in that project's talking points.

Until step 4 is something you could say out loud to a skeptical interviewer, the gap is not closed.
