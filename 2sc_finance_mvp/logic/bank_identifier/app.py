import streamlit as st
import PyPDF2
import re
import pandas as pd

# Bank Keywords for Identification
BANK_MARKERS = {
    'Standard Bank': ['standard bank', 'sbsa'],
    'Nedbank': ['nedbank', 'nedgroup'],
    'Capitec': ['capitec', 'global one'],
    'FNB': ['fnb', 'first national bank', 'fnb app'],
    'Absa': ['absa', 'authorise financial services provider']
}

def identify_bank_from_text(text):
    text_lower = text.lower()
    for bank_name, markers in BANK_MARKERS.items():
        if any(marker in text_lower for marker in markers):
            return bank_name
    return "Unknown Bank"

def bank_identifier_logic(uploaded_file):
    """
    Seamlessly identifies and routes the file to the correct parser.
    """
    if uploaded_file is not None:
        reader = PyPDF2.PdfReader(uploaded_file)
        first_page_text = reader.pages[0].extract_text()
        
        bank_name = identify_bank_from_text(first_page_text)
        st.info(f"Detected Statement Source: {bank_name}")
        
        # In Phase 3, these will call the specific parsing functions
        if bank_name == "FNB":
            # call fnb_parser(uploaded_file)
            pass
        elif bank_name == "Nedbank":
            # call nedbank_parser(uploaded_file)
            pass
        elif bank_name == "Standard Bank":
            # call standard_bank_parser(uploaded_file)
            pass
        else:
            st.warning("Standard Absa processing applied by default.")
            
    return bank_name