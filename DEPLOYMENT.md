# Guide de déploiement

## Prérequis

- Docker / Kubernetes (optionnel)
- Redis (pour rate limiting SlowAPI) `REDIS_URL=redis://host:6379`
- Variables d'environnement:
  - `ENV=production`
  - `API_KEYS` (liste de clés, séparées par des virgules)
  - `ALLOWED_ORIGINS` (liste d'origines autorisées, séparées par des virgules)
  - `API_KEY_CLIENT_MAP` (RBAC léger: `key1:clientA,clientB;key2:clientC`)
  - `RATE_LIMIT_RULE` (ex: `60/minute`)
  - `RATE_LIMIT_KEY` (`ip` ou `apikey`)
  - `REDIS_URL` (pour activer le rate limiting Redis)
  - Observabilité (facultatif): `SENTRY_DSN`

## Docker

Build & run:

```
docker build -t chat-bot-ai:latest .
docker run -p 8000:8000 \
  -e ENV=production \
  -e API_KEYS="key1,key2" \
  -e ALLOWED_ORIGINS="https://front.example.com" \
  chat-bot-ai:latest
```

## Sécurité

- En production, API_KEYS et ALLOWED_ORIGINS doivent être définis.
- CORS wildcard est interdit.
- Rate limiting Redis recommandé; sinon limiter au proxy.
- Jamais de secrets dans les images; utiliser un secret manager.

## Observabilité

- Metrics Prometheus exposées sur `/metrics` lorsque activées.
- Sentry (optionnel): définir `SENTRY_DSN`.

## Runbook (incident)

- Rotation des clés API en cas d’incident
- Désactivation temporaire des clés compromises
- Audit des logs et traces
- Réindexation vectorstore si corruption suspectée