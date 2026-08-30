# Evidence rules

## Source access is evidence state

`accessed_body` means the relevant page or document body was actually available. `snippet_only`, `blocked`, and `not_found` describe collection outcomes; they are not weaker synonyms for accessed evidence.

- Use `search_snippet` or `snippet_only` to record discovery, not to support a current claim.
- Keep a blocked source as `blocked`. Do not turn access failure into `not_found`.
- Use `not_found` only after an accessible source was checked and the expected information was absent.

## Applicable periods

A source can support a `current` claim only when `applicablePeriod` equals `project.currentPeriod` or is `evergreen`. Older material can remain as a `reference` claim but must not be relabeled as current.

Each source also declares `supportsFields`. This is a semantic scope, not a list of words present on the page. For example, a general contact page can support `contact` but cannot by itself prove that a recruitment programme is open.

## Claim and evidence separation

Every claim has a target, field, value, status, and evidence list. Evidence items point to source IDs and state one relation:

- `supports`: the excerpt directly supports the value;
- `contradicts`: the excerpt conflicts with the value or another source;
- `context`: useful background that does not prove the value.

Use short excerpts and a locator that helps a reviewer find the relevant section. Do not copy full pages.

## Gaps are first-class records

Use gaps instead of invented values:

- `not_found`: accessible material was checked but the requested field was absent;
- `blocked`: the relevant body could not be accessed;
- `low_yield`: collection succeeded but returned little usable evidence;
- `conflict`: credible sources disagree;
- `pending`: research or review remains open.

## Human decision boundary

The review dossier is evidence for a decision, not the decision itself. Only a person changes each entry in `reviews/<batch-id>-decisions.json` from `needs_followup` to `accept` or `reject` and provides a reason. Rejected claims are excluded from approved data. Accepted claims with blocking errors cannot be promoted.
