import aiohttp
import asyncio
import pandas as pd
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote

# ---------------- Configuration ----------------
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
API_URL = "https://mftplus.com/ajax/default/calendar?need=search"
PAGE_SIZE = 9
MAX_CONCURRENCY = 5
MAX_EMPTY_PAGES = 2

CSV_FILE = "mftplus_courses_async.csv"
JSON_FILE = "mftplus_courses_async.json"
LOG_FILE = "COURSE_LOG.md"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://mftplus.com/calendar"
}

# ---------------- Load JSON samples ----------------
with open("data/places.json", encoding="utf-8") as f:
    places_data = json.load(f)
with open("data/departments.json", encoding="utf-8") as f:
    departments_data = json.load(f)
with open("data/groups.json", encoding="utf-8") as f:
    groups_data = json.load(f)
with open("data/courses.json", encoding="utf-8") as f:
    courses_data = json.load(f)
with open("data/months.json", encoding="utf-8") as f:
    months_data = json.load(f)

# ---------------- Helper functions ----------------
def multi_select(options, key_name="title"):
    """Prompt user to select multiple options"""
    if not options:
        return []

    print("\nSelect options (comma-separated numbers, or empty for none):")
    for i, opt in enumerate(options):
        print(f"{i+1}. {opt.get(key_name, 'N/A')}")
    selected = input("Your choice: ").strip()
    
    if not selected:
        return []

    indices = []
    for s in selected.split(","):
        s = s.strip()
        if s.isdigit():
            idx = int(s) - 1
            if 0 <= idx < len(options):
                indices.append(idx)
    return [options[i] for i in indices]

def get_ids(items):
    """Extract IDs from items"""
    return [
        item["id"]["$oid"] if isinstance(item.get("id"), dict) else item.get("id")
        for item in items
    ]

def make_course_link(course):
    return (
        f"https://mftplus.com/lesson/"
        f"{course.get('lessonId','')}/"
        f"{course.get('lessonUrl','')}?refp={quote(course.get('center',''))}"
    )

def normalize(course, is_active=1, changed_at=None):
    now = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "id": course["id"]["$oid"],
        "title": course.get("title", ""),
        "department": course.get("dep", ""),
        "center": course.get("center", ""),
        "teacher": course.get("author", ""),
        "start_date": course.get("start", ""),
        "end_date": course.get("end", ""),
        "capacity": course.get("capacity", ""),
        "duration_hours": course.get("time", ""),
        "days": " | ".join(course.get("days", [])),
        "min_price": course.get("minCost", ""),
        "max_price": course.get("maxCost", ""),
        "course_url": make_course_link(course),
        "cover": course.get("cover", ""),
        "is_active": is_active,
        "changed_at": changed_at or now,
        "updated_at": now
    }

def load_existing():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        if df.empty:
            return pd.DataFrame()
        return df
    return pd.DataFrame()

def save_all(df, new_courses, expired_courses=[], revived_courses=[]):
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
    df.to_json(JSON_FILE, force_ascii=False, indent=2)
    print("💾 CSV & JSON updated")

    now = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n<details>\n<summary>📊 Sync {now} 📈({len(new_courses)})|📉({len(expired_courses)})|♻️({len(revived_courses)})</summary>\n\n")
        
        if new_courses:
            f.write(f"\n<details>\n<summary> 📈 New courses ({len(new_courses)})</summary>\n\n")
            for c in new_courses:
                f.write(f"- [{c['title']}]({c['course_url']}) | {c['center']}\n")
            f.write("</details>\n")

        if expired_courses:
            f.write(f"\n<details>\n<summary> 📉 Expired courses ({len(expired_courses)})</summary>\n\n")
            for c in expired_courses:
                f.write(f"- [{c['title']}]({c['course_url']}) | {c['center']}\n")
            f.write("</details>\n")

        if revived_courses:
            f.write(f"\n<details>\n<summary> ♻️ Revived courses ({len(revived_courses)})</summary>\n\n")
            for c in revived_courses:
                f.write(f"- [{c['title']}]({c['course_url']}) | {c['center']}\n")
            f.write("</details>\n")

        f.write("</details>\n")

# ---------------- Fetch courses from API ----------------
async def fetch_page(session, payload):
    try:
        async with session.post(API_URL, data=payload) as resp:
            return json.loads(await resp.text())
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return []

