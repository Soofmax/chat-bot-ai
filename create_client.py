#!/usr/bin/env python3
import json
import re
from pathlib import Path
import argparse

SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

def ensure_safe_client_id(client_id: str) -> str:
    if not SAFE_ID.match(client_id):
        raise ValueError("client_id invalide: utilisez lettres, chiffres, _ ou -, max 64 caractères")
    return client_id

def main():
    parser = argparse.ArgumentParser(description="Créer un nouveau client à partir du template")
    parser.add_argument("--client-id", required=True, help="Identifiant client (slug)")
    parser.add_argument("--brand-name", required=True, help="Nom de la marque/entreprise")
    parser.add_argument("--mode", choices=["main","alt"], default="main", help="Type de client (main|alt)")
    args = parser.parse_args()

    cid = ensure_safe_client_id(args.client_id)
    base = Path("./rag_alt/clients" if args.mode == "alt" else "./clients")
    tmpl_path = Path("./clients/_template/data.json")
    out_dir = (base / cid)
    out_file = out_dir / "data.json"

    if not tmpl_path.exists():
        raise FileNotFoundError("Template introuvable: clients/_template/data.json")

    out_dir.mkdir(parents=True, exist_ok=True)

    with tmpl_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Remplacer placeholders
    def replace_in_obj(obj):
        if isinstance(obj, str):
            return obj.replace("{{BRAND_NAME}}", args.brand_name)
        if isinstance(obj, list):
            return [replace_in_obj(x) for x in obj]
        if isinstance(obj, dict):
            return {k: replace_in_obj(v) for k, v in obj.items()}
        return obj

    data = replace_in_obj(data)

    with out_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Client créé: {out_file}")

if __name__ == "__main__":
    main()