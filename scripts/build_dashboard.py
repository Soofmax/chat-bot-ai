import argparse
import json
import os
import shutil
from pathlib import Path


DASHBOARD_DIR = Path("dashboard")


def build_dashboard(client_id: str, brand_name: str, api_url: str, api_key: str, mode: str, accent: str, output: str):
    # Prepare output directory
    out_dir = Path(output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy static files
    for fname in ["index.html", "app.js", "style.css"]:
        shutil.copy(DASHBOARD_DIR / fname, out_dir / fname)

    # Write config.json
    config = {
        "brandName": brand_name,
        "theme": {
            "accent": accent or "#3b82f6",
        },
        "apiUrl": api_url,
        "apiKey": api_key,
        "clientId": client_id,
        "mode": mode or "main",
    }
    with open(out_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"Dashboard prêt: {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="Génère un bundle dashboard client (statique)")
    parser.add_argument("--client-id", required=True, help="ID du client (ex: bms_ventouse)")
    parser.add_argument("--brand-name", required=True, help="Nom de la marque")
    parser.add_argument("--api-url", required=True, help="Base URL de l'API (ex: https://api.example.com)")
    parser.add_argument("--api-key", default="", help="Clé API (optionnelle)")
    parser.add_argument("--mode", default="main", choices=["main", "alt"], help="Mode (main|alt)")
    parser.add_argument("--accent", default="#3b82f6", help="Couleur accent (hex)")
    parser.add_argument("--output", default="", help="Dossier de sortie (ex: dist/mon_client)")
    args = parser.parse_args()

    output = args.output or f"dist/{args.client_id}-dashboard"
    build_dashboard(
        client_id=args.client_id,
        brand_name=args.brand_name,
        api_url=args.api_url,
        api_key=args.api_key,
        mode=args.mode,
        accent=args.accent,
        output=output,
    )


if __name__ == "__main__":
    main()