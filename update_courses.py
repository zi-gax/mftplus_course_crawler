import aiohttp
import asyncio
import pandas as pd
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote
from pandas.errors import EmptyDataError

# ---------------- Configuration ----------------
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
API_URL = "https://mftplus.com/ajax/default/calendar?need=search"
PAGE_SIZE = 9
MAX_CONCURRENCY = 5
MAX_EMPTY_PAGES = 2

CSV_FILE = "mftplus_courses_async.csv"
JSON_FILE = "mftplus_courses_async.json"
LOG_FILE = "COURSE_LOG.md"

COLUMNS = [
    "id", "title", "department", "center", "teacher",
    "start_date", "end_date", "capacity", "duration_hours",
    "days", "min_price", "max_price",
    "course_url", "cover",
    "is_active", "changed_at", "updated_at"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://mftplus.com/calendar"
}

# ---------------- Stage 1: Fetch ----------------
async def fetch_page(session, skip):
    payload = {"term": "", "sort": "", "skip": skip, "pSkip": 0, "type": "all"}
    try:
        async with session.post(API_URL, data=payload) as resp:
            return json.loads(await resp.text())
    except Exception as e:
        print(f"⚠️ skip={skip} error: {e}")
        return []

async def fetch_all_courses():
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENCY)
    courses, skip, empty = [], 0, 0

    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        while True:
            data = await fetch_page(session, skip)

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

# ---------------- Stage 2: Normalize ----------------
def make_course_link(course):
    return (
        f"https://mftplus.com/lesson/"
        f"{course.get('lessonId','')}/"
        f"{course.get('lessonUrl','')}?refp={quote(course.get('center',''))}"
    )

def normalize(course, is_active, changed_at):
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
        "changed_at": changed_at,
        "updated_at": now
    }

# ---------------- Stage 3: Load ----------------
def load_existing():
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame(columns=COLUMNS)

    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty:
            return pd.DataFrame(columns=COLUMNS)
        return df
    except EmptyDataError:
        return pd.DataFrame(columns=COLUMNS)

# ---------------- Stage 4: Save ----------------
def save_all(df, new_courses, expired_courses, revived_courses):
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
    df.to_json(JSON_FILE, force_ascii=False, indent=2)

    now = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"\n<details>\n"
            f"<summary>📊 Sync {now} "
            f"📈({len(new_courses)}) | "
            f"📉({len(expired_courses)}) | "
            f"♻️({len(revived_courses)})</summary>\n\n"
        )

        for title, items, emoji in [
            ("New courses", new_courses, "📈"),
            ("Expired courses", expired_courses, "📉"),
            ("Revived courses", revived_courses, "♻️")
        ]:
            if items:
                f.write(f"<details>\n<summary>{emoji} {title} ({len(items)})</summary>\n\n")
                for c in items:
                    f.write(f"- [{c['title']}]({c['course_url']}) | {c['center']}\n")
                f.write("</details>\n")

        f.write("</details>\n")

# ---------------- Main ----------------
async def main():
    existing_df = load_existing()
    now = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")

    existing_map = {row["id"]: row.to_dict() for _, row in existing_df.iterrows()}

    old_active_ids = {
        row["id"] for _, row in existing_df.iterrows()
        if row.get("is_active") == 1
    }

    old_inactive_ids = {
        row["id"] for _, row in existing_df.iterrows()
        if row.get("is_active") == 0
    }

    raw_courses = await fetch_all_courses()
    print(f"🎯 Total fetched: {len(raw_courses)}")

    api_ids = set()
    api_courses = []

    for c in raw_courses:
        cid = c["id"]["$oid"]
        api_ids.add(cid)

        prev = existing_map.get(cid)
        status_changed = not prev or prev.get("is_active") == 0

        api_courses.append(
            normalize(
                c,
                is_active=1,
                changed_at=now if status_changed else prev.get("changed_at", now)
            )
        )

    new_courses = [c for c in api_courses if c["id"] not in existing_map]
    revived_courses = [c for c in api_courses if c["id"] in old_inactive_ids]

    expired_courses = []
    for cid in old_active_ids - api_ids:
        row = existing_map[cid]
        row["is_active"] = 0
        row["changed_at"] = now
        row["updated_at"] = now
        expired_courses.append(row)

    final_map = {row["id"]: row for row in existing_map.values()}
    for c in api_courses + expired_courses:
        final_map[c["id"]] = c

    final_df = pd.DataFrame(final_map.values(), columns=COLUMNS)

    save_all(final_df, new_courses, expired_courses, revived_courses)

    print(f"✨ New: {len(new_courses)}")
    print(f"⏸️ Expired: {len(expired_courses)}")
    print(f"♻️ Revived: {len(revived_courses)}")

if __name__ == "__main__":
    asyncio.run(main())
