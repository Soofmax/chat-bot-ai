import argparse
import json
import shutil
from pathlib import Path

DASHBOARD_DIR = Path("dashboard")


def build_dashboard(config: dict, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for fname in ["index.html", "app.js", "style.css"]:
        shutil.copy(DASHBOARD_DIR / fname, out_dir / fname)
    with open(out_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Génère des dashboards statiques pour plusieurs clients")
    parser.add_argument("-i", "--input", required=True, help="Fichier JSON avec la liste de clients (dashboard/clients.json)")
    parser.add_argument("-o", "--output", default="dist", help="Dossier de sortie (par défaut: dist)")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        clients = json.load(f)

    if not isinstance(clients, list):
        raise ValueError("Le fichier doit contenir une liste de configurations clients")

    for cfg in clients:
        client_id = cfg.get("clientId") or cfg.get("client_id")
        brand_name = cfg.get("brandName") or cfg.get("brand_name", "")
        if not client_id or not brand_name:
            print(f"Config invalide, clientId ou brandName manquant: {cfg}")
            continue
        out_dir = output_path / f"{client_id}-dashboard"
        build_dashboard(cfg, out_dir)
        print(f"Dashboard généré: {out_dir}")


if __name__ == "__main__":
    main()