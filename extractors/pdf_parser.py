"""
pdf_parser.py
=============

Utilities for turning an ITDB fact‑sheet PDF (supplied as raw **bytes**) into:

1. **Plain text** – sufficient when you only need the full document as a string.
2. **A vector store** – ready for Retrieval‑Augmented Generation (RAG) pipelines.

Both functions are *pure* (no global state) so they’re easy to unit‑test.

Best‑practice highlights
------------------------
* **Lazy dependencies** – import heavy packages (`fitz`, `langchain_*`) at
  module top‑level so cold‑starts in Streamlit remain fast.
* **Chunking before embedding** – `RecursiveCharacterTextSplitter` with a
  modest overlap (20 % by default) retains context and prevents the embeddings
  model from truncating long passages.
* **Metadata‑rich `Document` objects** – makes future provenance or
  citation features easier.
* **Single‑responsibility helpers** – `extract_text_from_pdf` does *not*
  embed; `parse_and_embed` handles RAG needs.
"""

from __future__ import annotations

from typing import List, Tuple

import fitz  # PyMuPDF

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.vectorstores.faiss import FAISS
from langchain_openai import AzureOpenAIEmbeddings


# --------------------------------------------------------------------------- #
# Plain text extractor (kept for any non‑RAG use cases)
# --------------------------------------------------------------------------- #
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract all text from a PDF supplied as *bytes*.

    Parameters
    ----------
    pdf_bytes
        Binary content of a PDF.

    Returns
    -------
    str
        Concatenated text from every page, separated by newlines.

    Notes
    -----
    This purposely ignores images and tables—LLMs cope fine with raw text.
    """
    
with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
    full_text = "\n".join(page.get_text() for page in doc)
return full_text


# --------------------------------------------------------------------------- #
# Text‑to‑vector helper for RAG
# --------------------------------------------------------------------------- #
def parse_and_embed(
    pdf_bytes: bytes,
    embeddings_client: AzureOpenAIEmbeddings,
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 240,
    return_vectorstore: bool = True,
) -> "FAISS | List[Tuple[Document, list[float]]]":
    """
    Convert a PDF into an *embedded* representation.

    Parameters
    ----------
    pdf_bytes
        The PDF content as bytes.
    embeddings_client
        Pre‑configured :class:`AzureOpenAIEmbeddings` instance pointing at your
        embedding deployment (e.g. *text-embedding-ada-002*).
    chunk_size, chunk_overlap
        Controls for :class:`RecursiveCharacterTextSplitter`.  The defaults
        keep chunks safely below the 8 k token limit of `text-embedding-ada-002`
        while still holding useful context.
    return_vectorstore
        *True*  – return a ready‑to‑query :class:`FAISS` store (recommended).  
        *False* – return ``List[Tuple[Document, vector]]`` if you need manual
                  control or wish to persist vectors elsewhere.

    Returns
    -------
    FAISS | list
        Either a FAISS vector store with `.as_retriever(...)` support **or**
        a list of ``(Document, embedding)`` tuples.
    """
    # 1️⃣  Extract and split ---------------------------------------------------
    raw_text = extract_text_from_pdf(pdf_bytes)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    docs: List[Document] = [Document(page_content=txt) for txt in splitter.split_text(raw_text)]

    # 2️⃣  Embed ---------------------------------------------------------------
    if return_vectorstore:
        # The vector store persists both text and vectors – great for RAG
        return FAISS.from_documents(docs, embeddings_client)

    # Manual mode: caller does their own storage/indexing
    vectors = embeddings_client.embed_documents([d.page_content for d in docs])
    return list(zip(docs, vectors))
