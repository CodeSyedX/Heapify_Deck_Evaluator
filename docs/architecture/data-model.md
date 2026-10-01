# Data model

Status: accepted · 2026-10-01. PostgreSQL 18 with pgvector. One Alembic history in `db/migrations`.

## Conventions

- Primary keys are UUIDv7, generated in the application.
- Timestamps are `timestamptz`, named `*_at`, set by the application clock.
- Every tenant-owned table has `tenant_id uuid not null`, a forced RLS policy `tenant_isolation`, and `tenant_id` as the first column of its indexes.
- Parents expose `unique (tenant_id, id)`; children reference `(tenant_id, parent_id)` so a row cannot point across tenants.
- Enumerations are `text` with a check constraint, so adding a value is a cheap migration.
- Immutable tables (`rubric_versions`, `credit_ledger`, `audit_log`, `pipeline_events`) grant the runtime role `insert` and `select` only.

## Roles

| Role | Use |
|---|---|
| `app_owner` | Owns tables and runs migrations. Never used at runtime. |
| `app_rw` | API and worker. `NOBYPASSRLS`, DML grants only. |
| `app_admin` | `BYPASSRLS`. Named cross-tenant jobs only. |

## Global tables (no RLS)

| Table | Columns |
|---|---|
| `users` | `id`, `email` (unique, lower-cased), `display_name`, `adult_declared_at`, `created_at`, `deleted_at` |
| `user_identities` | `issuer`, `subject` (PK together), `user_id` |
| `tenants` | `id`, `kind` (`personal`, `organisation`), `name`, `slug` (unique), `plan_code`, `retention_days`, `created_at`, `deleted_at` |

`memberships` is tenant-scoped but must be readable when resolving which tenants a user belongs to; its policy also admits rows where `user_id` matches the transaction-local `app.user_id`.

## Tenant-owned tables

### Tenancy

| Table | Columns |
|---|---|
| `memberships` | `tenant_id`, `user_id` (PK together), `role`, `created_at` |
| `invitations` | `id`, `tenant_id`, `email`, `role`, `token_hash`, `invited_by`, `expires_at`, `accepted_at`, `created_at` |

### Events and rubrics

| Table | Columns |
|---|---|
| `rubrics` | `id`, `tenant_id`, `name`, `created_by`, `created_at` |
| `rubric_versions` | `id`, `tenant_id`, `rubric_id`, `version` (int), `definition` (jsonb), `content_hash`, `created_by`, `created_at`; unique `(tenant_id, rubric_id, version)` |
| `events` | `id`, `tenant_id`, `name`, `status` (`draft`, `open`, `closed`), `rubric_version_id`, `scoring_profile` (jsonb), `shortlist_size`, `created_by`, `created_at`, `closed_at` |

A personal workspace has one implicit event so that single-deck evaluation and organiser screening share one code path.

### Submissions

| Table | Columns |
|---|---|
| `submissions` | `id`, `tenant_id`, `event_id`, `team_name`, `external_ref`, `submitted_by`, `created_at`, `deleted_at` |
| `uploads` | `id`, `tenant_id`, `submission_id`, `object_key`, `filename`, `declared_content_type`, `declared_size`, `size`, `sha256`, `status` (`pending`, `uploaded`, `rejected`, `quarantined`), `created_at`, `completed_at` |

### Evaluation

| Table | Columns |
|---|---|
| `evaluation_runs` | `id`, `tenant_id`, `submission_id`, `upload_id`, `rubric_version_id`, `scoring_profile` (jsonb snapshot), `status`, `current_step`, `idempotency_key` (unique per tenant), `error_code`, `error_detail`, `created_by`, `created_at`, `started_at`, `finished_at` |
| `pipeline_steps` | `tenant_id`, `run_id`, `step` (PK `run_id, step`), `status`, `attempt`, `started_at`, `finished_at`, `error` |
| `pipeline_events` | `id` (bigint identity), `tenant_id`, `run_id`, `type`, `payload` (jsonb), `created_at` |
| `deck_documents` | `run_id` (PK), `tenant_id`, `parser_version`, `source_format`, `slide_count`, `content` (jsonb), `created_at` |
| `criterion_scores` | `tenant_id`, `run_id`, `criterion_key` (PK `run_id, criterion_key`), `score` (numeric), `score_low`, `score_high`, `agreement`, `evidence` (jsonb), `missing` (jsonb), `reasoning`, `samples` (jsonb, raw) |
| `evaluation_results` | `run_id` (PK), `tenant_id`, `submission_id`, `total_score`, `band_low`, `band_high`, `confidence`, `structure_report` (jsonb), `feedback` (jsonb), `prompt_version`, `created_at` |
| `integrity_flags` | `id`, `tenant_id`, `run_id`, `kind`, `severity`, `slide_index`, `excerpt`, `detail` |
| `score_overrides` | `id`, `tenant_id`, `submission_id`, `criterion_key`, `score`, `note`, `judge_id`, `created_at`; unique `(tenant_id, submission_id, criterion_key, judge_id)` |
| `llm_calls` | `id`, `tenant_id`, `run_id`, `purpose`, `provider`, `model`, `prompt_version`, `request_hash`, `input_tokens`, `output_tokens`, `cached_tokens`, `cost_micros`, `latency_ms`, `status`, `response` (jsonb), `created_at` |

A submission's current result is the result of its most recent succeeded run. Re-evaluation creates a new run; earlier runs are kept.

### Originality

| Table | Columns |
|---|---|
| `deck_embeddings` | `run_id` (PK), `tenant_id`, `event_id`, `submission_id`, `model`, `embedding` (`vector(1024)`), `shingles` (jsonb), `created_at` |
| `similarity_findings` | `id`, `tenant_id`, `event_id`, `submission_id`, `other_submission_id`, `semantic`, `lexical`, `band` (`common_theme`, `closely_related`, `text_overlap`), `created_at`; unique `(tenant_id, submission_id, other_submission_id)` |

### Billing

| Table | Columns |
|---|---|
| `credit_balances` | `tenant_id` (PK), `available`, `reserved`, `updated_at` |
| `credit_ledger` | `id`, `tenant_id`, `entry_type` (`grant`, `reserve`, `capture`, `release`, `adjustment`), `amount` (signed int), `reference_type`, `reference_id`, `idempotency_key`, `created_by`, `created_at`; unique `(tenant_id, idempotency_key)` |
| `credit_reservations` | `id`, `tenant_id`, `run_id` (unique), `amount`, `status` (`held`, `captured`, `released`), `created_at`, `settled_at` |

Plans (`free`, `team_pass`, `institution_season`, `institution_year`, `organiser_event`) are defined in code with their credit grant and concurrency limit.

### Audit and idempotency

| Table | Columns |
|---|---|
| `audit_log` | `id`, `tenant_id`, `actor_id`, `action`, `target_type`, `target_id`, `metadata` (jsonb), `request_id`, `created_at` |
| `idempotency_keys` | `tenant_id`, `key` (PK together), `request_hash`, `response_status`, `response_body` (jsonb), `created_at` |

## Object storage keys

```
tenants/{tenant_id}/submissions/{submission_id}/original/{upload_id}.{ext}
tenants/{tenant_id}/submissions/{submission_id}/derived/{run_id}/slide-{n}.png
tenants/{tenant_id}/exports/{export_id}.{ext}
```

Keys are generated by the server and never contain a user-supplied filename.

## Deletion

Deleting a submission is a soft delete followed by a job that removes the stored objects, the parsed document, embeddings, model call payloads and results. Ledger and audit rows are kept. A nightly job applies each tenant's `retention_days` the same way.
