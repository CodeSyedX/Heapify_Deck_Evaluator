# 6. S3-compatible object storage behind a port

Status: accepted · 2026-10-01

## Decision
Decks and derived files live in S3-compatible storage behind an `ObjectStorage` port. Browsers upload directly with presigned URLs; the API verifies size and checksum on completion and never trusts the upload step alone. Local development uses SeaweedFS, because MinIO's community edition was archived in 2026.

## Consequences
Any S3-compatible service works in production. Presigned-request behaviour differs between implementations, so the adapter has an integration test.
