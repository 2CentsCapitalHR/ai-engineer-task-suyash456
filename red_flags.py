# utils/red_flags.py
import re

# Simple rule checks
def detect_wrong_jurisdiction(text):
    """
    Returns list of matches where a jurisdiction other than ADGM is referenced.
    For MVP, we flag references to 'UAE Federal' or 'DIFC' as wrong.
    """
    issues = []
    patterns = [
        (r"\bUAE Federal (Court|Courts|law|laws)\b", "References UAE Federal Courts instead of ADGM Courts"),
        (r"\bDIFC\b", "References DIFC instead of ADGM"),
        (r"\bUnited Arab Emirates Federal Courts\b", "References UAE Federal Courts instead of ADGM Courts")
    ]
    for pat, msg in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            issues.append({"match": m.group(0), "message": msg, "start": m.start(), "end": m.end(), "severity": "High"})
    return issues

def detect_missing_signature_block(paragraphs):
    """
    Very naive: look for paragraphs that look like signature headings
    If none found, flag missing signature block.
    """
    joined = "\n".join(paragraphs)
    if re.search(r"(signature|signed by|for and on behalf|authorised signatory|signature:)", joined, flags=re.IGNORECASE):
        return []
    else:
        return [{"match": None, "message": "No signature block detected in document.", "severity": "High"}]

def detect_ambiguous_language(text):
    """
    Look for common ambiguous non-binding phrases like 'may', 'endeavour', 'best endeavours'
    Flag their occurrences as Medium severity.
    """
    issues = []
    for pat in [r"\bmay\b", r"\bmight\b", r"\bendeavour\b", r"\bbest endeavours\b", r"\bbest efforts\b"]:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            issues.append({"match": m.group(0), "message": f"Ambiguous/non-binding phrase: '{m.group(0)}'", "start": m.start(), "end": m.end(), "severity": "Medium"})
    return issues

def run_all_checks(text, paragraphs):
    issues = []
    issues += detect_wrong_jurisdiction(text)
    issues += detect_ambiguous_language(text)
    issues += detect_missing_signature_block(paragraphs)
    # Map location to paragraph indexes for annotation
    # For simplicity, map each issue to likely paragraph index by searching paragraph text
    mapped = []
    for iss in issues:
        para_idx = -1
        if iss.get("match"):
            for i,p in enumerate(paragraphs):
                if iss["match"].lower() in p.lower():
                    para_idx = i
                    break
        if para_idx == -1:
            # default to top of doc
            para_idx = 0
        mapped.append({
            "paragraph_index": para_idx,
            "flag_text": iss.get("match") or "",
            "comment": iss.get("message"),
            "severity": iss.get("severity","Medium")
        })
    return mapped
