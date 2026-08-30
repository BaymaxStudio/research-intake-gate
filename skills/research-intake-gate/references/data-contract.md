# Data contract

## Project

`project.json` defines the stable research scope.

```json
{
  "schemaVersion": "0.1.0",
  "name": "Example intake",
  "currentPeriod": "2027",
  "allowedFields": ["application_window"],
  "targets": [{"id": "example-target", "name": "Example Target"}]
}
```

Target IDs, source IDs, claim IDs, and batch IDs must be unique within their scope. A staged filename must match its `batchId`.

## Staged batch

```json
{
  "schemaVersion": "0.1.0",
  "batchId": "example-2027-01",
  "createdAt": "2026-08-30T00:00:00Z",
  "sources": [
    {
      "id": "source-official",
      "url": "https://example.invalid/notice",
      "title": "Official notice",
      "sourceType": "official_page",
      "supportsFields": ["application_window"],
      "publishedAt": "2026-08-20",
      "accessedAt": "2026-08-30",
      "applicablePeriod": "2027",
      "accessStatus": "accessed_body"
    }
  ],
  "claims": [
    {
      "id": "claim-window",
      "targetId": "example-target",
      "field": "application_window",
      "value": {"closes": "2026-12-15"},
      "status": "current",
      "evidence": [
        {
          "sourceId": "source-official",
          "relation": "supports",
          "excerpt": "Applications close on 15 December 2026.",
          "locator": "Application timeline"
        }
      ]
    }
  ],
  "gaps": []
}
```

Allowed source types are `official_page`, `official_pdf`, `search_snippet`, `third_party`, and `other`. Allowed access states are `accessed_body`, `blocked`, `not_found`, and `snippet_only`. `supportsFields` states which project fields the source body is suitable to prove; a contact page scoped to `contact` cannot support `program_status`. Claim status is `current` or `reference`; the validator applies the strict period rule only to `current`.

## Review decisions

The `review` command creates a template containing `needs_followup` for every claim. A human replaces each value with `accept` or `reject` and writes a reason. `reviewedAt` is supplied by the reviewer.

## Approved batch

The `promote` command writes `approved/<batch-id>.json`. It contains only accepted claims, their referenced sources, and the complete review decision list. Existing approved files are never replaced.

## Diff report

`diff` resolves an ID from `approved/` first, then `staging/`. It compares claims by `targetId::field` and reports added, removed, modified, and status changes in JSON and Markdown.
