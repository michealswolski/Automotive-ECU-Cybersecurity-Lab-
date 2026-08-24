# Corrections — ISO/SAE 21434 TARA Workbench

Apply these while building. Full reasoning and provenance: [`docs/spec-corrections.md`](../../docs/spec-corrections.md). Editions to cite: [`docs/standards-register.md`](../../docs/standards-register.md).

## Must fix

- [ ] **ISO/SAE 21434:2021 is still the current edition.** It entered ISO systematic review in July 2026; a second edition is expected to start development on a roughly three-year timeline. Say review has begun — do not imply a revision exists.
- [ ] **CAL is informative, not normative** in 21434:2021 (Annex E). The workbench must treat it as optional, and the README must not present it as required.
- [ ] **Attack feasibility has three approaches in Clause 15**, not one: attack-potential-based, CVSS-based, and attack-vector-based. Support all three, or at minimum name them and say which you implemented.

## Add — the forward-looking differentiator

- [ ] **ISO/SAE 8475 (CAL and TAF)** is at final approval as a PAS with publication expected imminently. It makes CAL **prescriptive** and redefines the levels as **Basic / Intermediate / Advanced**, replacing the informative CAL1–CAL4. Add support as a forward-looking feature, and add **TAF (Targeted Attack Feasibility)** as a design-target attribute distinct from descriptive attack feasibility.
- [ ] Reference the alternative TARA methods so a reader knows the method was chosen rather than assumed: HEAVENS and HEAVENS 2.0, EVITA (severity × attack probability), SAHARA (safety + security), ETSI TVRA. HEAVENS 2.0 and attack-potential are the most common in ISO 21434 practice.
- [ ] Know the competitive landscape and say where you sit: commercial — itemis SECURE, ThreatGet, Ansys medini analyze; open — Microsoft Threat Modeling Tool, OWASP Threat Dragon, pytm, threagile, OVVL, taralizer. Most open tools are generic STRIDE/DFD threat modelling; **very few do a full 21434 TARA with attack-potential feasibility, S-F-O-P impact and 1–5 risk determination.** That gap is the value proposition — lead with bidirectional traceability, the linter, and the 21434-native data model.

## Soften

- [ ] Do not present CAL as normative or required. It is informative in 21434 and only becomes prescriptive under ISO/SAE 8475.
- [ ] The standard is paywalled. Cite public secondary sources for the tables rather than reproducing copyrighted matrices, and note the paywall explicitly.

## Confirmed correct — do not change

Clause 15 is the TARA clause. The step set matches the standard's methodology. Four impact categories (safety, financial, operational, privacy) and risk values 1–5 are correct. The attack-potential factors — elapsed time, expertise, knowledge of the item/component, window of opportunity, equipment — are correct. The four risk-treatment options (avoid/remove, reduce/mitigate, share/transfer, retain/accept) are correct.

## Cite

ISO/SAE 21434:2021 Clause 15 · ISO/SAE PAS 8475 · UN R155
