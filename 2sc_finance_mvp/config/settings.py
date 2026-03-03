import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
USER_ID = "1"
JSON_PATH = os.path.join(DATA_DIR, f"user_{USER_ID}.json")

os.makedirs(DATA_DIR, exist_ok=True)

# Value-Add: Auto-Categorization keywords for the SA context
CATEGORIES = {
    "Education": ["college", "rosebank", "unisa"],
    "Groceries": ["woolworths", "pnp", "checkers", "superspar", "clicks"],
    "Transport": ["uber", "bolt", "sasol", "engen", "motors", "flysafair"],
    "Lifestyle": ["mcd", "bk", "liquor", "coffee", "numetro", "disney", "youtube", "lumo"],
    "Financial/Admin": ["settlement", "fee", "notific", "interest", "tax", "charge", "instntlife"],
    "Transfers": ["cashsend", "digital transf", "immediate trf"]
}