import server.app as app_module


class Doc:
    def __init__(self, content: str):
        self.page_content = content


class FakeRetriever:
    def __init__(self, docs):
        self._docs = docs

    def get_relevant_documents(self, question: str):
        return self._docs


class FakeChroma:
    def __init__(self, embedding_function=None, collection_name=None, persist_directory=None):
        self._count = 1

        class Coll:
            def __init__(self, count):
                self._count = count

            def count(self):
                return self._count

        self._collection = Coll(self._count)

    @classmethod
    def from_documents(cls, documents, embedding=None, collection_name=None, persist_directory=None, collection_metadata=None):
        inst = cls(embedding_function=embedding, collection_name=collection_name, persist_directory=persist_directory)
        inst._count = len(documents)
        return inst

    def as_retriever(self, **kwargs):
        return FakeRetriever([Doc("contexte 1"), Doc("contexte 2")])


class FakeEmb:
    pass


class FakeLLM:
    def invoke(self, prompt: str) -> str:
        return "Réponse cliente: contactez-nous."


def test_build_pipeline_main(monkeypatch, tmp_path):
    # Patch core dependencies to avoid IO/network
    monkeypatch.setattr(app_module, "Chroma", FakeChroma)
    monkeypatch.setattr(app_module, "build_embeddings_and_llm", lambda: (FakeEmb(), FakeLLM()))
    monkeypatch.setattr(app_module, "load_client_data", lambda mode, cid: {"entreprise": {"nom": "TestCo"}})
    monkeypatch.setattr(app_module, "safe_client_path", lambda mode, cid: tmp_path / "fake.json")
    monkeypatch.setattr(app_module, "load_and_prepare_documents", lambda path: [Doc("doc1"), Doc("doc2")])

    pipeline = app_module.build_pipeline("main", "clientX")
    assert pipeline.client_id == "clientX"
    assert pipeline.mode == "main"
    out = pipeline.process("question simple")
    assert "contact" in out.lower() or "contactez" in out.lower()


def test_build_pipeline_alt(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "Chroma", FakeChroma)
    monkeypatch.setattr(app_module, "build_embeddings_and_llm", lambda: (FakeEmb(), FakeLLM()))
    monkeypatch.setattr(app_module, "load_client_data", lambda mode, cid: {"entreprise": {"nom": "TestCo"}})
    monkeypatch.setattr(app_module, "safe_client_path", lambda mode, cid: tmp_path / "fake.json")
    monkeypatch.setattr(app_module, "load_and_prepare_documents", lambda path: [Doc("docA"), Doc("docB")])

    pipeline = app_module.build_pipeline("alt", "clientY")
    assert pipeline.client_id == "clientY"
    assert pipeline.mode == "alt"
    out = pipeline.process("besoin devis")
    assert "contact" in out.lower() or "devis" in out.lower()