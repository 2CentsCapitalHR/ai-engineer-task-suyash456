# utils/doc_checker.py
import json
import os

def load_checklists(path="checklists/company_incorp.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def identify_process_from_filenames(filenames, checklists):
    """
    Very simple heuristic:
    - If filenames contain 'articles' or 'aoa' => assume Company Incorporation
    - If filenames contain 'memorandum' or 'moa' => incorporation
    Returns process_name, matched_docs_list
    """
    lower_names = [os.path.basename(fn).lower() for fn in filenames]
    # currently only Company Incorporation is in checklist
    process = None
    matched = []
    if any(("articles" in n) or ("aoa" in n) for n in lower_names) or any(("memorandum" in n) or ("moa" in n) for n in lower_names):
        process = "Company Incorporation"
        # find which required docs appear in filenames
        required = checklists.get(process, [])
        for r in required:
            r_lower = r.lower()
            # simple match
            if any(r_lower.split()[0] in n for n in lower_names):
                matched.append(r)
    # fallback: if no match, still default to Company Incorporation if filenames non-empty
    if not process and filenames:
        process = "Company Incorporation"
    return process, matched

def checklist_results(process_name, matched_docs, checklists):
    required = checklists.get(process_name, [])
    missing = [d for d in required if d not in matched_docs]
    return {
        "process": process_name,
        "documents_uploaded": len(matched_docs),
        "required_documents": len(required),
        "missing_documents": missing
    }
