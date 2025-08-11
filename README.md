# ADGM-Compliant Corporate Agent with Document Intelligence

## 📌 Overview
This project implements an AI-powered **Corporate Agent** that reviews, validates, and prepares legal documentation for **Abu Dhabi Global Market (ADGM)** compliance.  
It accepts `.docx` files, verifies completeness against official checklists, flags legal issues, inserts contextual comments, and outputs both a marked-up `.docx` file and a structured report.  
It also integrates **Retrieval-Augmented Generation (RAG)** using ADGM official documents for accurate suggestions.

---

## 🚀 Features
- 📂 Upload `.docx` legal documents via a Streamlit interface.
- 🔍 Automatic document classification.
- ✅ Checklist verification for ADGM processes like **Company Incorporation**.
- 📑 Missing document detection with detailed feedback.
- ⚠️ Legal red flag detection (e.g., wrong jurisdiction, missing clauses).
- 📝 Inline commenting in `.docx` with ADGM law references.
- ⬇️ Downloadable reviewed `.docx` files.
- 📊 JSON/Python structured summary report generation.
- 🤖 **RAG-powered** legal clause suggestions using ADGM regulations.

---

## 📂 Folder Structure
```plaintext
ADGM_Corporate_Agent/
├── app.py                 # Streamlit UI entry point
├── doc_checker.py         # Checklist & validation logic
├── doc_utils.py           # .docx parsing, classification, processing
├── rag_utils.py           # RAG pipeline setup and query handling
├── red_flags.py           # Legal red flag detection logic
├── requirements.txt       # Required Python dependencies
├── Task.pdf               # Problem statement
├── README.md              # Project documentation
│
├── outputs/               # Generated outputs (runtime)
│   ├── reviewed_docs/     # Reviewed and commented .docx files
│   └── reports/           # JSON/Python report files
│
├── reference_data/        # ADGM reference docs and law text (for RAG)
└── sample_docs/           # Example input documents for testing


