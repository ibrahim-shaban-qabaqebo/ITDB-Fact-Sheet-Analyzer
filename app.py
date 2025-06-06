# app.py
from dotenv import load_dotenv
import os
import streamlit as st
import pandas as pd
import base64
from openai import AzureOpenAI
from extractors.json_extractor import extract_json
from extractors.pdf_parser import extract_text_from_pdf, parse_and_embed

# LangChain / RAG
from langchain.vectorstores.faiss import FAISS
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate

load_dotenv()

# Chat‑model credentials
api_key = os.getenv("OPENAI_API_KEY")
endpoint = os.getenv("OPENAI_API_ENDPOINT")
deployment = os.getenv("OPENAI_DEPLOYMENT_NAME")
version = os.getenv("OPENAI_API_VERSION")

# Embedding‑model credentials
embed_api_key = os.getenv("OPENAI_EMBEDDING_API_KEY")
embed_endpoint = os.getenv("OPENAI_EMBEDDING_ENDPOINT")
embed_deployment = os.getenv("OPENAI_EMBEDDING_DEPLOYMENT")

# Low‑level Azure client (used only for structured‑data extraction)
client = AzureOpenAI(api_version=version, azure_endpoint=endpoint, api_key=api_key)

# ------------------------------------------------------------------ #
# Prompt & fallback chat model
# ------------------------------------------------------------------ #
BASE_SYSTEM_PROMPT = (
    "You are the ITDB Fact‑Sheet Assistant. "
    "Keep answers concise and reference the sheet when relevant."
)

base_llm = AzureChatOpenAI(
    azure_endpoint=endpoint,
    openai_api_version=version,
    openai_api_key=api_key,
    azure_deployment=deployment,
    temperature=0.7,
)

# ------------------------------------------------------------------ #
# Session‑state initialisation
# ------------------------------------------------------------------ #
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! I'm here to help with fact‑sheets."},
    ]

# Render past chat (skip system)
for m in st.session_state.messages:
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ------------------------------------------------------------------ #
# Sidebar – PDF upload and preprocessing
# ------------------------------------------------------------------ #
with st.sidebar:
    uploaded = st.file_uploader("Upload ITDB fact‑sheet PDF", type="pdf")

    if uploaded:
        pdf_bytes = uploaded.read()
        st.subheader("PDF Preview")

        # Extract raw text
        raw_text = extract_text_from_pdf(pdf_bytes)
        st.session_state["pdf_text"] = raw_text

        # Build / refresh vector store and RAG chain
        if ("rag_chain" not in st.session_state) or (
            st.session_state.get("pdf_name") != uploaded.name
        ):
            # Embedding model
            embeddings = AzureOpenAIEmbeddings(
                azure_endpoint=embed_endpoint,
                openai_api_key=embed_api_key,
                openai_api_version=version,
                azure_deployment=embed_deployment,
            )

            vs: FAISS = parse_and_embed(
                pdf_bytes,
                embeddings_client=embeddings,
                chunk_size=1200,
                chunk_overlap=200,
                return_vectorstore=True,
            )
            st.session_state["vector_store"] = vs

            memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")

            rag_llm = AzureChatOpenAI(
                azure_endpoint=endpoint,
                openai_api_version=version,
                openai_api_key=api_key,
                azure_deployment=deployment,
                temperature=0.2,
            )

            qa_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are the ITDB Fact‑Sheet Assistant.\n"
                        "Use the following context to answer the user's question. "
                        "Keep the answer concise.\n\nContext:\n{context}",
                    ),
                    ("human", "{question}"),
                ]
            )

            chain = ConversationalRetrievalChain.from_llm(
                rag_llm,
                retriever=vs.as_retriever(search_kwargs={"k": 6}),
                memory=memory,
                combine_docs_chain_kwargs={"prompt": qa_prompt},
            )

            st.session_state["rag_chain"] = chain
            st.session_state["pdf_name"] = uploaded.name

        # Download + Extract buttons
        col_dl, col_ex = st.columns(2)
        with col_dl:
            st.download_button("Download PDF", data=pdf_bytes, file_name=uploaded.name)

        with col_ex:
            if st.button("Extract structured data"):
                with st.spinner("Extracting structured data…"):
                    try:
                        structured = extract_json(raw_text, client=client, deployment=deployment)
                        st.session_state["structured_data"] = structured

                        # Embed JSON blob for richer retrieval
                        if "vector_store" in st.session_state:
                            import json

                            st.session_state["vector_store"].add_texts(
                                [json.dumps(structured, indent=2)],
                                metadatas=[{"source": "structured_json"}],
                            )
                        st.success("Structured data extracted!")
                    except Exception as exc:
                        st.error(f"Extraction failed: {exc}")

        # PDF preview in iframe
        b64 = base64.b64encode(pdf_bytes).decode()
        st.markdown(
            f"""
            <div style="height: 90vh; overflow:auto;">
              <iframe src="data:application/pdf;base64,{b64}" width="100%" height="100%" style="border:none;"></iframe>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Show extracted text"):
            st.text_area("Raw Text", raw_text, height=300)

# ------------------------------------------------------------------ #
# Chat input (runs after sidebar)
# ------------------------------------------------------------------ #
if prompt := st.chat_input("Ask me anything…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    chain = st.session_state.get("rag_chain")
    with st.chat_message("assistant"):
        if chain:
            answer = chain({"question": prompt})["answer"]
        else:
            answer = base_llm.invoke(st.session_state.messages).content.strip()
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

# ------------------------------------------------------------------ #
# Structured JSON table
# ------------------------------------------------------------------ #
if "structured_data" in st.session_state:
    st.subheader("Structured Data")
    df = pd.json_normalize(st.session_state["structured_data"])
    st.dataframe(df, use_container_width=True)