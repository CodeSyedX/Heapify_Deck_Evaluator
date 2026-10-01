# 9. Append-only credit ledger; payment provider as a later adapter

Status: accepted · 2026-10-01

## Decision
Usage is prepaid credits recorded in an append-only ledger with unique idempotency keys. A run reserves a credit, captures it on success and releases it on failure. Entitlements are never read from a payment provider. Razorpay is the first intended adapter, because Stripe is invite-only for Indian businesses; no provider is integrated yet.

## Consequences
Billing logic is testable without a provider and identical across providers. Payment collection is manual until an adapter is built.
