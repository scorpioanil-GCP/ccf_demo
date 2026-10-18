# CCF SDK Interim License Handoff Guide

Prepared for David Castillo on October 10, 2026, for the planned Tuesday, October 13, 2026 handoff.

This package provides a draft private, no-fee software and limited patent license, an ownership reservation, a delivery record, and source-notice templates. It is a drafting aid for your lawyer and Wells Fargo's authorized legal representative, not an opinion establishing ownership or enforceability. Have counsel review it before execution and delivery. No repository has been changed and no agreement has been sent or accepted.

## What is included

- LICENSE.md: the complete proposed agreement, including Schedule A and signature blocks.
- CCF_WF_Interim_License_DRAFT.docx: the same agreement in editable Word format.
- SOURCE_HEADERS.md: Python, YAML, Markdown, and HTML notice templates and a README notice.

## Proposed terms to review

The following are drafting choices, not previously agreed terms with Wells Fargo:

| Topic | Proposed position |
| --- | --- |
| License duration | 90 calendar days after the last signature; no automatic renewal |
| Price | No fee or royalty |
| Permitted activity | Internal evaluation, development, production use, modification, and extension, including systems supporting customer services |
| Permitted users | Named Wells Fargo entity, specifically listed affiliates, and restricted personnel and contractors acting for them |
| Distribution | No public repository, customer SDK delivery, external sublicensing, or transfer without written permission |
| Patent permission | Limited to controlled, issued claims in the listed application family necessarily practiced by the delivered functionality; no blanket license to future inventions |
| Ownership | Reserve the rights you actually own; no assignment of the original materials or automatic transfer of either party's additions |
| Expiration | Licensed operation must stop, including production use requiring those rights, unless the parties extend or replace the agreement |
| Breach | Written notice and 10 calendar days to cure; unauthorized disclosure must stop promptly |
| Confidentiality | Three years after the term, with trade secrets protected while they qualify; legal and regulatory disclosure exceptions |
| Liability | No support or indemnity; warranty disclaimer; proposed USD 100 aggregate liability cap for you, subject to stated exceptions and applicable law |

If Wells intends continuing production use, agree on an extension or replacement before the 90-day period ends. Do not bury the expiration condition in a source header. This temporary draft does not promise a perpetual free license; any longer-term arrangement should state its duration and permissions expressly.

## Before the Tuesday handoff

1. Ask your patent or IP counsel to confirm the scope you own and can license, including any employment-assignment terms and AI-assisted or third-party content. Wells acknowledging the provisional does not by itself resolve software copyright ownership. The draft does not rewrite existing agreements.
2. Complete Schedule A with the exact Wells Fargo legal entity, any authorized affiliates, patent application identifiers, the extension identifier, and the precise delivered materials. The provisional application number and filing date are not known from this conversation and have not been invented.
3. Create the final private delivery snapshot after adding any notices. Record its full commit SHA in Schedule A outside that snapshot. If using a ZIP, compute its SHA-256 after finalizing it and record that checksum in the signed delivery record. Do not put a file's own final hash inside itself or create a self-referential Git commit requirement.
4. Obtain your signature and that of a Wells Fargo representative authorized to bind the named entity. A developer acknowledging receipt is not necessarily authorized to accept the agreement. Record the effective and expiration dates. The draft deliberately requires signatures rather than assuming a repository download binds Wells Fargo.
5. Include the matching license and README notice with the handoff. Keep the complete signed agreement and delivery record privately. Source comments are helpful but not required in every file. Do not overwrite third-party notices or change signed/content-addressed fixtures just to add a banner.
6. Retain the exact delivered archive or commit, its checksum, and written evidence of receipt. Put an internal reminder ahead of expiry so the parties can complete the longer-term agreement. No reminder has been scheduled by this package.

If signatures are not ready Tuesday, the banner can state your ownership claim, but it does not substitute for acceptance of the proposed contractual protections. Agree on a narrower signed evaluation arrangement or adjust the handoff timing with Wells legal; do not describe this draft as an executed license.

## Specific counsel review points

Confirm the licensor's legal identity and chain of title; whether Wells needs affiliate, contractor, or customer distribution rights; the patent-family description and treatment of continuations; ownership of the employment-related extension; interaction with existing agreements and confidentiality duties; the 90-day term and production cessation; warranty and liability language; and any governing-law or dispute-resolution clause counsel considers appropriate. Neither party's actual ownership or patent claim scope has been independently established here.

## Sources supporting the drafting approach

These sources explain the legal distinctions used in the draft; they are not endorsements of its wording or evidence that its terms will be enforceable in this situation.

- U.S. Copyright Office, Copyright Act chapter 2, sections 201, 202, and 204: authorship and work made for hire, distinction between a copy and copyright ownership, and transfers of copyright ownership. https://www.copyright.gov/title17/92chap2.html
- U.S. Copyright Office, Circular 3, Copyright Notice: notice is generally optional for modern works and identifies a claim of ownership. https://www.copyright.gov/circs/circ03.pdf
- USPTO, Provisional Application for Patent: a provisional application is not examined and does not itself become an issued patent without further steps. https://www.uspto.gov/patents/basics/apply/provisional-application
- USPTO, Managing a patent: a patent provides an exclusionary right, and an improvement may still implicate an earlier patent. https://www.uspto.gov/patents/basics/manage

Sources checked October 10, 2026.
