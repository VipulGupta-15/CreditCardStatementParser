# app.py
import re
import io
import pdfplumber
import pandas as pd
import streamlit as st
from dateutil import parser as dateparser
from typing import Dict, Optional, Any, Tuple, List

# -----------------------
# Utility helpers
# -----------------------

def normalize_spaces(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()

def try_parse_date(text: str) -> Optional[str]:
    try:
        dt = dateparser.parse(text, dayfirst=False, fuzzy=True)
        return dt.date().isoformat()
    except Exception:
        return None

def find_first_regex(text: str, patterns: List[str]) -> Optional[Tuple[str,str]]:
    """Return (pattern, matchgroup) for first match"""
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE|re.DOTALL)
        if m:
            # prefer group(1) if exists
            if m.groups():
                return p, m.group(1).strip()
            return p, m.group(0).strip()
    return None

# -----------------------
# Issuer detection
# -----------------------

def detect_issuer(text: str) -> str:
    t = text.lower()
    # simple keyword-based detection. Extend as needed.
    if "american express" in t or "amex" in t:
        return "American Express"
    if "chase" in t or "chase cardmember" in t:
        return "Chase"
    if "citibank" in t or "citi" in t:
        return "Citi"
    if "bank of america" in t or "bofa" in t:
        return "Bank of America"
    if "hsbc" in t:
        return "HSBC"
    # fallback
    return "Unknown"

# -----------------------
# Parsers per issuer
# -----------------------

def parse_amex(text: str) -> Dict[str, Optional[str]]:
    out = dict.fromkeys(["issuer","last4","card_variant","statement_period","due_date","amount_due"])
    out["issuer"]="American Express"
    # last 4 digits
    m = re.search(r'Card Member since.*|Card ending in[:\s]*?(\d{4})', text, re.IGNORECASE)
    if not m:
        m = re.search(r'ending in[:\s]*?(\d{4})', text, re.IGNORECASE)
    out["last4"] = m.group(1) if m and m.groups() else None

    # variant
    v = find_first_regex(text, [r'(Platinum|Gold|Green|Centurion|Blue|Everyday|Cashback|Corporate)\s+Card', r'American Express\s+([A-Za-z]+)\s+Card'])
    out["card_variant"] = v[1] if v else None

    # statement period
    sp = find_first_regex(text, [r'Statement Period[:\s]*([\w,\s\-/\d]+)', r'Statement Summary\s*Period[:\s]*([\w,\s\-/\d]+)', r'For the period[:\s]*([\w,\s\-/\d]+)'])
    out["statement_period"] = normalize_spaces(sp[1]) if sp else None

    # due date
    dd = find_first_regex(text, [r'Due Date[:\s]*([A-Za-z0-9 ,\-]+)', r'Payment Due Date[:\s]*([A-Za-z0-9 ,\-]+)'])
    out["due_date"] = try_parse_date(dd[1]) if dd else None

    # amount due
    ad = find_first_regex(text, [r'Amount Due[:\s]*\$?([,\d\.]+)', r'Total Amount Due[:\s]*\$?([,\d\.]+)', r'New Balance[:\s]*\$?([,\d\.]+)'])
    out["amount_due"] = ad[1] if ad else None

    return out

def parse_chase(text: str) -> Dict[str, Optional[str]]:
    out = dict.fromkeys(["issuer","last4","card_variant","statement_period","due_date","amount_due"])
    out["issuer"]="Chase"
    # last 4
    m = re.search(r'Account ending in[:\s]*?(\d{4})', text, re.IGNORECASE) or re.search(r'Card ending in[:\s]*?(\d{4})', text, re.IGNORECASE)
    out["last4"] = m.group(1) if m else None

    # variant
    v = find_first_regex(text, [r'(Sapphire|Freedom|Ink|Slate|Preferred|Reserve|Bold)\s+(?:Card|Account|Cardmember)?', r'Chase\s+([A-Za-z]+)\s+Card'])
    out["card_variant"] = v[1] if v else None

    # statement period
    sp = find_first_regex(text, [r'Statement Period[:\s]*([\w,\s\-/\d]+)', r'For the period[:\s]*([\w,\s\-/\d]+)'])
    out["statement_period"] = normalize_spaces(sp[1]) if sp else None

    # due date
    dd = find_first_regex(text, [r'Payment Due Date[:\s]*([A-Za-z0-9 ,\-]+)', r'Due Date[:\s]*([A-Za-z0-9 ,\-]+)'])
    out["due_date"] = try_parse_date(dd[1]) if dd else None

    # amount due
    ad = find_first_regex(text, [r'Total Amount Due[:\s]*\$?([,\d\.]+)', r'New Balance[:\s]*\$?([,\d\.]+)', r'Amount Due[:\s]*\$?([,\d\.]+)'])
    out["amount_due"] = ad[1] if ad else None

    return out

