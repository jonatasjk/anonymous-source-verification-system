# Anonymous Source Verification System

## Objective
Build a prototype system that verifies evidence from anonymous sources and generates a public, privacy-preserving certificate with ready-to-use attribution language. The core challenge: how do you prove that a piece of evidence is genuine and has not been tampered with? Anyone can hash a file after creating it. Your system must solve for provenance.

## Sample Data
Scenario: Academic Misconduct Allegation.
A postdoctoral researcher alleges that her principal investigator fabricated data in a published gene therapy paper.
The source has requested full anonymity.

Build and test your prototype against the following evidence package.

- journalist_intake_notes.txt — Journalist’s summary and initial assessment.
- email_chain_vasquez_hargrove.txt — Email correspondence between source and accused.
- recorded_conversation_march_19.mp3 — Audio recording with a corroborating witness.
- data_comparison_memo.txt — Quantitative comparison of raw data vs. published values.
- vasquez_personal_notes.txt — Personal notes kept by the source.

While coding, explain the problem, the solution, and how it works. Show an example certificate. Clear call to action.

Design and prototype a system for handling evidence from anonymous sources. The architecture should address how evidence enters the system, how its authenticity is established, and how it is analyzed. The engine should assess consistency, corroboration, and plausibility across evidence, classify reliability, and return structured output. No sensitive source data should be exposed.

Certificate & Attribution Output. Generate a privacy-preserving certificate (ID, timestamp, confidence score, evidence breakdown) and publication-ready attribution language that journalists can copy directly into their reporting.

Example of attribution:
“The internal review process was bypassed entirely,” said a source verified via our independent certification process.