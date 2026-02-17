import json

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

# ---------------- Helper function for multi-select ----------------
def multi_select(options, key_name="title"):
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

# ---------------- Helper to extract IDs ----------------
def get_ids(items):
    return [
        item["id"]["$oid"] if isinstance(item.get("id"), dict) else item.get("id")
        for item in items
    ]

# ---------------- Step 1: Places ----------------
print("Step 1 → Select Places:")
selected_places = multi_select(places_data)
selected_place_ids = get_ids(selected_places)

# ---------------- Step 2: Departments ----------------
print("\nStep 2 → Select Departments:")
selected_departments = multi_select(departments_data)
selected_department_ids = get_ids(selected_departments)

# ---------------- Step 3: Groups filtered by department ----------------
selected_groups = []
selected_group_ids = []

if selected_department_ids:
    print("\nStep 3 → Select Groups (filtered by selected departments):")
    filtered_groups = [
        g for g in groups_data if g.get("department_id") in selected_department_ids
    ]
    selected_groups = multi_select(filtered_groups)
    selected_group_ids = get_ids(selected_groups)
else:
    print("\nStep 3 → No departments selected, skipping groups.")

# ---------------- Step 4: Courses filtered by group ----------------
selected_courses = []
selected_course_ids = []

if selected_group_ids:
    print("\nStep 4 → Select Courses (filtered by selected groups):")
    filtered_courses = [
        c for c in courses_data if c.get("group_id") in selected_group_ids
    ]
    selected_courses = multi_select(filtered_courses)
    selected_course_ids = get_ids(selected_courses)
else:
    print("\nStep 4 → No groups selected, skipping courses.")

# ---------------- Step 5: Months ----------------
print("\nStep 5 → Select Months:")
selected_months = multi_select(months_data)
selected_month_ids = get_ids(selected_months)

# ---------------- Step 6: Prepare POST payload ----------------
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
