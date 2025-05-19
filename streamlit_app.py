import os, io, re, json
from datetime import date
import datetime
import pandas as pd
import pypdfium2 as pdfium
import streamlit as st
import pdfplumber
import pytesseract
from PIL import Image
import io

# ─── CONFIG ─────────────────────────────────────────────────────────
DATA_DIR = "data"
USER_ID = "1"
JSON_PATH = os.path.join(DATA_DIR, f"user_{USER_ID}.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ─── PARSERS ─────────────────────────────────────────────────────────
@st.cache_data
def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # try text first
            txt = page.extract_text() or ""
            if not txt.strip():
                # fallback to OCR on a page image
                img = page.to_image(resolution=200).original
                txt = pytesseract.image_to_string(img)
            text_pages.append(txt)
    return "\n".join(text_pages)


def parse_absa_pdf(file_bytes: bytes) -> list[dict]:
    raw = extract_text_from_pdf(file_bytes)
    lines = raw.splitlines()
    st.sidebar.text_area("PDF Preview (first 2600 chars)", raw[:2600], height=200)

    txns = []
    line_re = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4})\s+(.+?)\s+([\d,.]+)\s+([\d,.]+)$")

    for line in lines:
        line = line.strip()
        match = line_re.match(line)
        if not match:
            continue
        date_str, desc, amt_str, bal_str = match.groups()
        try:
            d = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
            amt = float(amt_str.replace(",", ""))
            bal = float(bal_str.replace(",", ""))

            txns.append({
                "date": d.isoformat(),
                "description": desc,
                "raw_amount": amt,     # keep raw amount for comparison
                "balance": bal
            })
        except Exception:
            continue

    # Infer direction (debit/credit) based on balance difference
    for i in range(len(txns)):
        if i == 0:
            # First row — can't compare, default to positive
            txns[i]["amount"] = txns[i]["raw_amount"]
        else:
            prev_bal = txns[i - 1]["balance"]
            curr_bal = txns[i]["balance"]
            delta = round(curr_bal - prev_bal, 2)
            txns[i]["amount"] = delta

        del txns[i]["raw_amount"]  # clean up

    if not txns:
        st.warning("No transactions matched. Tweak the parser.")
    return txns




def parse_csv_file(file_bytes: bytes) -> list[dict]:
    s = file_bytes.decode("utf-8", errors="ignore")
    df = pd.read_csv(io.StringIO(s))
    txns=[]
    for _, row in df.iterrows():
        raw_date = str(row.get("Date", row.get("Transaction Date", "")))
        date_str = raw_date.splitlines()[0].strip()
        dt = pd.to_datetime(date_str, dayfirst=True)
        debit  = float(row.get("Debit", 0) or 0)
        credit = float(row.get("Credit", 0) or 0)
        bal    = float(str(row.get("Balance", row.get("Running Balance", 0))).replace(",", ""))
        amt = credit - debit
        txns.append({"date": date_str, "description": row.get("Description", row.get("Narrative","")).strip(), "amount": amt, "balance": bal})
    return txns

# ─── STORAGE ─────────────────────────────────────────────────────────
def load_transactions():
    return json.load(open(JSON_PATH)) if os.path.exists(JSON_PATH) else []

def save_transactions(txns):
    with open(JSON_PATH, "w") as f:
        json.dump(txns, f, indent=2, default=str)

# ─── UI ──────────────────────────────────────────────────────────────
st.title("📊 Second Story Finance MVP")
st.sidebar.header("1. Upload Statement")

# Upload widgets
up1 = st.sidebar.file_uploader("PDF/CSV (sidebar)", type=["pdf","csv"])
up2 = st.file_uploader("Or upload here", type=["pdf","csv"])
uploaded = up1 or up2

if uploaded:
    raw = uploaded.read()
    fname = uploaded.name.lower()

    if fname.endswith(".csv"):
        txns = parse_csv_file(raw)
    else:
        txns = parse_absa_pdf(raw)

    all_txns = load_transactions()
    all_txns.extend(txns)

    # dedupe
    seen, unique = set(), []
    for t in all_txns:
        key = (t['date'], t['description'], t['amount'])
        if key not in seen:
            seen.add(key)
            unique.append(t)

    save_transactions(unique)
    st.success(f"✅ {len(txns)} transactions added, {len(unique)} total now")

# Show where we store data and confirm it's working
    st.sidebar.markdown("✅ **Data saved to:**")
    st.sidebar.code(os.path.abspath(JSON_PATH))
    st.sidebar.markdown("📄 **Saved transactions:**")
    st.sidebar.json(unique if unique else {})

# Review section
st.header("2. Review Transactions")
txns = load_transactions()
if txns:
    df = pd.DataFrame(txns)
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("Save Edits"):
        save_transactions(edited.to_dict("records"))
        st.success("Changes saved")
else:
    st.info("No transactions found. Upload first.")

# Dashboard
st.header("3. Dashboard Stub")
if txns:
    df = pd.DataFrame(txns)
    st.metric("Total Income", f"R {df[df.amount>0].amount.sum():,.2f}")
    st.metric("Total Expenses", f"R {-df[df.amount<0].amount.sum():,.2f}")

    st.subheader("Spend by Category")
    cat = df.assign(cat="Uncategorized").groupby("cat")["amount"].sum().abs()
    st.bar_chart(cat)

    st.subheader("Monthly Trend")
    df['mon'] = pd.to_datetime(df.date).dt.to_period('M').astype(str)
    trend = df.groupby('mon')['amount'].sum().cumsum()
    st.line_chart(trend)
else:
    st.info("No data to display on dashboard.")
