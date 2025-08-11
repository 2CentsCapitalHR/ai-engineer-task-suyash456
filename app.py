# app.py
import streamlit as st
import os
import json
import sys
import platform
from utils.doc_utils import read_docx_text, save_reviewed_docx
from utils.doc_checker import load_checklists, identify_process_from_filenames, checklist_results
from utils.red_flags import run_all_checks
from utils.rag_utils import build_vector_store, load_vector_store, check_clause_with_rag, create_llm, VECTORSTORE_DIR

st.set_page_config(page_title="ADGM Corporate Agent — RAG-enabled", layout="wide")
st.title("ADGM Corporate Agent — RAG-enabled")

# Environment warnings
if sys.version_info.major == 3 and sys.version_info.minor >= 13:
    st.warning("Python 3.13+ may cause package build issues. Use Python 3.11 (64-bit) for best compatibility.")
if platform.system() == "Windows":
    st.info("On Windows, conda is recommended for installing FAISS and some binary packages.")

# Sidebar: RAG controls
with st.sidebar:
    st.header("RAG / ADGM index")
    vs_exists = os.path.exists(VECTORSTORE_DIR)
    st.write(f"Vectorstore exists: {vs_exists}")
    if st.button("(Re)build vectorstore from legal_refs/"):
        try:
            with st.spinner("Building vectorstore (this may take a few minutes)..."):
                build_vector_store()
            st.success("Vectorstore built and saved.")
            vs_exists = True
        except Exception as e:
            st.error(f"Failed to build vectorstore: {e}")

    st.write("LLM settings")
    use_llm = st.checkbox("Use OpenAI LLM for clause checks (requires OPENAI_API_KEY)", value=True)
    llm_model = st.text_input("OpenAI model name (e.g., gpt-4o-mini)", value="gpt-4o-mini")

# load checklists
checklists = load_checklists()

# Load or cache vectorstore in session_state
if "vectorstore" not in st.session_state:
    if os.path.exists(VECTORSTORE_DIR):
        try:
            st.session_state.vectorstore = load_vector_store()
        except Exception as e:
            st.session_state.vectorstore = None
            st.warning(f"Could not load vectorstore: {e}")
    else:
        st.session_state.vectorstore = None

vectorstore = st.session_state.vectorstore

# Create LLM if requested & API key present
llm = None
if use_llm:
    if os.environ.get("OPENAI_API_KEY") is None:
        st.warning("OPENAI_API_KEY not found — LLM calls will be skipped.")
        llm = None
    else:
        try:
            llm = create_llm(openai_model=llm_model)
        except Exception as e:
            st.warning(f"Could not create LLM: {e}")
            llm = None

uploaded_files = st.file_uploader("Upload .docx files (multiple allowed)", accept_multiple_files=True, type=["docx"])
if uploaded_files:
    tmp_dir = "tmp_uploads"
    if os.path.exists(tmp_dir) and not os.path.isdir(tmp_dir):
        os.rename(tmp_dir, tmp_dir + "_backup")
    os.makedirs(tmp_dir, exist_ok=True)

    file_paths = []
    for f in uploaded_files:
        path = os.path.join(tmp_dir, f.name)
        with open(path, "wb") as out:
            out.write(f.getbuffer())
        file_paths.append(path)

    # identify process & checklist
    process, matched_docs = identify_process_from_filenames(file_paths, checklists)
    results = checklist_results(process, matched_docs, checklists)
    st.subheader("Checklist Verification")
    st.json(results)

    # rule-based checks
    st.subheader("Rule-based red-flag detection")
    all_issues = []
    annotations_by_file = {}
    for path in file_paths:
        full_text, paragraphs = read_docx_text(path)
        mapped_annotations = run_all_checks(full_text, paragraphs)
        annotations_by_file[path] = mapped_annotations
        for ann in mapped_annotations:
            all_issues.append({
                "document": os.path.basename(path),
                "paragraph_index": ann["paragraph_index"],
                "issue": ann["comment"],
                "severity": ann["severity"],
            })

    # RAG checks on flagged paragraphs
    if vectorstore is None:
        st.info("No vectorstore found. Use the sidebar button to build it from legal_refs/.")
    else:
        st.subheader("RAG checks on flagged paragraphs")
        for path, anns in annotations_by_file.items():
            full_text, paragraphs = read_docx_text(path)
            for ann in anns:
                p_idx = ann["paragraph_index"]
                para_text = paragraphs[p_idx] if p_idx < len(paragraphs) else ""
                try:
                    rag_result = check_clause_with_rag(para_text, vectorstore, llm, k=3)
                except Exception as e:
                    rag_result = {"compliant": None, "issue": f"RAG error: {e}", "suggestion": None, "citation": None}
                ann["suggestion"] = rag_result.get("suggestion")
                ann["citation"] = rag_result.get("citation")
                all_issues.append({
                    "document": os.path.basename(path),
                    "paragraph_index": p_idx,
                    "issue": ann.get("comment"),
                    "severity": ann.get("severity"),
                    "rag_compliant": rag_result.get("compliant"),
                    "rag_issue": rag_result.get("issue"),
                    "rag_suggestion": rag_result.get("suggestion"),
                    "rag_citation": rag_result.get("citation"),
                })

    # ensure outputs folders (safe)
    def safe_mkdir(path):
        if os.path.exists(path) and not os.path.isdir(path):
            os.rename(path, path + "_backup")
        os.makedirs(path, exist_ok=True)

    safe_mkdir("outputs")
    safe_mkdir("outputs/reviewed_docs")
    safe_mkdir("outputs/reports")

    report = {
        "process": process,
        "documents_uploaded": results["documents_uploaded"],
        "required_documents": results["required_documents"],
        "missing_documents": results["missing_documents"],
        "issues_found": all_issues
    }

    report_path = os.path.join("outputs/reports", "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    reviewed_paths = []
    for path, annotations in annotations_by_file.items():
        outname = os.path.basename(path).replace(".docx", "_reviewed.docx")
        outpath = os.path.join("outputs/reviewed_docs", outname)
        save_reviewed_docx(path, annotations, outpath)
        reviewed_paths.append(outpath)

    st.success("Review complete!")

    st.subheader("Downloads")
    for r in reviewed_paths:
        with open(r, "rb") as f:
            st.download_button(label=f"Download reviewed file: {os.path.basename(r)}", data=f.read(), file_name=os.path.basename(r), mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    with open(report_path, "rb") as f:
        st.download_button(label="Download JSON report", data=f.read(), file_name="report.json", mime="application/json")

    st.markdown("### Quick preview of found issues")
    st.table(report["issues_found"])
else:
    st.info("Upload at least one .docx file to start the review.")
