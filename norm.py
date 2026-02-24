import pandas as pd
import jdatetime
import re

# ---------------- CONFIG ----------------
INPUT_CSV = "mftplus_courses_async.csv"
OUTPUT_CSV = "courses_normalized.csv"

# ---------------- HELPERS ----------------
FA_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

MONTHS_FA = {
    "فروردین": 1, "اردیبهشت": 2, "خرداد": 3,
    "تیر": 4, "مرداد": 5, "شهریور": 6,
    "مهر": 7, "آبان": 8, "آذر": 9,
    "دی": 10, "بهمن": 11, "اسفند": 12
}

def fa_to_en(val):
    if pd.isna(val):
        return None
    return str(val).translate(FA_TO_EN)

def normalize_price(val):
    if not val or pd.isna(val):
        return None
    val = fa_to_en(val).replace(",", "")
    return int(val) if val.isdigit() else None

def normalize_bool(val):
    try:
        return bool(int(val))
    except:
        return False

def normalize_jalali_date(text):
    if not text or pd.isna(text):
        return None

    text = fa_to_en(text)
    match = re.search(r"(\d{1,2}) (\w+) (\d{4})", text)
    if not match:
        return None

    day, month_fa, year = match.groups()
    month = MONTHS_FA.get(month_fa)
    if not month:
        return None

    jd = jdatetime.date(int(year), month, int(day))
    return jd.togregorian().isoformat()

def normalize_updated_at(val):
    if not val or pd.isna(val):
        return None
    # فقط تاریخ قبل از فاصله
    return str(val).split(" ")[0]

# ---------------- MAIN ----------------
df = pd.read_csv(INPUT_CSV)

rows = []

for _, row in df.iterrows():
    rows.append({
        "id": str(row.get("id")),
        "title": row.get("title"),
        "department": row.get("department"),
        "center": row.get("center"),
        "teacher": None if row.get("teacher") in ["مشخص نشده", "", None] else row.get("teacher"),

        "start_date": normalize_jalali_date(row.get("start_date")),
        "end_date": normalize_jalali_date(row.get("end_date")),

        "capacity": int(fa_to_en(row.get("capacity"))) if not pd.isna(row.get("capacity")) else None,
        "duration_hours": int(fa_to_en(row.get("duration_hours"))) if not pd.isna(row.get("duration_hours")) else None,

        "days": fa_to_en(row.get("days")),

        "min_price": normalize_price(row.get("min_price")),
        "max_price": normalize_price(row.get("max_price")),

        "is_active": normalize_bool(row.get("is_active")),

        # فقط تاریخ
        "updated_at": normalize_updated_at(row.get("updated_at")),
    })

normalized_df = pd.DataFrame(rows)

# ---------------- SAVE ----------------
normalized_df.to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig"
)

print(f"✅ Normalized CSV saved to: {OUTPUT_CSV}")