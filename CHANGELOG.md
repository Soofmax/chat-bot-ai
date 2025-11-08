# Changelog

Toutes les modifications notables de ce projet seront documentées ici.

## [Unreleased]

- Ajout rate limiting Redis (SlowAPI) optionnel
- Gating production (auth/CORS)
- Logging JSON avec correlation ID
- Prometheus metrics
- Dockerfile durci + Trivy scan
- CI coverage gate + CodeQL + Dependabot
- LICENSE (MIT), CONTRIBUTING, CODE_OF_CONDUCT, DEPLOYMENT

## [0.1.0] - Initial

- API RAG de base avec FastAPI
- Sécurité headers, CORS, auth optionnelle, path traversal fix
- Vectorstore Chroma persisté, modules partagés