# Security Baseline

## Required controls

- `.env` for credentials and API keys — never commit to git
- Gitleaks pre-commit hook for zero secrets in code
- Read-only Oracle connection — no writes to source system
- API Key authentication on FastAPI endpoints
- Minimal permissions for PostgreSQL service users

## Delivery rule

No scaffold is complete unless it names the security boundary and the observability hook for that component.