def parse_citi(text: str) -> Dict[str, Optional[str]]:
    out = dict.fromkeys(["issuer","last4","card_variant","statement_period","due_date","amount_due"])
    out["issuer"]="Citi"
    # last4
    m = re.search(r'Card ending in[:\s]*?(\d{4})', text, re.IGNORECASE) or re.search(r'ending in (\d{4})', text, re.IGNORECASE)
    out["last4"] = m.group(1) if m else None

    # variant
    v = find_first_regex(text, [r'(Premier|Prestige|Gold|Platinum|Custom|Simplicity|Double Cash|Double)\s+Card', r'Citi\s+([A-Za-z]+)\s+Card'])
    out["card_variant"] = v[1] if v else None

    # statement period
    sp = find_first_regex(text, [r'Statement Period[:\s]*([\w,\s\-/\d]+)', r'Statement Date[:\s]*([\w,\s\-/\d]+)'])
    out["statement_period"] = normalize_spaces(sp[1]) if sp else None

    # due date
    dd = find_first_regex(text, [r'Payment Due Date[:\s]*([A-Za-z0-9 ,\-]+)', r'Due Date[:\s]*([A-Za-z0-9 ,\-]+)'])
    out["due_date"] = try_parse_date(dd[1]) if dd else None

    # amount due
    ad = find_first_regex(text, [r'Total Amount Due[:\s]*\$?([,\d\.]+)', r'Amount due now[:\s]*\$?([,\d\.]+)', r'Current Due[:\s]*\$?([,\d\.]+)'])
    out["amount_due"] = ad[1] if ad else None

    return out

def parse_bofa(text: str) -> Dict[str, Optional[str]]:
    out = dict.fromkeys(["issuer","last4","card_variant","statement_period","due_date","amount_due"])
    out["issuer"]="Bank of America"
    # last4
    m = re.search(r'Account Number[:\s]*\*+(\d{4})', text, re.IGNORECASE) or re.search(r'ending in (\d{4})', text, re.IGNORECASE)
    out["last4"] = m.group(1) if m else None

    # variant
    v = find_first_regex(text, [r'(Preferred|Platinum|Cash Rewards|Travel Rewards|Customized Cash Rewards)\s+Card', r'Bank of America\s+([A-Za-z]+)\s+Card'])
    out["card_variant"] = v[1] if v else None

    # statement period
    sp = find_first_regex(text, [r'Statement Period[:\s]*([\w,\s\-/\d]+)', r'Activity Period[:\s]*([\w,\s\-/\d]+)'])
    out["statement_period"] = normalize_spaces(sp[1]) if sp else None

    # due date
    dd = find_first_regex(text, [r'Payment Due Date[:\s]*([A-Za-z0-9 ,\-]+)', r'Due Date[:\s]*([A-Za-z0-9 ,\-]+)'])
    out["due_date"] = try_parse_date(dd[1]) if dd else None

    # amount due
    ad = find_first_regex(text, [r'Total Due[:\s]*\$?([,\d\.]+)', r'Amount Due[:\s]*\$?([,\d\.]+)', r'Current Balance[:\s]*\$?([,\d\.]+)'])
    out["amount_due"] = ad[1] if ad else None

    return out

def parse_hsbc(text: str) -> Dict[str, Optional[str]]:
    out = dict.fromkeys(["issuer","last4","card_variant","statement_period","due_date","amount_due"])
    out["issuer"]="HSBC"
    # last4
    m = re.search(r'Card number[:\s]*\*+(\d{4})', text, re.IGNORECASE) or re.search(r'ending in[:\s]*(\d{4})', text, re.IGNORECASE)
    out["last4"] = m.group(1) if m else None

    # variant
    v = find_first_regex(text, [r'(Premier|Advance|Platinum|Gold|Red)\s+Card', r'HSBC\s+([A-Za-z]+)\s+Card'])
    out["card_variant"] = v[1] if v else None

    # statement period
    sp = find_first_regex(text, [r'Statement Period[:\s]*([\w,\s\-/\d]+)', r'Account summary for the period[:\s]*([\w,\s\-/\d]+)'])
    out["statement_period"] = normalize_spaces(sp[1]) if sp else None

    # due date
    dd = find_first_regex(text, [r'Due Date[:\s]*([A-Za-z0-9 ,\-]+)', r'Payment Due Date[:\s]*([A-Za-z0-9 ,\-]+)'])
    out["due_date"] = try_parse_date(dd[1]) if dd else None

    # amount due
    ad = find_first_regex(text, [r'Total Amount Due[:\s]*\$?([,\d\.]+)', r'Amount Due[:\s]*\$?([,\d\.]+)', r'Total due[:\s]*\$?([,\d\.]+)'])
    out["amount_due"] = ad[1] if ad else None

    return out

# -----------------------
# Generic fallback parser
# -----------------------

