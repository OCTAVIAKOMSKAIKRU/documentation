# 📊 Second Story Finance | MVP (Phase 2)

A robust, secure financial intelligence platform designed to transform raw South African bank statements into actionable insights. This version elevates the MVP from simple parsing to a multi-user, database-backed ecosystem with duplicate protection and a persistent "Financial Archive."

## 🚀 Core Capabilities

### 1. Secure Authentication & Multi-Tenancy

* **Encrypted Access:** User registration and login powered by `bcrypt` password hashing.
* **Session Management:** Persistent user sessions to ensure data privacy and isolated financial ledgers.

### 2. Advanced Sync Ledger (The Engine)

* **Robust Parsing:** High-accuracy extraction for ABSA PDF statements using `pdfplumber`.
* **Receipt Stitching:** OCR-powered receipt scanning using `pytesseract` and `OpenCV` to match physical slips to bank records.
* **Sign Correction:** Intelligent logic to distinguish between Credits (Income) and Debits (Expenses) based on balance fluctuations.

### 3. The Financial Vault (Document Management)

* **Integrity Protection:** SHA-256 file hashing to prevent duplicate statement uploads and double-counting of transactions.
* **Relational Storage:** Documents are stored as "Parent" records in MySQL, allowing for a cascading cleanup—delete a document, and its associated transactions are purged automatically.
* **Archive Management:** Users can rename, delete, and audit their history of uploaded statements.

### 4. Intelligence & Insights

* **Critical Trackers:** Specialized logic to track "Infrastructure" costs like Rent, Debt Servicing, and SARS payments.
* **Auto-Categorization:** Keyword-based classification engine (e.g., `Checkers` → `Groceries`).
* **Real-Time Metrics:** Dynamic calculation of Total Spend, Savings Rate, and Monthly Trends.

## 🛠️ Tech Stack

* **Frontend:** [Streamlit](https://streamlit.io/) (High-performance UI)
* **Database:** [MySQL](https://www.mysql.com/) (Relational Data & Integrity)
* **ORMs/Drivers:** `SQLAlchemy` & `mysql-connector-python`
* **Security:** `bcrypt` (Hashing) & `python-dotenv` (Secret Management)
* **Data Science:** `Pandas` & `NumPy`
* **OCR/Vision:** `pdfplumber`, `pytesseract`, and `OpenCV`

## ⚙️ Installation & Setup

```bash
# 1. Clone & Navigate
git clone https://github.com/OCTAVIAKOMSKAIKRU/documentation.git
cd documentation

# 2. Environment Setup
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Database Configuration
# Create a .env file in the root directory:
DB_HOST=localhost
DB_USER=root
DB_PASS=yourpassword
DB_NAME=second_story
DB_PORT=3306

```

## 🏗️ Database Schema Overview

The system automatically initializes the following relational structure:

* **`users`**: Secure credentials and timestamps.
* **`documents`**: Metadata for PDFs/Receipts, including file hashes for duplicate prevention.
* **`transactions`**: The ledger, linked via `doc_id` to the parent document and `user_id` to the owner.

## 📈 Engineering Standards

* **Atomic Deletes:** Uses `ON DELETE CASCADE` to ensure no orphaned transactions remain when a document is removed.
* **Batch Processing:** Uses `executemany` for 10x faster database writes compared to standard loops.
* **State Synchronization:** Streamlit session state is synchronized with MySQL to ensure a "Single Source of Truth."

## 🛣️ Roadmap: Towards Phase 3

* **Predictive Budgeting:** AI-driven forecasting of upcoming month-end balances.
* **Export Engine:** Generate professional-grade PDF/Excel financial reports.
* **Direct API Integration:** Connecting directly to South African banking APIs for real-time syncing.

---

*Second Story Group © 2025 | Secure. Transparent. Robust.*

