import pdfplumber
import pytesseract
import cv2
import numpy as np
import io
import pandas as pd
import re

def clean_amount_safe(val_str):
    """Correctly handles SA formats like '24 835,46' without multiplying by 100."""
    if not val_str or str(val_str).strip().lower() in ["none", "", "r0.00"]:
        return 0.0
    
    clean = str(val_str).replace("R", "").replace(" ", "").strip()
    clean = clean.replace("-", "")
    
    punctuations = [i for i, char in enumerate(clean) if char in [",", "."]]
    if punctuations:
        last_idx = punctuations[-1]
        whole = re.sub(r"[,.]", "", clean[:last_idx])
        decimal = clean[last_idx+1:]
        clean = f"{whole}.{decimal}"
    
    try:
        return float(clean)
    except:
        return 0.0

# --- THE FIX: We define the categorization logic here so the parser can use it directly ---
def categorize_transaction(description, amount):
    desc = str(description).upper()
    amt = abs(amount)
    
    # Priority 1: Critical Infrastructure (Check these before anything else)
    if any(x in desc for x in ["STEPUP", "4101731287", "BRUMA LAKE", "Rent", "161A1C0DD1"]):
        return 'Rent & Accommodation'
    
    # 2. Tax & Government (New Category for SARS)
    if "SARS" in desc:
        return 'Tax & Government'

    # Priority 3: Debt Servicing
    if "DC INTERNAL ABSACC" in desc or "110000050965" in desc:
        return 'Credit Card Payment'
    
    # Priority 4: Reversals
    if amount > 0:
        if any(x in desc for x in ['UNPAID', 'UNSUCCESSFUL', 'REVERSAL', 'RETURN']):
            return 'Payment Reversal' 
            
    # Priority 5: Internal Credit Card Management
    if any(x in desc for x in ["47876926", "40382280", "110000050965", "478769"]):
        if amount > 0:
            return 'Internal Transfer' 
        else:
            return 'Credit Card Payment'
            
    # Priority 5: Savings & Emergency
    if "EMERGENCY" in desc:
        return 'Emergency Fund'
        
    # Priority 6: Income
    if amount > 0:
        if any(x in desc for x in ["NPF CREDIT", "SALARY", "THE PRIME", "BIMBO"]):
            return 'Monthly Income'
        return 'Other Credits'

    # Priority 7: Lifestyle & General
    if any(x in desc for x in ['CHECKERS', 'PNP', 'SPAR', 'WOOLWORTHS', 'MEAT WORLD', 'FLM']):
        return 'Groceries & Essentials'
    if any(x in desc for x in ['LUMO LOUNGE', 'LIQUORSHOP']):
        return 'Entertainment'
    if any(x in desc for x in ['UBER', 'BOLT', 'SASOL']):
        return 'Transport & Travel'
    if any(x in desc for x in ['INSTNTLIFE', 'CLICKS', 'DISCHEM', 'MEDICAL']):
        return 'Health & Insurance'
    if any(x in desc for x in ['CASHSEND', 'DIGITAL TRANSF', 'ABSA BANK TRANSFER', 'INTERNAL TRANSF']):
        return 'Internal Transfers'

    return 'General Spending'

def parse_absa_robust(file_bytes):
    """
    Text-based parsing. 
    Uses the unified categorize_transaction logic to ensure Phase 2 consistency.
    """
    txns = []
    # Matches both YYYY-MM-DD and DD/MM/YYYY
    date_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})")
    money_pattern = re.compile(r'(-?R?\s?\d{1,3}(?:[ ,.]\d{3})*[.,]\d{2}-?)')
    
    current_date = None # STICKY DATE: Keep the last seen date

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or "Balance Brought Forward" in line or "Transaction Description" in line:
            continue

        # Check for date
        date_match = date_pattern.search(line)
        if date_match:
            current_date = date_match.group(1)

        # Check for money (Amount and Balance)
        amounts = money_pattern.findall(line)
        
        # We need a date AND at least two money figures to define a transaction
        if current_date and len(amounts) >= 2:
            amt_str = amounts[-2]
            bal_str = amounts[-1]
            
            raw_amt = clean_amount_safe(amt_str)
            raw_bal = clean_amount_safe(bal_str)
            
            # Clean description
            desc = line
            if date_match:
                desc = desc.replace(current_date, "", 1)
            for m in amounts:
                desc = desc.replace(m, "")
            
            desc = re.sub(r"CARD NO\.\s?\d{4}", "", desc, flags=re.IGNORECASE)
            desc = " ".join(desc.split()).strip().upper()

            # Sign correction
            is_neg = "-" in amt_str or amt_str.endswith("-")
            is_cr = any(x in desc for x in [" CR ", "CREDIT", "FROM "])
            final_amt = -abs(raw_amt) if (is_neg or not is_cr) else abs(raw_amt)

            # Categorize
            cat = categorize_transaction(desc, final_amt)

            # Date formatting
            try:
                if '-' in current_date:
                    clean_dt = pd.to_datetime(current_date).date()
                else:
                    clean_dt = pd.to_datetime(current_date, dayfirst=True).date()
            except:
                continue

            txns.append({
                "date": clean_dt,
                "description": desc,
                "amount": final_amt,
                "balance": raw_bal,
                "category": cat
            })

    return sorted(txns, key=lambda x: x['date']) if txns else []

def parse_receipt_ocr(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    
    amounts = re.findall(r"(\d+[\.,]\d{2})", text)
    detected_amount = float(amounts[-1].replace(",", ".")) if amounts else 0.0
    return {"text": text, "amount": detected_amount}