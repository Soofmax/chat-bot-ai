from server.app import _get_prompt_template
from shared.generation import DEFAULT_PROMPT_TEMPLATE

def test_prompt_template_default():
    client_data = {"entreprise": {"nom": "TestCo"}}
    tmpl = _get_prompt_template(client_data)
    assert tmpl == DEFAULT_PROMPT_TEMPLATE

def test_prompt_template_custom():
    custom = "Tu es l'assistant de {brand_name}. Contexte:\n{context}\nQuestion: {question}\nCas: {scenario}\nRéponse:"
    client_data = {"entreprise": {"nom": "TestCo"}, "prompt_template": custom}
    tmpl = _get_prompt_template(client_data)
    assert tmpl == custom