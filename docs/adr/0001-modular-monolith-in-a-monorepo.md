# 1. Modular monolith in a monorepo

Status: accepted · 2026-10-01

## Context
The product has several distinct areas (tenancy, events, evaluation, billing) built by a small team that will also deploy it.

## Decision
One repository. One Python package, `deck_core`, organised by bounded context with domain, application, infrastructure and interface layers. Two thin entry points, the API and the worker, share it. Import rules are enforced by import-linter.

## Consequences
One deployable codebase and one schema to migrate. Contexts can be extracted later because they only meet at `public.py`. Discipline depends on the import contracts staying in CI.
