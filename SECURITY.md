# Security Policy

This project aims to be production-grade and security-conscious. Below are key controls and practices implemented and expected in deployments.

## Threat Model and Controls

- API authentication
  - All `/api/*` endpoints require an API key (Authorization: Bearer KEY) when `API_KEYS` is configured.
  - Keys are managed via environment variables. Never commit secrets.

- Path traversal prevention
  - `client_id` is validated (regex: `^[a-zA-Z0-9_-]{1,64}$`) and resolved to enforce base directory containment.
  - Attempts to access outside `./clients` or `./rag_alt/clients` are rejected.

- CORS restrictions
  - `ALLOWED_ORIGINS` env var configures allowed origins.
  - `allow_credentials` is disabled; methods/headers are restricted.

- Security headers
  - HSTS (HTTPS required), X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP (default-src 'none', no framing).

- Rate limiting (recommended)
  - Add `starlette-limiter` (Redis) or equivalent in front proxy (NGINX/API Gateway) for DoS protection.

- Logging and PII
  - Avoid logging PII. Phone/email in client JSON must be treated as sensitive.
  - Configure structured logging for production and redact sensitive fields.

- Dependency security
  - Dependencies are pinned. CI runs `pip-audit` and `safety` on each push.

- LLM prompt injection
  - Inputs are sanitized; outputs parsed by an `AdvancedOutputParser`.
  - Consider additional guardrails depending on risk tolerance.

## Secrets Management

- Use environment variables for all secrets.
- Prefer external secret managers (Render secrets, AWS Secrets Manager, GCP Secret Manager).
- Do not commit `.env` files with real secrets.
- Provide `.env.example` for documentation only.

## Incident Response

- On suspected compromise:
  - Rotate API keys and any provider keys immediately.
  - Audit logs and request patterns.
  - Patch dependencies to latest and re-deploy.

## Compliance (GDPR)

- Data categories: business contact details (phone/email URLs), references.
- Rights: access, rectification, erasure — provide contact in `PRIVACY.md`.
- Retention: minimal storage in repository; deployers define retention policies for runtime logs.

## Reporting a Vulnerability

Please open a private security advisory or contact the maintainer directly. Do not disclose publicly until a fix is available.