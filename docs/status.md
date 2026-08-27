# Status

Generated from each project's `ACCEPTANCE.md` and `BUILD_PLAN.md`, so it cannot flatter the repository. A project reads as complete only when every box in its own checklist is ticked.

Regenerate with `make render`; CI fails if this page has drifted.

<!-- labctl:begin totals -->

**6 projects · 56 core build phases (7 optional) · 114 acceptance criteria · 17 met so far.**

<!-- labctl:end totals -->

<!-- labctl:begin readme-status -->

| # | Project | Status | Phases | Acceptance | Language |
|---|---|---|---|---|---|
| `01` | [Secure Boot Chain Simulator](../projects/secure-boot-chain-simulator) | ◼ Built | 8 (+2) | 17/17 | Python |
| `02` | [CAN Bus SecOC Demo](../projects/can-secoc-demo) | ◻ Specified | 9 (+1) | 0/17 | Python |
| `03` | [ECU Key Lifecycle Manager](../projects/ecu-key-lifecycle) | ◻ Specified | 10 (+1) | 0/19 | Python |
| `04` | [ISO/SAE 21434 TARA Workbench](../projects/tara-workbench) | ◻ Specified | 9 (+1) | 0/17 | Python |
| `05` | [In-Vehicle Network Security Lab](../projects/ivn-security-lab) | ◻ Specified | 10 (+1) | 0/22 | Python |
| `06` | [ECU Firmware Security Validation Pipeline](../projects/ecu-firmware-validation) | ◻ Specified | 10 (+1) | 0/22 | C + Python |

<!-- labctl:end readme-status -->

---

## What the statuses mean

| Status | Meaning | Enforced by |
|---|---|---|
| ◻ **Specified** | Specification, build plan and acceptance criteria written. No implementation. | Flagged as stale once any acceptance box is ticked |
| ◐ **Building** | Implementation under way; acceptance criteria not all met. | — |
| ◼ **Built** | Every acceptance criterion in that project's `ACCEPTANCE.md` is met. | Rejected while any box is unchecked |

The two enforcement rules matter more than they look. Together they mean the status column cannot be optimistic: a project cannot be declared done early, and it cannot silently stay marked "not started" once work has begun.

## Phase counts

"Phases" counts core build phases; the number in parentheses is optional phases beyond the definition of done. Optional phases are where the cross-project bridges live — the key lifecycle manager's MAC-key export, the network lab's real-hardware CAN backend — so they are worth more than "optional" suggests. See [portfolio map](./portfolio-map.md).

## Updating

Status lives in `lab.toml`, one field per project. Change it there, run `make render`, and every table in the repository updates together. Details in [tooling](./tooling.md).
