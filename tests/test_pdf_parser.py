import importlib
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))




class DummyPage:
    def __init__(self, text):
        self._text = text

    def get_text(self):
        return self._text


class DummyDoc:
    def __init__(self, pages):
        self.pages = pages
        self.entered = False
        self.exited = False

    def __iter__(self):
        return iter(self.pages)

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.exited = True


def test_extract_text_uses_context_manager(monkeypatch):
    dummy_doc = DummyDoc([DummyPage("a"), DummyPage("b")])

    def fake_open(*args, **kwargs):
        return dummy_doc

    sys.modules["fitz"] = types.SimpleNamespace(open=fake_open)
    sys.modules.setdefault(
        "langchain.text_splitter", types.SimpleNamespace(RecursiveCharacterTextSplitter=None)
    )
    sys.modules.setdefault(
        "langchain.docstore.document", types.SimpleNamespace(Document=None)
    )
    sys.modules.setdefault("langchain.vectorstores.faiss", types.SimpleNamespace(FAISS=None))
    sys.modules.setdefault("langchain_openai", types.SimpleNamespace(AzureOpenAIEmbeddings=None))

    from extractors import pdf_parser
    importlib.reload(pdf_parser)

    text = pdf_parser.extract_text_from_pdf(b"%PDF")
    assert text == "a\nb"
    assert dummy_doc.entered is True
    assert dummy_doc.exited is True
