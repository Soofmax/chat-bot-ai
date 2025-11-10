# Template Showcase — Dashboards clients statiques

Ce guide explique comment générer et déployer des **dashboards clients** (sites statiques) qui consomment l'API RAG (`POST /v1/chat`). L'objectif est d'avoir un **template duplicable en quelques minutes** pour chaque client, sans refonte.

## ⚙️ Prérequis côté API

En production:
- `ENV=production`
- `API_KEYS` (liste de clés valides)
- `ALLOWED_ORIGINS="https://site-client.example.com"` (domaine du site statique)
- `REDIS_URL` (rate limiting global requis en prod)

## 🚀 3 façons d'adapter le template par client

### 1) Paramètres d'URL (le plus rapide)
Vous pouvez adapter le dashboard **sans aucun fichier** via l’URL:

```
https://site-client.example.com/dashboard/?apiUrl=https://api.example.com&apiKey=key1&clientId=bms_ventouse&mode=main&brandName=Ma%20Marque&accent=%2322c55e
```

Supportés:
- `apiUrl`, `apiKey`, `clientId`, `mode`
- `brandName`, `accent`, `bg`, `card`, `text`, `muted`

### 2) config.json (fichier par client)
Placez un `config.json` dans le dossier `dashboard/` ou dans votre site statique:

```json
{
  "brandName": "Ma Marque",
  "theme": { "accent": "#3b82f6", "bg": "#0b0f1a", "card": "#111827", "text": "#e5e7eb", "muted": "#9ca3af" },
  "apiUrl": "https://api.example.com",
  "apiKey": "key1",
  "clientId": "bms_ventouse",
  "mode": "main",
  "requestId": "",
  "debug": false
}
```

Un exemple est fourni: `dashboard/config.example.json`.

### 3) Générateur de bundles (plusieurs clients)
Créez un fichier `dashboard/clients.json` qui liste les configurations clients (exemple: `dashboard/clients.example.json`), puis:

```
python scripts/build_dashboards.py -i dashboard/clients.json -o dist
```

Chaque client aura un bundle statique dans `dist/<clientId>-dashboard/` prêt à être publié.

## 🖥️ Déploiement

### GitHub Pages (CI/CD automatique)
Le workflow CI génère les bundles si `dashboard/clients.json` existe et peut publier sur GitHub Pages.

Étapes:
1. Activez GitHub Pages (Settings → Pages).
2. Ajoutez `dashboard/clients.json`.
3. Poussez sur `main`.
4. La CI:
   - Génère `dist/` via `scripts/build_dashboards.py`
   - Publie `dist/` sur Pages (job `deploy-pages`)

### Netlify (CI/CD automatique)
Le job `deploy-netlify` de la CI déploie `dist/` si les secrets suivants sont configurés:
- `NETLIFY_AUTH_TOKEN`: token API Netlify
- `NETLIFY_SITE_ID`: ID du site Netlify (target)

Étapes:
1. Créez/identifiez un site Netlify (statique) et récupérez `NETLIFY_SITE_ID`.
2. Ajoutez les secrets dans GitHub (`Settings → Secrets and variables → Actions`).
3. Poussez sur `main` avec un `dashboard/clients.json`.
4. La CI:
   - Bâtit `dist/` (dashboards)
   - Déploie `dist/` sur Netlify via `netlify-cli`

### Vercel (CI/CD automatique)
Le job `deploy-vercel` déploie `dist/` si les secrets suivants sont configurés:
- `VERCEL_TOKEN`: token Vercel
- `VERCEL_ORG_ID`: organisation Vercel
- `VERCEL_PROJECT_ID`: projet Vercel cible

Étapes:
1. Configurez un projet Vercel (statique). Note: vous pouvez créer un projet spécialisé pour les dashboards.
2. Ajoutez les secrets dans GitHub.
3. Poussez sur `main` avec `dashboard/clients.json`.
4. La CI déploie `dist/` avec `vercel deploy --prod`.

### Déploiement manuel
- Netlify/Vercel: déployez le contenu de `dist/<clientId>-dashboard` directement.
- Ajoutez un `config.json` spécifique si vous n’utilisez pas les paramètres d’URL.

## 🧰 Outils inclus

- `dashboard/index.html`, `style.css`, `app.js`: UI responsive, debug mode et historique des requêtes, bouton “Copier CURL”
- `scripts/build_dashboard.py`: génère un bundle pour **un** client
- `scripts/build_dashboards.py`: génère des bundles pour **plusieurs** clients depuis `dashboard/clients.json`
- `dashboard/README.md`: documentation détaillée d’intégration
- `shared/client.ts`: client TypeScript léger typé via OpenAPI

## 🛡️ Debug & observabilité

- `Request ID`: permet de corréler la réponse avec les logs serveur (X-Request-ID)
- `Debug` mode: affiche le JSON complet (incluant erreurs)
- Historique local (20 entrées): exportable en JSON; copie cURL par requête

## 🧪 Test rapide

```
curl -X POST https://api.example.com/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer key1" \
  -d '{"question":"Besoin devis", "client_id":"bms_ventouse", "mode":"main"}'
```

## 📝 Makefile (optionnel)

Exécutez `make dashboards` pour générer les bundles depuis `dashboard/clients.json`:
```
make dashboards
```

## 🔒 Sécurité

- Ajoutez le domaine du site statique dans `ALLOWED_ORIGINS` côté API (CORS)
- En production, utilisez une clé API et `REDIS_URL`
- Les réponses d’erreur HTTP sont normalisées (400/401/403/404/429/500)