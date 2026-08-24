# Interview talking points - TARA Workbench

## The 30-second version
"I built a TARA workbench that runs the ISO 21434 Clause 15 workflow as structured data instead of a
spreadsheet, and then used it to produce a complete threat analysis for an OTA telematics gateway.
The part I care about is traceability: I can take any cybersecurity requirement, run one command, and
get the full chain back to the risk, the threat scenario, the damage scenario, and the asset it
protects. Five of those requirements link to actual test cases in my other repos, so the analysis
points at running code."

## Questions you should be able to answer cold

**"Walk me through the TARA steps."**
Item definition, asset identification with damage scenarios, impact rating across safety, financial,
operational and privacy, threat scenario identification, attack path analysis, attack feasibility
rating, risk determination, risk treatment. Know the vocabulary exactly -- calling a damage scenario a
"threat" is the tell.

**"How did you rate attack feasibility?"**
Attack-potential method: elapsed time, specialist expertise, knowledge of the item, window of
opportunity, equipment. Each factor scored with a written justification, summed, and mapped to a
feasibility level. Be upfront that the specific thresholds in your tool are a documented project
convention, since the standard is a paid document -- that honesty reads as maturity, not as a gap.

**"What's the hardest part of a TARA?"**
Not the threats. Keeping the analysis consistent and traceable as the design changes, and writing
damage scenarios that describe consequences to road users rather than to the company. Most TARAs rot
because nobody can tell what changed between revisions -- which is why my tool has a diff command.

**"Where does a TARA output actually go?"**
Cybersecurity goals and requirements that drive design, verification criteria, and test cases, and
evidence supporting type approval under UN R155. Show the trace command.

**"What are the limits of what you built?"**
It's an independent implementation of the publicly described method. No conformance, no certification,
no organizational CSMS behind it, and the scoring thresholds are mine. And a real TARA is done by a
team with domain experts arguing about ratings -- one person's analysis is one person's opinion,
structured.

## Claim discipline

Say: "I implemented the publicly described ISO/SAE 21434 TARA workflow as a tool with enforced
traceability, and produced a complete worked threat analysis for a telematics gateway ECU."

Do not say: that you have performed TARA in a professional CSMS context, that the analysis is
conformant, or that you were part of a type-approval process.
