# Review: recruitment-2027-01

- Project: Synthetic recruitment intake
- Current period: 2027
- Claims: 3
- Sources: 3
- Errors: 2
- Warnings: 3

## Global checks

- WARNING `EMAIL_PRESENT`: Email-like value at $.batch.claims[1].evidence[1].excerpt
- WARNING `EMAIL_PRESENT`: Email-like value at $.batch.claims[2].evidence[0].excerpt
- WARNING `EMAIL_PRESENT`: Email-like value at $.batch.claims[2].value

## claim-window-stale: Harbor City School / application_window

- Status: `current`
- Value: `{"closes": "2025-11-30"}`
- Evidence relation: `supports`
  - Source ID: `source-official-2026`
  - Source title: 2026 teaching recruitment notice
  - URL: `https://example.invalid/recruitment/2026-notice`
  - Source type: `official_page`
  - Access status: `accessed_body`
  - Applicable period: `2026`
  - Supports fields: `["application_window"]`
  - Published: `2025-08-20`
  - Accessed: `2026-08-30`
  - Locator: application timeline
  - Excerpt: Applications for the 2026 teaching intake closed on 30 November 2025.
- Checks:
  - ERROR `CURRENT_SUPPORT`: Current claim lacks accessed body evidence for the current period

## claim-status-snippet: Harbor City School / program_status

- Status: `current`
- Value: `"open"`
- Evidence relation: `supports`
  - Source ID: `source-search-2027`
  - Source title: Search result for 2027 recruitment
  - URL: `https://example.invalid/search-result`
  - Source type: `search_snippet`
  - Access status: `snippet_only`
  - Applicable period: `2027`
  - Supports fields: `["program_status"]`
  - Published: `None`
  - Accessed: `2026-08-30`
  - Locator: search result snippet
  - Excerpt: Harbor City School 2027 teacher recruitment is now open.
- Evidence relation: `context`
  - Source ID: `source-contact`
  - Source title: School contact page
  - URL: `https://example.invalid/recruitment/contact`
  - Source type: `official_page`
  - Access status: `accessed_body`
  - Applicable period: `evergreen`
  - Supports fields: `["contact"]`
  - Published: `None`
  - Accessed: `2026-08-30`
  - Locator: contact section
  - Excerpt: For general enquiries, write to recruitment@example.org.
- Checks:
  - ERROR `CURRENT_SUPPORT`: Current claim lacks accessed body evidence for the current period

## claim-contact: Harbor City School / contact

- Status: `current`
- Value: `"recruitment@example.org"`
- Evidence relation: `supports`
  - Source ID: `source-contact`
  - Source title: School contact page
  - URL: `https://example.invalid/recruitment/contact`
  - Source type: `official_page`
  - Access status: `accessed_body`
  - Applicable period: `evergreen`
  - Supports fields: `["contact"]`
  - Published: `None`
  - Accessed: `2026-08-30`
  - Locator: contact section
  - Excerpt: For general enquiries, write to recruitment@example.org.
- Checks:
  - No claim-specific issues

## Gaps

### gap-current-not-found

- Target: `harbor-city-school`
- Field: `application_window`
- Type: `low_yield`
- Note: No accessed 2027 notice body was available in this batch.
- Source IDs: `["source-search-2027"]`
  - `source-search-2027`: Search result for 2027 recruitment | search_snippet | snippet_only | period 2027 | supports ["program_status"] | published None | accessed 2026-08-30 | `https://example.invalid/search-result`