def parse_generic(text: str) -> Dict[str, Optional[str]]:
    out = dict.fromkeys(["issuer","last4","card_variant","statement_period","due_date","amount_due"])
    out["issuer"]="Unknown"
    # common patterns
    last4 = find_first_regex(text, [r'ending in[:\s]*?(\d{4})', r'Account Number[:\s]*\*+(\d{4})', r'Card\s+ending[:\s]*?(\d{4})'])
    out["last4"] = last4[1] if last4 else None

    variant = find_first_regex(text, [r'(Platinum|Gold|Silver|Classic|Cashback|Rewards|Signature|Infinite)\s+(?:Card|Account)', r'Card Type[:\s]*([A-Za-z0-9 ]+)'])
    out["card_variant"] = variant[1] if variant else None

    sp = find_first_regex(text, [r'(Statement Period|Statement Date|For the period)[:\s]*([\w,\s\-/\d]+)', r'For the period[:\s]*([\w,\s\-/\d]+)'])
    out["statement_period"] = normalize_spaces(sp[1]) if sp else None

    dd = find_first_regex(text, [r'(Payment Due Date|Due Date)[:\s]*([A-Za-z0-9 ,\-]+)'])
    out["due_date"] = try_parse_date(dd[1]) if dd else None

    ad = find_first_regex(text, [r'(Total Amount Due|Amount Due|New Balance|Current Balance)[:\s]*\$?([,\d\.]+)'])
    out["amount_due"] = ad[1] if ad else None

    return out

# -----------------------
# Master extraction pipeline
# -----------------------

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    full_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        # try to extract page-wise text (stop early if first pages have content)
        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text:
                full_text.append(text)
        # fallback: if pdfplumber couldn't extract text, try reading all pages' .extract_text() anyway
    return "\n\n".join(full_text)

def parse_statement(pdf_bytes: bytes) -> Dict[str, Any]:
    text = extract_text_from_pdf_bytes(pdf_bytes)
    text_norm = normalize_spaces(text)
    issuer = detect_issuer(text_norm)
    # pick parser by issuer
    if issuer == "American Express":
        result = parse_amex(text_norm)
    elif issuer == "Chase":
        result = parse_chase(text_norm)
    elif issuer == "Citi":
        result = parse_citi(text_norm)
    elif issuer == "Bank of America":
        result = parse_bofa(text_norm)
    elif issuer == "HSBC":
        result = parse_hsbc(text_norm)
    else:
        result = parse_generic(text_norm)

    result["raw_sample_snippet"] = text_norm[:1200]  # a short snippet for debugging
    return result

# -----------------------
# Streamlit UI
# -----------------------

st.set_page_config(page_title="Credit Card Statement Parser", layout="wide")
st.title("Credit Card Statement Parser — Streamlit")
st.markdown("""
Upload one or more credit card statement PDFs. The app will attempt to detect the issuer and extract 5 key fields:
- Card last 4 digits
- Card variant
- Statement period
- Payment due date
- Total amount due

Built for demonstration and grading purposes. Do NOT upload sensitive live PDFs you are not allowed to share.
""")

uploaded_files = st.file_uploader("Upload statement PDF(s)", type=["pdf"], accept_multiple_files=True)
examples_col, controls_col = st.columns([3,1])

if uploaded_files:
    results = []
    progress_placeholder = st.empty()
    for i, uploaded in enumerate(uploaded_files):
        with st.spinner(f"Parsing {uploaded.name} ..."):
            pdf_bytes = uploaded.read()
            parsed = parse_statement(pdf_bytes)
            parsed["filename"] = uploaded.name
            results.append(parsed)
            progress_placeholder.info(f"Parsed {i+1}/{len(uploaded_files)}")
    progress_placeholder.empty()

    # show results table
    df = pd.DataFrame([{
        "filename": r.get("filename"),
        "issuer": r.get("issuer"),
        "last4": r.get("last4"),
        "card_variant": r.get("card_variant"),
        "statement_period": r.get("statement_period"),
        "due_date": r.get("due_date"),
        "amount_due": r.get("amount_due")
    } for r in results])

    st.subheader("Extraction Results")
    st.dataframe(df, use_container_width=True)

    # show detail per file
    for r in results:
        with st.expander(f"Details — {r['filename']} (detected: {r['issuer']})", expanded=False):
            st.markdown("**Extracted fields**")
            st.write({
                "Issuer": r.get("issuer"),
                "Last 4": r.get("last4"),
                "Card variant": r.get("card_variant"),
                "Statement period": r.get("statement_period"),
                "Payment due date (parsed ISO)": r.get("due_date"),
                "Amount due": r.get("amount_due")
            })
            st.markdown("**Raw text snippet (first 1200 chars)**")
            st.code(r.get("raw_sample_snippet") or "(no text)", language="text")

    # CSV download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download results as CSV", data=csv, file_name="parsed_statements.csv", mime="text/csv")

else:
    st.info("Upload PDF statement(s) to begin.")

# -----------------------
# Developer / testing helpers
# -----------------------
st.markdown("---")
st.markdown("### Notes & Tips")
st.markdown("""
- If extraction misses fields, try visually inspecting the raw snippet shown in the details expander — statement layouts vary widely.
- You can add or tune regex patterns in the parser functions for each issuer (functions named `parse_amex`, `parse_chase`, etc.).
- For heavy-duty production parsing consider: OCR for scanned PDFs (Tesseract/Adobe OCR), layout models (Grobid-style or ML models), or table extraction tools if transactions table must be parsed.
""")
