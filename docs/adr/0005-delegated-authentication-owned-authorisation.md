# 5. Delegated authentication, backend-owned authorisation

Status: accepted · 2026-10-01

## Context
The product needs email and Google sign-in now and institutional SSO later, and must not be tied to one identity vendor.

## Decision
The API verifies OIDC bearer tokens against the issuer's JWKS through an `IdentityProvider` port and maps `(issuer, subject)` to a local user. Tenants, memberships, roles and permissions live in backend tables. The default identity provider is Better Auth, self-hosted in the web app; its organisation features are not used.

## Consequences
The provider can be swapped for Keycloak or WorkOS without touching the backend. The web app is a required component for sign-in.
