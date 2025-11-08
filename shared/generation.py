import re
from typing import List, Dict, Any

from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser


class AdvancedOutputParser(BaseOutputParser):
    def __init__(self, brand_name: str):
        self.brand_name = brand_name

    def parse(self, text: str) -> str:
        t = re.sub(r"\[.*?\]", "", text)
        t = re.sub(r"\*+\s?", "", t)
        t = re.sub(r"\n+", "\n", t)

        leak_markers = ["MISSION", "VOCABULAIRE", "# ", "🎬 MISSION"]
        if any(m in t for m in leak_markers):
            parts = re.split(r"Réponse\s*:|\*\*Réponse\s*:?\*\*", t)
            if len(parts) > 1:
                t = parts[-1].strip()

        sentences = [s.strip() for s in t.split(". ") if s.strip()]
        uniq = []
        for s in sentences:
            if s not in uniq:
                uniq.append(s)
        res = ". ".join(uniq).strip()

        if len(res) < 25:
            return f"Merci pour votre message. L'équipe {self.brand_name} vous répond rapidement. Contact recommandé pour devis/précisions."
        return res


class ContextEnhancer:
    def __init__(self, client_data: Dict):
        self.client_data = client_data

    def enhance(self, docs: List[Any]) -> str:
        if not docs:
            ent = self.client_data.get("entreprise", {})
            return f"{ent.get('nom','Votre entreprise')} — {ent.get('slogan','')}"
        return "\n".join([d.page_content for d in docs[:3]])


def detect_scenario(q: str) -> str:
    ql = q.lower()
    if any(k in ql for k in ["urgent", "demain", "crise", "last minute"]):
        return "Urgence"
    if any(k in ql for k in ["prix", "devis", "budget", "tarif"]):
        return "Devis"
    if any(k in ql for k in ["référence", "reference", "portfolio"]):
        return "Références"
    return "Question générale"


DEFAULT_PROMPT_TEMPLATE = """Tu es l'assistant de {brand_name}.

CONTEXTE:
{context}

CLIENT DIT: "{question}"

SITUATION: {scenario}

Mission: Réponds en 2-3 phrases claires, professionnelles et orientées solution. Termine par un appel à l'action (contact, devis, etc.).
Réponse:"""