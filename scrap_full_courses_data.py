from bs4 import BeautifulSoup
import requests
import pandas as pd
import json
import os
import re
from time import sleep

# ---------------- CONFIG ----------------
CSV_FILE = "mftplus_courses_async.csv"
OUTPUT_JSON = "courses_full_data.json"
LINK_COLUMN = "course_url"
LESSON_ID_REGEX = r"/lesson/(\d+)/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ---------------- EXTRACT LESSON ID ----------------
def extract_lesson_id(url):
    match = re.search(LESSON_ID_REGEX, url)
    return match.group(1) if match else None

# ---------------- GET UNIQUE URLS ----------------
def extract_unique_urls_by_lessonid(csv_file):
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        return []

    df = pd.read_csv(csv_file)

    if LINK_COLUMN not in df.columns:
        print(f"❌ Column '{LINK_COLUMN}' not found in CSV")
        return []

    unique_ids = set()
    urls = []

    for link in df[LINK_COLUMN].dropna():
        link = link.strip()
        lesson_id = extract_lesson_id(link)
        if not lesson_id:
            continue

        if lesson_id in unique_ids:
            continue

        unique_ids.add(lesson_id)
        urls.append(link)

    return urls

# ---------------- SCRAPE COURSE PAGE ----------------
def scrape_course(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(response.text, "html.parser")

    lesson_id = extract_lesson_id(url)

    # title (ترجیحاً از h1 اگر بود)
    title_tag = soup.find("h1")
    if not title_tag:
        title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # description
    desc_tag = soup.select_one("div.forced-ellipsis p")
    description = desc_tag.get_text(" ", strip=True) if desc_tag else ""

    prerequisites = []
    curriculum = []
    skills_acquired = []
    career_opportunities = []

    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)

        if "پیش نیاز" in text:
            ul = h2.find_next("ul", class_="custom-ul")
            if ul:
                prerequisites = [li.get_text(strip=True) for li in ul.find_all("li")]

        elif "سرفصل" in text:
            ul = h2.find_next("ul", class_="custom-ul")
            if ul:
                curriculum = [li.get_text(strip=True) for li in ul.find_all("li")]

        elif "کسب توانایی" in text:
            ul = h2.find_next("ul", class_="custom-ul")
            if ul:
                skills_acquired = [li.get_text(strip=True) for li in ul.find_all("li")]

        elif "بازار کار" in text:
            ul = h2.find_next("ul", class_="custom-ul")
            if ul:
                career_opportunities = [
                    li.get_text(" ", strip=True) for li in ul.find_all("li")
                ]

    return {
        "lesson_id": lesson_id,
        "title": title,
        "description": description,
        "prerequisites": prerequisites,
        "curriculum": curriculum,
        "skills_acquired": skills_acquired,
        "career_opportunities": career_opportunities,
        "url": url
    }

# ---------------- MAIN ----------------
def main():
    urls = extract_unique_urls_by_lessonid(CSV_FILE)
    print(f"🔗 {len(urls)} unique URLs found")

    results = []

    for i, url in enumerate(urls, 1):
        print(f"📘 [{i}/{len(urls)}] Scraping: {url}")
        try:
            data = scrape_course(url)
            results.append(data)
            sleep(1)  # جلوگیری از بلاک شدن
        except Exception as e:
            print(f"❌ Error scraping {url}:", e)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(results)} courses to {OUTPUT_JSON}")

# ---------------- RUN ----------------
if __name__ == "__main__":
    main()