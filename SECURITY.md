# Security policy

## What this repository is

A portfolio of **simulated** automotive security projects. Nothing here is production software, none of it runs on a vehicle, and none of it should be deployed anywhere that matters.

Specifically:

- The cryptography is used, not implemented — `cryptography` (pyca) primitives throughout — but the *protocols built on top of it* are learning implementations that have had no independent review.
- The simulated HSMs are Python objects. They provide no hardware guarantee of any kind.
- The [firmware validation project](./projects/ecu-firmware-validation) contains **deliberately planted, documented vulnerabilities**. That is its entire purpose. Every one lives in `docs/vulns/VULN-nnn.md` with its CWE, the exact source line, and the fix. Do not reuse that firmware for anything.

## Reporting a problem

If you find a genuine security-relevant defect — a cryptographic mistake, an unsafe pattern that would mislead someone learning from this code, or a planted vulnerability that is reachable in a way the documentation does not describe — please open an issue. Public disclosure is appropriate here; there is nothing deployed to protect.

If you would rather not open a public issue, reach out through [LinkedIn](https://www.linkedin.com/in/michealwolski).

## What is out of scope

- The planted vulnerabilities in project `06`, when they behave as documented.
- The absence of hardware guarantees in the simulated HSM and OTP fuse models.
- Any claim that these implementations are conformant, certified or production-ready. They are not, and [the README says so above the fold](./README.md#read-this-part-first).

## Secrets

No real key material belongs in this repository, ever. `.gitignore` blocks the usual extensions, and any key that appears in a test or demo is generated at runtime or is an explicitly published test vector — RFC 4493's AES-CMAC vectors, for example.

If a real credential ever lands here, treat it as compromised, rotate it, and open an issue so the history can be dealt with.
