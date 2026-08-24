# ACCEPTANCE - the definition of done

## Hard gates
- [ ] `make check` green: ruff, `mypy --strict src/`, pytest ≥85% on `src/tara`.
- [ ] `tara lint examples/telematics-gateway` exits 0, enforced in CI.
- [ ] `tara report --format html` produces a standalone readable document.

## Method gates
- [ ] Risk values are computed from impact and feasibility. No API sets a risk value directly.
- [ ] Swapping `config/risk_matrix.yaml` changes results with zero code changes.
- [ ] Every feasibility factor and every impact rating in the worked example carries a written
      justification. No placeholders, no "TBD", no empty strings.
- [ ] Every attack path step traverses an interface that exists in the item definition.
- [ ] `tara trace` works in both directions and `tara orphans` returns empty on the worked example.

## Worked-example gates
- [ ] Meets the minimum scope in SPEC §6.
- [ ] At least three multi-step attack chains cross a trust boundary from an external interface to a
      safety-relevant domain.
- [ ] All six STRIDE categories represented.
- [ ] At least five requirements carry `Claim` evidence links to the other portfolio repos.
- [ ] Damage scenarios describe consequences to road users, not to the organization.

## Honesty gates
- [ ] No text, table, or figure from the paid standard is reproduced anywhere in the repo.
- [ ] Scoring tables are labeled as project conventions in `docs/method.md`.
- [ ] README states plainly that this is not conformant or certified.
- [ ] Every clause number cited was verified; anything unverified is cited by document name only.
