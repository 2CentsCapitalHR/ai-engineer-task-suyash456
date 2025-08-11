# utils/rag_utils.py
import os
import json
from typing import Optional, Dict, Any, List
from langchain.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.schema import Document

VECTORSTORE_DIR = "legal_refs/faiss_store"
LEGAL_REFS_DIR = "legal_refs"
HF_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ------------------- build/load vectorstore -------------------
def build_vector_store(legal_folder: str = LEGAL_REFS_DIR,
                       save_dir: str = VECTORSTORE_DIR,
                       hf_model: str = HF_EMBEDDING_MODEL) -> FAISS:
    """Load legal refs, chunk, embed and save a FAISS vectorstore."""
    if not os.path.exists(legal_folder):
        raise FileNotFoundError(f"Legal refs folder not found: {legal_folder}")

    try:
        embeddings = HuggingFaceEmbeddings(model_name=hf_model)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize embeddings: {e}")

    docs: List[Document] = []
    for fname in os.listdir(legal_folder):
        path = os.path.join(legal_folder, fname)
        if fname.lower().endswith(".pdf"):
            loader = PyPDFLoader(path)
            pages = loader.load()
            docs.extend(pages)
        elif fname.lower().endswith(".txt"):
            loader = TextLoader(path, encoding="utf-8")
            docs.extend(loader.load())
        # optional: add other loaders if you place docs in different formats

    if not docs:
        raise ValueError("No legal reference documents found in legal_refs/")

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    try:
        vs = FAISS.from_documents(chunks, embeddings)
    except Exception as e:
        raise RuntimeError(f"Failed to build FAISS vectorstore: {e}")

    os.makedirs(os.path.dirname(save_dir), exist_ok=True)
    try:
        vs.save_local(save_dir)
    except Exception as e:
        raise RuntimeError(f"Failed to save FAISS vectorstore: {e}")
    return vs

def load_vector_store(save_dir: str = VECTORSTORE_DIR, hf_model: str = HF_EMBEDDING_MODEL) -> FAISS:
    """Load existing FAISS vectorstore from disk."""
    if not os.path.exists(save_dir):
        raise FileNotFoundError("FAISS vectorstore not found. Run build_vector_store() first.")
    embeddings = HuggingFaceEmbeddings(model_name=hf_model)
    vs = FAISS.load_local(save_dir, embeddings)
    return vs

# ------------------- LLM helper (version tolerant) -------------------
def _call_llm_tolerant(llm, prompt: str) -> str:
    """
    Call `llm` in a way that works across common LangChain wrappers.
    Returns the raw text response or raises an Exception.
    """
    if llm is None:
        raise ValueError("LLM instance is None")

    # Try multiple call patterns used by common wrappers
    try:
        # direct call (works for many wrappers)
        resp = llm(prompt)
        if isinstance(resp, str):
            return resp.strip()
    except Exception:
        resp = None

    # try predict
    try:
        if hasattr(llm, "predict"):
            resp = llm.predict(prompt)
            if isinstance(resp, str):
                return resp.strip()
    except Exception:
        pass

    # try generate -> extract text
    try:
        if hasattr(llm, "generate"):
            gen = llm.generate([prompt])
            # attempt to extract .generations[...] -> .text
            try:
                text = gen.generations[0][0].text
                return text.strip()
            except Exception:
                # fallback to stringifying the result
                return str(gen)
    except Exception:
        pass

    # fallback to __call__ or raise
    try:
        resp = llm.__call__(prompt)
        if isinstance(resp, str):
            return resp.strip()
        return str(resp)
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}")

# ------------------- RAG check -------------------
PROMPT_TEMPLATE = """You are an expert legal compliance assistant for ADGM jurisdiction.

Task:
- Given the user's clause and the ADGM context snippets below, determine compliance.
- If non-compliant, explain the issue and provide one concrete improved clause suggestion.
- If possible include the snippet's filename or short citation.

Return a JSON object exactly with keys:
{{"compliant": true/false, "issue": "...", "suggestion": "...", "citation": "..."}}

User clause:
{clause}

Context (relevant snippets):
{context}
"""

def check_clause_with_rag(clause_text: str, vectorstore: FAISS, llm: Optional[ChatOpenAI], k: int = 3) -> Dict[str, Any]:
    """Retrieve k relevant snippets and optionally call the llm to get a compliance JSON."""
    docs = vectorstore.similarity_search(clause_text, k=k)
    context = "\n\n---\n\n".join([
        (d.page_content + f"\n\n[SOURCE: {d.metadata.get('source','unknown')}]") if hasattr(d, "page_content") else str(d)
        for d in docs
    ])

    if llm is None:
        # return contexts only (no judgement)
        return {"compliant": None, "issue": None, "suggestion": None, "citation": context}

    prompt = PROMPT_TEMPLATE.format(clause=clause_text, context=context)
    try:
        raw = _call_llm_tolerant(llm, prompt)
    except Exception as e:
        return {"compliant": None, "issue": f"LLM error: {e}", "suggestion": None, "citation": context}

    # try to extract JSON from raw
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        json_text = raw[start:end]
        data = json.loads(json_text)
    except Exception:
        data = {"compliant": None, "issue": raw, "suggestion": None, "citation": context}
    return data

def create_llm(openai_model: str = "gpt-4o-mini", temperature: float = 0.0) -> ChatOpenAI:
    """Create a ChatOpenAI instance (requires OPENAI_API_KEY in env)."""
    # ChatOpenAI will use env var OPENAI_API_KEY automatically
    return ChatOpenAI(model=openai_model, temperature=temperature)
