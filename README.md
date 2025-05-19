# Second Story Finance MVP

A lightweight Streamlit-based MVP for parsing South African bank statements (PDF/CSV), extracting transactions, auto-detecting debits vs. credits, auto-categorizing them, and visualizing in a simple dashboard.

## Features

1. **Statement Upload & Parsing**

   * Upload ABSA (and CSV) statements via file picker.
   * Extract text with `pdfplumber` and `pytesseract` OCR fallback.
   * Regex-based line parsing for date, description, amount, balance.
2. **Debit vs. Credit Detection**

   * Compare successive balances to compute actual transaction amount.
3. **Auto-categorization**

   * Categorize transactions by keywords (e.g., `"uber eats"` → `Food/Delivery`).
4. **Storage**

   * Persist transactions in JSON: `data/user_1.json`.
5. **Review & Edit**

   * In-app data editor to correct descriptions, amounts, or categories.
6. **Dashboard**

   * **Metrics:** Total Income & Total Expenses.
   * **Spend by Category:** Bar chart of categorized spend.
   * **Monthly Trend:** Line chart of cumulative spending over time.

## Tech Stack

* **Python 3.10+**
* [Streamlit](https://streamlit.io/) for UI
* [pdfplumber](https://github.com/jsvine/pdfplumber) + [pytesseract](https://github.com/madmaze/pytesseract) for PDF text extraction
* [Pandas](https://pandas.pydata.org/) for CSV parsing & DataFrame

## Installation & Usage

```bash
# Clone the repo
git clone https://github.com/OCTAVIAKOMSKAIKRU/documentation.git
cd documentation

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py
```

Once running, open [http://localhost:8501](http://localhost:8501) in your browser:

1. **Upload**: Choose a PDF or CSV statement.
2. **Review**: Validate extracted transactions and edit if needed.
3. **Dashboard**: View income, expenses, category breakdown, and trends.

## Next Steps

* Add **Export** feature (download JSON or CSV).
* Build **automated tagging** for merchant-based categories.
* Integrate user **authentication** & multi-user support.

---

*Second Story Group © 2025*

