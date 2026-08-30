# Security policy

## Supported version

Security fixes are applied to the latest release.

## Report a vulnerability

Open a private security advisory in this GitHub repository. Do not include credentials, private datasets, or personal identifiers in a public issue.

## Data boundary

The core CLI is local and makes no network requests. Imported pages and files are treated as untrusted data. Credential-like fields and values block validation; email addresses, phone numbers, and long excerpts produce warnings. The tool does not delete source files or automatically approve research claims.
