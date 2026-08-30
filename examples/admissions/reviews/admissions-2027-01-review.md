# Review: admissions-2027-01

- Project: Synthetic admissions intake
- Current period: 2027
- Claims: 2
- Sources: 4
- Errors: 1
- Warnings: 0

## Global checks

- No global issues

## claim-application-window: Northbridge University / application_window

- Status: `current`
- Value: `{"closes": "2026-12-15", "opens": "2026-10-01"}`
- Evidence relation: `supports`
  - Source ID: `source-official-2027`
  - Source title: 2027 doctoral admissions notice
  - URL: `https://example.invalid/admissions/2027-notice`
  - Source type: `official_page`
  - Access status: `accessed_body`
  - Applicable period: `2027`
  - Supports fields: `["application_window", "program_status"]`
  - Published: `2026-08-20`
  - Accessed: `2026-08-30`
  - Locator: application timeline
  - Excerpt: Applications for the 2027 doctoral intake run from 1 October to 15 December 2026.
- Checks:
  - No claim-specific issues

## claim-program-status: Northbridge University / program_status

- Status: `current`
- Value: `"open"`
- Evidence relation: `supports`
  - Source ID: `source-official-2027`
  - Source title: 2027 doctoral admissions notice
  - URL: `https://example.invalid/admissions/2027-notice`
  - Source type: `official_page`
  - Access status: `accessed_body`
  - Applicable period: `2027`
  - Supports fields: `["application_window", "program_status"]`
  - Published: `2026-08-20`
  - Accessed: `2026-08-30`
  - Locator: opening paragraph
  - Excerpt: The 2027 doctoral intake is open for applications.
- Evidence relation: `contradicts`
  - Source ID: `source-department-pause`
  - Source title: Department programme notice
  - URL: `https://example.invalid/admissions/department-notice`
  - Source type: `official_page`
  - Access status: `accessed_body`
  - Applicable period: `2027`
  - Supports fields: `["program_status"]`
  - Published: `2026-08-27`
  - Accessed: `2026-08-30`
  - Locator: department notice
  - Excerpt: The department has paused its 2027 doctoral intake pending programme review.
- Checks:
  - ERROR `CLAIM_CONFLICT`: Claim contains supporting and contradicting evidence

## Gaps

### gap-contact-blocked

- Target: `northbridge-university`
- Field: `contact`
- Type: `blocked`
- Note: The programme contact page could not be accessed; no contact value was inferred.
- Source IDs: `["source-contact-blocked"]`
  - `source-contact-blocked`: Programme contact page | official_page | blocked | period evergreen | supports ["contact"] | published None | accessed 2026-08-30 | `https://example.invalid/admissions/contact`
### gap-archive-low-yield

- Target: `northbridge-university`
- Field: `program_status`
- Type: `low_yield`
- Note: The archive index exposed titles but no usable programme-level status evidence.
- Source IDs: `["source-archive-index"]`
  - `source-archive-index`: Admissions archive index | official_page | accessed_body | period evergreen | supports [] | published None | accessed 2026-08-30 | `https://example.invalid/admissions/archive`
