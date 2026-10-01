# Engineering conventions

These apply to all code in the repository. Where a rule is enforced by tooling, the tool is named.

## Python

- Python 3.14. Dependencies managed by uv in one workspace with one lockfile.
- `ruff format` and `ruff check`; `mypy --strict`. No `# type: ignore` without an error code and a reason.
- Domain entities are frozen dataclasses or plain classes. Pydantic models are for HTTP schemas, settings and model output only, never for domain entities or ORM rows.
- SQLAlchemy 2.x Core tables with explicit mapping functions between rows and entities. No ORM lazy loading.
- All I/O is async. One unit of work per request or per job step.
- Use cases are classes with a single `execute` method, constructed with their ports. They receive a `Principal` and check a permission before doing anything else.
- Errors: raise subclasses of `deck_core.shared_kernel.errors.DomainError`. Do not raise `HTTPException` outside `interfaces/http`. Do not catch bare `Exception` except at process boundaries.
- Time and ids come from injected `Clock` and `IdGenerator`, so tests are deterministic.
- No module-level mutable state. Wiring happens in the composition roots (`apps/api`, `apps/worker`).
- Comments explain why, not what. Public functions get a docstring when the name and signature do not already say enough.

## Layering

Enforced by `import-linter` (see `pyproject.toml`).

- `domain` imports nothing outside `shared_kernel`.
- A context imports another context only through its `public.py`.
- No cross-context SQL joins.

## Database

- Every schema change is an Alembic migration. `alembic check` must pass.
- A new tenant-owned table calls `enable_tenant_rls()` in its migration. A meta-test fails if a table with `tenant_id` lacks the policy.
- Integration tests connect as `app_rw`, never as a superuser.

## HTTP API

- Versioned under `/v1`. Tenant-scoped routes are under `/v1/tenants/{tenant_id}`.
- Every operation has an explicit `operation_id` of the form `context_action` (`events_list`), because generated client names derive from it.
- Request models forbid unknown fields. Response models are explicit; never return an entity or row directly.
- Errors are RFC 9457 problem documents with a stable `code`.
- List endpoints are cursor-paginated.
- A resource in another tenant returns 404.

## TypeScript

- Strict mode. No `any`; no non-null assertions without a comment.
- The generated client in `packages/api-client` is the only way to call the API. Do not hand-write request types.
- Server state lives in TanStack Query with the tenant id in every query key. No authenticated data is cached in the Next.js layer.
- Feature code lives in `features/<name>`; `app/` composes it.

## Tests

- Unit tests cover domain and application code with fakes for ports and run without I/O.
- Integration tests use real PostgreSQL through testcontainers.
- Every tenant-scoped feature has a cross-tenant test.
- Tests assert behaviour, not implementation. No test depends on wall-clock time or network.

## Commits

Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`). One logical change per commit.
