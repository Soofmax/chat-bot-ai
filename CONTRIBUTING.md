# CONTRIBUTING

Merci de contribuer à ce projet. Voici les règles de base :

- Proposez une PR avec description claire.
- Écrivez des tests pour toute nouvelle fonctionnalité.
- Respectez le style (ruff, black) et le typage (mypy).
- Ajoutez la documentation nécessaire (README/API/SECURITY).
- Ne commitez jamais de secrets (.env, clés).

## Environnement

- Python 3.11
- `pip install -r requirements.txt && pip install -r requirements-dev.txt`

## Qualité

- Lint: `ruff check .`
- Format: `black .`
- Types: `mypy --ignore-missing-imports .`
- Tests: `pytest --cov=. --cov-report=term-missing`

## Sécurité

- `pip-audit -r requirements.txt`
- `safety check -r requirements.txt --full-report`

Merci !