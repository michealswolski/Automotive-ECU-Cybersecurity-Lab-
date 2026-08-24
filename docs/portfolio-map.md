# Portfolio map

How the six projects fit together, and why that matters more than any one of them.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/portfolio-map.svg">
  <source media="(prefers-color-scheme: light)" srcset="../assets/portfolio-map-light.svg">
  <img src="../assets/portfolio-map.svg" width="100%" alt="Portfolio map. Four bands: analysis, ECU, network, key material. The TARA workbench emits requirement identifiers the projects below trace their tests to; the SecOC authenticator is reused as the in-vehicle network gateway's enforcement point; the key lifecycle manager provisions the MAC keys SecOC consumes." />
</picture>

---

## The argument

Six unrelated repositories demonstrate six things. Six that hand off to each other demonstrate that you can hold a system in your head — which is the thing an automotive product-security role actually needs and the thing a portfolio of disconnected demos never shows.

So the projects are arranged in four bands, and the bands are ordered so that every hand-off is between neighbours.

| Band | Projects | What it owns |
|---|---|---|
| **Analysis** | `04` TARA Workbench | What are we protecting, from whom, and how badly does it matter |
| **ECU** | `01` Secure Boot · `06` Firmware Validation | Is the code running on this ECU the code we intended, and is it any good |
| **Network** | `05` IVN Security Lab · `02` SecOC Demo | Can ECUs trust what they receive, and can an attacker cross a boundary |
| **Key material** | `03` Key Lifecycle Manager | Where the keys everything above depends on come from, and where they go |

---

## The three hand-offs

Only three edges are drawn on the map, and each one is a hand-off the build specifications actually define. There are no speculative arrows — a diagram claiming an integration the repository does not have is the same defect as a résumé line claiming a tool you have not driven.

### Requirements: `04` → everything below

The TARA workbench's output is not a report. It is a set of cybersecurity goals and requirements with stable identifiers, and every requirement traces bidirectionally: down to the test cases that verify it, up to the risk, threat scenario, damage scenario and asset that motivated it.

`tara trace REQ-014` prints that chain. `tara orphans` finds anything unlinked. Bidirectional traceability is what an auditor actually checks and what most portfolio TARAs completely lack.

The firmware validation pipeline consumes this directly: its test IDs map to TARA requirement IDs, and `make trace` reports zero unverified requirements and zero orphan tests. That is what "documented test cases" means to an automotive employer.

### Authenticator: `02` → `05`

The gateway in the network lab needs a SecOC enforcement point — the place where a frame crossing a zone boundary gets its authenticator checked. That is the SecOC project's authenticator, reused rather than reimplemented.

This is why the SecOC project's core (`authenticator.py`, `freshness.py`) is specified to have **zero dependency on `python-can`**. It operates on bytes. The bus layer is a thin adapter. That design decision is what makes the reuse possible, and it is the kind of boundary an interviewer will respect if you can explain why you drew it there.

### Key material: `03` → `02`

The SecOC demo needs AES-128 CMAC keys, one per Data ID. Where do they come from?

In most portfolio projects, from a hardcoded constant at the top of a file. Here, from the key lifecycle manager: generated in a simulated backend HSM, derived with HKDF using per-generation domain separation, and provisioned to a specific ECU through a challenge-response ceremony whose AES-GCM AAD binds the package to that ECU alone. A package captured in transit and replayed at a different ECU fails authentication.

That bridge is the key lifecycle project's final optional phase, and it is worth the hour it takes. It turns two demos into one system.

---

## Reading order for someone evaluating this

If you have five minutes and want the strongest signal, this is the order:

1. **[`01` Secure Boot Chain Simulator](../projects/secure-boot-chain-simulator)** — run the demo. The rollback scenario shows a *valid signature from the legitimate key* being refused because the security version number sits behind the monotonic counter. Most people cannot demonstrate that distinction.
2. **[`02` CAN Bus SecOC Demo](../projects/can-secoc-demo)** — run the replay scenario twice. Same captured bytes, replayed byte-identical. Unprotected: the receiver actuates on a stale brake command. Protected: rejected, with the freshness window printed.
3. **[`04` TARA Workbench](../projects/tara-workbench)** — read the worked telematics-gateway analysis, then run `tara trace` on one of its requirements and follow it into a test case in project `01` or `06`.

Everything else is depth on those three ideas: `03` is where the keys in `02` come from, `05` is what happens when an attacker is already inside the network `02` protects, and `06` is whether the code implementing any of it is actually sound.

---

## What is deliberately *not* connected

Worth naming, because an obvious-looking edge that is missing usually means someone thought about it:

- **`01` Secure Boot does not consume keys from `03`.** The boot chain's HSM holds firmware *signing* keys, which live in a different trust domain from the per-ECU MAC keys the lifecycle manager provisions. Wiring them together would be a nice-looking arrow and a wrong one.
- **`06` Firmware Validation does not run `02`'s SecOC stack.** The firmware's attack surface is its UDS/ISO-TP parser, which is what the fuzzer targets. Adding SecOC to it would widen the project without strengthening its claim.
- **`05` does not invent security for LIN.** LIN has none — any node can answer any header. The defence is containment at the gateway, and the repository says that plainly instead of inventing a fix.

---

## Where to go next

- [Build order](./build-order.md) — why each project sits where it does in the sequence
- [Building a project](./building-a-project.md) — taking one from specification to working demo
- [Capability coverage](./skills-coverage.md) — the full capability-by-project matrix
