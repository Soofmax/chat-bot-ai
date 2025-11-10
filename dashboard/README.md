# Dashboard Client — Template statique

Ce dashboard est un **template prêt à l’emploi** pour tester l’API RAG par client, déployable sur n’importe quel hébergeur de site statique (GitHub Pages, Netlify, Vercel, etc.).

## Fonctionnement

Le dashboard consomme l’endpoint `POST /v1/chat` de l’API. Il expose une interface pour:
- Configurer l’API (URL, clé API), le `client_id` et le `mode` (`main|alt`)
- Saisir une question et envoyer la requête
- Visualiser le statut HTTP et la réponse
- **Exporter / Importer** un `config.json`
- **Copier une commande cURL** correspondant à la requête courante

## Configuration — 4 sources (ordre de priorité)

1. **Paramètres d’URL** (override rapide sans modifier de fichiers):
   ```
   ?apiUrl=https://api.example.com&apiKey=key1&clientId=bms_ventouse&mode=main&brandName=Ma%20Marque&accent=%2322c55e
   ```

2. **localStorage** (persistant dans le navigateur, via bouton “Enregistrer la configuration”)

3. **config.json** (fichier statique dans le même dossier):
   - Exemple `config.example.json` fourni:
     ```json
     {
       "brandName": "Ma Marque",
       "theme": {
         "accent": "#3b82f6",
         "bg": "#0b0f1a",
         "card": "#111827",
         "text": "#e5e7eb",
         "muted": "#9ca3af"
       },
       "apiUrl": "https://api.example.com",
       "apiKey": "",
       "clientId": "bms_ventouse",
       "mode": "main"
     }
     ```

4. **Defaults internes** (valeurs par défaut intégrées au code)

Le **thème** (couleurs CSS) et le **brandName** sont également configurables via `config.json` ou paramètres d’URL.

## Déploiement

### GitHub Pages
- Option A: Placez le dossier `dashboard/` à la racine ou dans `docs/`.
- Activez GitHub Pages sur `Settings → Pages` et sélectionnez la source (branche + dossier).
- Mettez `config.json` spécifique au client dans le même dossier si besoin.

### Netlify / Vercel
- Créez un projet “site statique” et déployez le contenu de `dashboard/`.
- Ajoutez `config.json` si vos valeurs ne sont pas passées par URL.

## CORS (serveur)

Côté API, vous devez autoriser le domaine du site statique:
- `ALLOWED_ORIGINS="https://site-client.example.com"`
- En production, l’API exige également:
  - `ENV=production`
  - `API_KEYS` (liste des clés valides)
  - `REDIS_URL` (rate limiting global)

## CLI — Générer un bundle par client

Utilisez `scripts/build_dashboard.py` pour produire un paquet statique prêt à publier:
```
python scripts/build_dashboard.py \
  --client-id bms_ventouse \
  --brand-name "BMS Ventouse" \
  --api-url https://api.mondomaine.com \
  --api-key key1 \
  --mode main \
  --accent "#22c55e" \
  --output dist/bms_ventouse-dashboard
```
Le dossier `dist/bms_ventouse-dashboard` contiendra `index.html`, `style.css`, `app.js` et le `config.json` spécifique.

## Bouton “Copier CURL”

Le bouton **Copier CURL** génère et copie une commande cURL équivalente à la requête courante:
- Inclut l’URL `/v1/chat`
- En-têtes `Content-Type` et `Authorization` (si configurée)
- Corps JSON avec `question`, `client_id`, `mode`, `refresh`

Vous pouvez coller la commande dans un terminal pour tester rapidement.

## Bonnes pratiques

- **Production**: utilisez une clé API (Bearer) et configurez `ALLOWED_ORIGINS` + `REDIS_URL`.
- **Sécurité**: évitez d’exposer des clés dans des commits publics; préférez les paramètres d’URL lors de démos temporaires.
- **Personnalisation**: préférez `config.json` par client et ajustez le `brandName` + le thème via paramètres.
- **Types**: des types TypeScript sont générés par la CI (`shared/api-types.ts`), vous pouvez les importer pour un client front plus robuste.