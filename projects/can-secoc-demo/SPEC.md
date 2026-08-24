# SPEC - CAN Bus SecOC Demo

Version 1.0. Source of truth. Deviations get recorded in `docs/decisions.md`.

---

## 1. Purpose

Demonstrate, with running code, why message authentication on CAN needs a **freshness value** and
not just a MAC -- by showing a replay attack land on an unprotected bus and get rejected on a
SecOC-protected one.

In scope: SecOC authenticator generation/verification, freshness value management and
synchronization, three AUTOSAR profiles, classic CAN and CAN FD framing, a replay/forgery attacker,
and quantified overhead.

Out of scope: real ECUs, real hardware CAN interfaces (support them, don't require them), UDS,
the AUTOSAR PduR/CanIf stack proper, key provisioning (that is the sibling project).

---

## 2. Background the implementation must honor

AUTOSAR SecOC appends authentication information to an Authentic I-PDU to produce a Secured I-PDU.
The authenticator is a MAC -- in the standard profiles, **AES-128 CMAC** (NIST SP 800-38B /
RFC 4493) -- computed over:

```
DataToAuthenticator = SecOCDataID || secured_part_of_authentic_IPDU || complete_freshness_value
```

Because a classic CAN frame carries only 8 bytes, both the MAC and the freshness value are
**truncated** on the wire. The receiver rebuilds the complete freshness value from its own
synchronized counter state plus the transmitted least-significant bits, recomputes the MAC over the
full FV, and compares the truncated result.

Standard profiles (all AES-128 CMAC):

| Profile | Name | Truncated FV | Truncated MAC |
|---|---|---|---|
| 1 | `24Bit-CMAC-8Bit-FV` | 8 bits | 24 bits |
| 2 | `24Bit-CMAC-No-FV` | 0 bits | 24 bits |
| 3 | `JASPAR` | 4 bits | 28 bits |

Implement all three. Profile 2 exists in this repo specifically so the demo can show what a
freshness-free profile costs you: it is the configuration where replay still works.

**Verify the profile table and the current AUTOSAR specification revision with a web search before
citing document numbers in the README.** The profile parameters above are stable across releases,
but the release identifier (R23-11, R24-11, etc.) changes annually.

---

## 3. Freshness value model

`src/secoc/freshness.py`. Implement the counter-based construction (not timestamps).

```
complete_freshness_value (64 bits, configurable) =
    [ trip_counter (16b) | reset_counter (24b) | message_counter (24b) ]
```

- **Trip counter** increments on ignition cycle; persisted to disk to model NVM.
- **Reset counter** increments on freshness resynchronization events.
- **Message counter** increments per Data ID per transmission; rolls over into reset counter.
- The transmitted truncated FV is the **N least-significant bits** of the complete FV, where N is
  the profile's `FreshnessValueTruncLength`.

### Receiver reconstruction and the acceptance window

The receiver holds `last_accepted_fv` per Data ID. On receipt of truncated FV bits `t`:

1. Build candidate FVs in `[last_accepted_fv + 1, last_accepted_fv + window]` whose low N bits equal `t`.
2. For each candidate, in ascending order, recompute the MAC. Accept the first match.
3. Cap the number of candidates at `SecOCFreshnessValueVerificationAttempts` (default 4). Exceeding
   it is `FV_WINDOW_EXHAUSTED`.
4. On accept, set `last_accepted_fv` to the matched candidate. **Never** accept a candidate ≤
   `last_accepted_fv` -- that single comparison is the replay defense, and it deserves a comment
   saying so.

### Resynchronization

Model the real-world failure mode: a receiver reset loses counter state and every subsequent frame
fails MAC verification forever. Implement an authenticated sync message (its own Data ID, its own
key, carrying the sender's upper FV bits, itself MAC-protected) plus:
- periodic broadcast every `sync_period_ms`
- a receiver-initiated sync request after `k` consecutive verification failures
- persistence of upper FV bits to NVM on idle

`secoc-demo scenario desync` must show the failure and then the recovery. This scenario is what
distinguishes someone who has read about SecOC from someone who has thought about deploying it.

---

## 4. Frame layout

### Classic CAN (8 bytes) - Profile 1 example
```
byte:  0    1    2    3     4      5    6    7
      [  payload (4B)   ][ FV(1B) ][  MAC (3B)  ]
```
Payload budget is 4 bytes. Make this visible in the demo -- the overhead is the whole reason
truncation exists, and CAN FD is the whole reason SecOC became practical.

### CAN FD (64 bytes)
```
[ payload (up to 56B) ][ FV (1-4B) ][ MAC (3-16B) ]
```
Support an untruncated 16-byte MAC as a `--profile full-cmac` option for comparison.

Provide `secoc-demo overhead --profile all --payload-len N` printing a table of usable payload,
overhead bytes, overhead percentage, and forgery probability per attempt (`2^-mac_bits`) for each
profile on both classic CAN and CAN FD.

---

## 5. Node model

`src/secoc/nodes.py`. Three node types, each a thread or asyncio task on the shared bus:

| Node | Role |
|---|---|
| `SenderECU` | Periodically transmits a signal (default: `BrakePressure`, Data ID `0x101`, 20 ms cycle), SecOC-protected or not per config |
| `ReceiverECU` | Verifies and either actuates (prints the decoded signal) or rejects with a reason code |
| `AttackerNode` | Sniffs all traffic into a capture buffer; can replay, forge, flood, and selectively suppress |

Signals carry semantic meaning so the attack is legible: a replayed `BrakePressure = 0` frame
accepted by the receiver is an obvious safety story; a rejected one is an obvious win.

---

## 6. Attack scenarios (the deliverable)

`secoc-demo run --scenario <name>`. Each prints a narrated timeline and ends with a verdict table.

| Scenario | Setup | Expected result |
|---|---|---|
| `baseline` | No SecOC | Attacker replays a captured frame; receiver **accepts**. Actuator responds to a stale command. |
| `replay` | Profile 1 | Same replay, byte-identical frames; receiver **rejects** `FV_STALE`. Show the FV window that was searched. |
| `no-fv` | Profile 2 | Replay **succeeds** despite a valid MAC. This is the scenario that proves the MAC alone is not enough. |
| `forge-payload` | Profile 1 | Attacker modifies payload, keeps the captured MAC. Rejects `MAC_MISMATCH`. |
| `forge-mac` | Profile 1 | Attacker brute-forces a 24-bit MAC. Report attempts made, acceptance rate, and the analytic expectation (1 in 2^24 per attempt). Compute how long that takes at 500 kbit/s with the configured frame rate and print it. |
| `wrong-key` | Profile 1 | Attacker holds a key for a different Data ID. Rejects `MAC_MISMATCH`. |
| `desync` | Profile 1 | Receiver loses counter state; frames start failing; sync message recovers the link. |
| `dos-suppress` | Profile 1 | Attacker suppresses frames. SecOC does **not** help. Say so explicitly -- authenticity is not availability. |

Every scenario writes `results/<scenario>.jsonl` with per-frame decisions, and
`secoc-demo report` renders a markdown summary plus matplotlib charts (accept/reject rate over
time, per-scenario verdict matrix). Charts are written to `results/` and embedded in the README.

---

## 7. Configuration

YAML, `config/demo.yaml`, validated with `pydantic`:

```yaml
bus:
  interface: virtual        # virtual | socketcan
  channel: secoc-demo       # or vcan0
  bitrate: 500000
  fd: false
secoc:
  profile: 1                # 1 | 2 | 3 | full-cmac
  freshness:
    length_bits: 64
    trunc_bits: 8           # derived from profile; explicit here so it can be broken on purpose
    verification_attempts: 4
    sync_period_ms: 1000
    failures_before_sync_request: 3
  data_ids:
    0x101: { name: BrakePressure, cycle_ms: 20, key_slot: brake_mac_key }
    0x102: { name: VehicleSpeed,  cycle_ms: 50, key_slot: speed_mac_key }
    0x7FF: { name: FvSync,        cycle_ms: 1000, key_slot: sync_mac_key }
keys:
  source: file              # file | env
  path: config/keys.json    # DEMO KEYS ONLY - loud warning on load, and a README line saying so
```

Keys are per-Data-ID, never one bus-wide key. Say why in `docs/decisions.md`: one compromised ECU
should not be able to forge every message on the bus.

---

## 8. CLI surface

```
secoc-demo run --scenario replay [--config config/demo.yaml] [--duration 10]
secoc-demo run --scenario all                  # runs every scenario, writes the full report
secoc-demo overhead --profile all
secoc-demo report [--open]
secoc-demo bus monitor                          # candump-style live view with SecOC decode
secoc-demo kat                                  # runs the RFC 4493 known-answer tests and prints them
secoc-demo bench                                # MAC gen/verify throughput, us per frame, frames/s ceiling
```

`secoc-demo bench` matters: "what does SecOC cost you in CPU on a 20 ms cycle?" is a real interview
question and you should have your own measured number.

---

## 9. Repository layout

```
can-secoc-demo/
├── README.md  pyproject.toml  Makefile
├── config/demo.yaml  config/keys.json.example
├── src/secoc/
│   ├── __init__.py  cli.py
│   ├── cmac.py          # thin wrapper over cryptography CMAC + truncation helpers
│   ├── authenticator.py # DataToAuthenticator construction, generate/verify - NO python-can import
│   ├── freshness.py     # FV manager, window search, sync
│   ├── profiles.py      # the three profiles as frozen dataclasses
│   ├── framing.py       # pack/unpack secured PDU for CAN and CAN FD
│   ├── bus.py           # python-can adapter (virtual | socketcan)
│   ├── nodes.py         # SenderECU, ReceiverECU, AttackerNode
│   ├── scenarios.py     # the eight scenarios
│   ├── reasons.py       # ReasonCode StrEnum
│   └── render.py        # rich live view, report generation
├── tests/
│   ├── test_cmac_kat.py          # RFC 4493 vectors - PHASE 1, before anything else
│   ├── test_authenticator.py     test_freshness_window.py
│   ├── test_framing_property.py  # hypothesis: pack/unpack round-trip, truncation bit-exactness
│   ├── test_scenarios.py         # each scenario's verdict is asserted, not eyeballed
│   └── test_no_can_import.py     # asserts the core never imports python-can
├── scripts/setup_vcan.sh         # Linux: modprobe vcan, ip link add vcan0
├── docs/  results/  .github/workflows/ci.yml
```

---

## 10. Testing requirements

- **RFC 4493 KATs**: the four published AES-128 CMAC test vectors, asserted exactly. Print them in
  `secoc-demo kat` so a reviewer can see the implementation is anchored to a standard.
- **Truncation property test**: for random 16-byte MACs and every profile, the truncated MAC equals
  the most-significant `n` bits, and the truncated FV equals the least-significant `m` bits. Getting
  MSB/LSB backwards is the single most common SecOC implementation bug -- test it explicitly and
  note it in the README.
- **Replay invariant**: for any accepted frame, re-injecting it is rejected. Assert this as a
  property over 200 random frames, not as one example.
- **Window boundary**: a frame with FV exactly `last + window` is accepted; `last + window + 1` is
  rejected; `last` is rejected.
- **Scenario assertions**: `test_scenarios.py` asserts each scenario's expected verdict from SPEC §6.
  If `baseline` ever starts rejecting the replay, the demo is broken and CI must catch it.

---

## 11. Standards mapping for the README

| Implemented | Maps to |
|---|---|
| AES-128 CMAC authenticator | NIST SP 800-38B, RFC 4493 |
| SecOC profiles 1/2/3, truncated MAC + FV, DataToAuthenticator construction | AUTOSAR Specification of Secure Onboard Communication (verify the current release identifier before citing) |
| Freshness value manager, sync, acceptance window | AUTOSAR Freshness Value Manager concept |
| Replay-attack mitigation as a design goal | UN ECE R155 Annex 5 (in-vehicle network threats), ISO/SAE 21434 |
| Per-Data-ID key separation | Key management practice; see the sibling ECU Key Lifecycle Manager project |

---

## 12. Explicit non-goals and honesty requirements

- The README states in the first paragraph that this is a demonstration implementation, not a
  certified SecOC stack, and that OEM SecOC deployments differ in vendor-specific ways.
- Demo keys in the repo are labeled as demo keys in the filename, in the loader warning, and in the README.
- Do not claim conformance to AUTOSAR. Claim that it implements the profiles as publicly specified.
