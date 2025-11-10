import server.app as app_module


class FakePipe:
    def __call__(self, prompt, **kwargs):
        return [{"generated_text": "OK"}]


class FakeEmb:
    def __init__(self, model_name=None, model=None):
        self.model_name = model_name or model


class FakeLLM:
    def __init__(self, **kwargs):
        pass

    def invoke(self, prompt: str) -> str:
        return "OK"


def test_build_embeddings_hf(monkeypatch):
    monkeypatch.setattr(app_module, "LLM_PROVIDER", "HF")
    monkeypatch.setattr(app_module, "HF_EMBED_MODEL", "dummy-embed")
    monkeypatch.setattr(app_module, "HF_LLM_MODEL", "dummy-llm")
    # Patch transformers.pipeline to avoid downloads
    monkeypatch.setattr(app_module, "pipeline", lambda *a, **k: FakePipe())

    emb, llm = app_module.build_embeddings_and_llm()
    assert emb is not None and llm is not None
    assert llm.invoke("hello") == "OK"


def test_build_embeddings_ollama(monkeypatch):
    monkeypatch.setattr(app_module, "LLM_PROVIDER", "OLLAMA")
    # Patch Ollama classes to avoid real calls
    monkeypatch.setattr(app_module, "OllamaEmbeddings", FakeEmb)
    monkeypatch.setattr(app_module, "OllamaLLM", FakeLLM)

    emb, llm = app_module.build_embeddings_and_llm()
    assert emb is not None and llm is not None
    assert llm.invoke("hello") == "OK"


def test_build_embeddings_openai(monkeypatch):
    monkeypatch.setattr(app_module, "LLM_PROVIDER", "OPENAI")
    # Force HAS_OPENAI branch
    monkeypatch.setattr(app_module, "HAS_OPENAI", True)

    # Patch OpenAI classes to avoid network calls
    monkeypatch.setattr(app_module, "OpenAIEmbeddings", FakeEmb)
    monkeypatch.setattr(app_module, "ChatOpenAI", FakeLLM)

    emb, llm = app_module.build_embeddings_and_llm()
    assert emb is not None and llm is not None
    assert llm.invoke("hello") == "OK"