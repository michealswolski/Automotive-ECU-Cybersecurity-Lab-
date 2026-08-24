# Interview talking points - In-Vehicle Network Security Lab

## The 30-second version
"I built a simulated vehicle network with three protocols -- LIN sub-bus, CAN-FD backbone, and an
Automotive Ethernet segment running SOME/IP and DoIP -- connected by a gateway with a zone-based
firewall. Then I wrote ten attacks and ran each one twice: once against a permissive gateway config,
once against a hardened one. The interesting one is the pivot: compromise a door module on the LIN
bus, and see how far you get toward the brake ECU. Without zone policy, all the way. With it, you
stop at the gateway."

## Questions you should be able to answer cold

**"Why zones instead of per-node rules?"**
Because architectures change and node lists rot. A policy that says "nothing from the comfort zone
reaches the chassis zone without authentication" survives a supplier swapping a door module. A
policy that names the module does not.

**"LIN has no security. So what did you actually do there?"**
Correct -- any node can answer any header, and I didn't invent a fix. The defense is at the gateway:
plausibility checks and cycle-time on values coming out of the LIN segment, and default-deny toward
critical zones. The honest lesson of the LIN scenarios is that you cannot secure that bus, so you
contain it.

**"What's the risk with SOME/IP service discovery?"**
An attacker can offer a service that is already offered and steal the subscribers, or de-associate a
subscriber and reroute its events. Mitigation is source binding and an offer allowlist -- and be
honest that link-layer security alone doesn't stop an attacker who has compromised a legitimate ECU.

**"Why is DoIP interesting from a security standpoint?"**
Because it tunnels diagnostics over IP to ECUs on entirely different segments through the gateway.
It is a bridge from a network you might reach remotely into a bus you shouldn't. That is why routing
activation authentication and a diagnostic firewall matter more than they look.

**"Your anomaly detector -- what's the false-positive rate?"**
Have the real number. Then say what it means: cycle-time detection catches injection that doesn't
match a periodic pattern, and misses an attacker patient enough to match it. It's a layer, not a
solution.

**"What isn't modeled?"**
Physical layer, real bus arbitration and timing, actual 100BASE-T1 behavior. Say it before you're
asked.

## Claim discipline

Say: "I built a simulated multi-protocol in-vehicle network -- LIN, CAN-FD, and Automotive Ethernet
with SOME/IP and DoIP -- with a zone-based gateway firewall, and validated it with ten attack
scenarios run against both permissive and hardened configurations."

Do not say: that you have production experience with these protocols on real vehicle hardware, or
that you've used commercial tooling you haven't. If you later run the CAN segment over a real USB-CAN
adapter, that becomes a separate, true, and much stronger claim -- see `bench-path.md`.