async def fetch_all_courses(payload):
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENCY)
    courses, skip, empty = [], 0, 0

    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        while True:
            payload["skip"] = skip
            data = await fetch_page(session, payload)
            if not data:
                empty += 1
                if empty >= MAX_EMPTY_PAGES:
                    break
            else:
                empty = 0
                courses.extend(data)
                print(f"✅ skip={skip} → {len(data)} courses")

            skip += PAGE_SIZE
            await asyncio.sleep(0.2)

    return courses

# ---------------- Main ----------------
async def main():
    # ---------------- Step 1 → Places ----------------
    print("Step 1 → Select Places:")
    selected_places = multi_select(places_data)
    selected_place_ids = get_ids(selected_places)

    # ---------------- Step 2 → Departments ----------------
    print("\nStep 2 → Select Departments:")
    selected_departments = multi_select(departments_data)
    selected_department_ids = get_ids(selected_departments)

    # ---------------- Step 3 → Groups ----------------
    selected_groups, selected_group_ids = [], []
    if selected_department_ids:
        print("\nStep 3 → Select Groups:")
        filtered_groups = [g for g in groups_data if g.get("department_id") in selected_department_ids]
        selected_groups = multi_select(filtered_groups)
        selected_group_ids = get_ids(selected_groups)

    # ---------------- Step 4 → Courses ----------------
    selected_courses, selected_course_ids = [], []
    if selected_group_ids:
        print("\nStep 4 → Select Courses:")
        filtered_courses = [c for c in courses_data if c.get("group_id") in selected_group_ids]
        selected_courses = multi_select(filtered_courses)
        selected_course_ids = get_ids(selected_courses)

    # ---------------- Step 5 → Months ----------------
    print("\nStep 5 → Select Months:")
    selected_months = multi_select(months_data)
    selected_month_ids = get_ids(selected_months)

    # ---------------- Step 6 → Prepare payload ----------------
    payload = {
        "place[]": selected_place_ids,
        "department[]": selected_department_ids,
        "group[]": selected_group_ids,
        "course[]": selected_course_ids,
        "month[]": selected_month_ids,
        "sort": "",
        "skip": 0,
        "pSkip": 0,
        "type": "all"
    }
    print("\nPayload ready:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    # ---------------- Stage 1: Load existing ----------------
    existing_df = load_existing()
    now = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    old_ids = set(existing_df["id"].astype(str)) if "id" in existing_df.columns else set()
    old_active_ids = set(existing_df.loc[existing_df.get("is_active", 0) == 1, "id"].astype(str)) if "id" in existing_df.columns else set()
    old_inactive_ids = set(existing_df.loc[existing_df.get("is_active", 0) == 0, "id"].astype(str)) if "id" in existing_df.columns else set()

    # ---------------- Stage 2: Fetch ----------------
    raw_courses = await fetch_all_courses(payload)
    print(f"🎯 Total fetched: {len(raw_courses)}")

    # ---------------- Stage 3: Normalize ----------------
    api_courses, api_ids = [], set()
    for c in raw_courses:
        course_id = c["id"]["$oid"]
        changed_at = now if course_id not in old_ids or course_id in old_inactive_ids else None
        normalized = normalize(c, is_active=1, changed_at=changed_at)
        api_courses.append(normalized)
        api_ids.add(course_id)

    api_df = pd.DataFrame(api_courses)

    # ---------------- Stage 4: Detect changes ----------------
    new_courses = [c for c in api_courses if c["id"] not in old_ids]

    expired_courses = []
    if not existing_df.empty and "id" in existing_df.columns:
        expired_ids = old_active_ids - api_ids
        if expired_ids:
            expired_df = existing_df[existing_df["id"].astype(str).isin(expired_ids)].copy()
            expired_df["is_active"] = 0
            expired_df["changed_at"] = now
            expired_df["updated_at"] = now
            expired_courses = expired_df.to_dict("records")

    revived_courses = [c for c in api_courses if c["id"] in old_inactive_ids]

    # ---------------- Stage 5: Merge final ----------------
    final_df = existing_df.copy() if not existing_df.empty else pd.DataFrame()
    if not final_df.empty and "id" in final_df.columns:
        final_df = final_df[~final_df["id"].astype(str).isin(api_ids)]
    final_df = pd.concat([final_df, api_df], ignore_index=True)
    if expired_courses:
        final_df = pd.concat([final_df, pd.DataFrame(expired_courses)], ignore_index=True)

    save_all(final_df, new_courses, expired_courses, revived_courses)

    print(f"✨ New: {len(new_courses)}")
    print(f"⏸️ Expired: {len(expired_courses)}")
    print(f"♻️ Revived: {len(revived_courses)}")

if __name__ == "__main__":
    asyncio.run(main())
