# API Documentation

## Base URL
- Local development: `http://localhost:8000`
- Production (Render): `https://<your-service>.onrender.com`

## Authentication

If `API_KEYS` is configured, all `/api/*` endpoints require:

```
Authorization: Bearer <YOUR_API_KEY>
```

## Endpoints

### Health Check

- `GET /healthz`
- Response:
```json
{"status":"ok"}
```

### Chat

- `POST /v1/chat` (recommended)
- `POST /api/chat` (legacy alias)
- Body (JSON):
  - `question` (string, required)
  - `client_id` (string, default: "bms_ventouse") — validated by regex `^[a-zA-Z0-9_-]{1,64}# API Documentation

## Base URL
- Local development: `http://localhost:8000`
- Production (Render): `https://<your-service>.onrender.com`

## Authentication

If `API_KEYS` is configured, all `/api/*` endpoints require:

```
Authorization: Bearer <YOUR_API_KEY>
```

## Endpoints

### Health Check

- `GET /healthz`
- Response:
```json
{"status":"ok"}
```


  - `mode` ("main" | "alt", default: "main")
  - `refresh` (boolean, default: false) — rebuild pipeline and vectorstore
- Response (JSON):
  - `client_id`, `mode`, `provider`
  - `response` (string)
  - or `error` (string)

Example:
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_API_KEY>" \
  -d '{"question":"Urgence tournage demain à Paris","client_id":"bms_ventouse","mode":"main"}'
```

## CORS

Allowed origins are configured via `ALLOWED_ORIGINS` env var (comma-separated list). Credentials are disabled.

## Errors

- 401 Unauthorized — missing or invalid API key when required
- 400/422 — invalid payload
- 500 — internal server error (limited)