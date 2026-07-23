import requests
import json
import time

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"

CATEGORY = "restaurant"

# --- Target areas: add or remove cities here ---
AREAS = [
    {"name": "New York", "country": "USA",       "bbox": (40.70, -74.02, 40.80, -73.93)},
    {"name": "London",   "country": "UK",         "bbox": (51.49, -0.15, 51.53, -0.08)},
    {"name": "Toronto",  "country": "Canada",     "bbox": (43.63, -79.42, 43.68, -79.35)},
    {"name": "Sydney",   "country": "Australia",  "bbox": (-33.90, 151.19, -33.85, 151.23)},
    {"name": "Dubai",    "country": "UAE",        "bbox": (25.18, 55.24, 25.28, 55.34)},
]

headers = {
    "User-Agent": "gmap-agency-scout/1.0 (contact: your-email@example.com)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
}

all_leads = []

for area in AREAS:
    name, country, bbox = area["name"], area["country"], area["bbox"]

    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"="{CATEGORY}"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      way["amenity"="{CATEGORY}"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
    );
    out center tags;
    """

    print(f"Querying {name}, {country}...")
    response = requests.post(OVERPASS_URL, data={"data": query}, headers=headers, timeout=90)
    response.raise_for_status()
    data = response.json()
    elements = data.get("elements", [])

    area_leads = 0
    for el in elements:
        tags = el.get("tags", {})
        biz_name = tags.get("name")
        if not biz_name:
            continue

        website = tags.get("website") or tags.get("contact:website")
        if website:
            continue

        email = tags.get("email") or tags.get("contact:email")
        phone = tags.get("phone") or tags.get("contact:phone")

        if email:
            channel = "email"
        elif phone:
            channel = "whatsapp"
        else:
            channel = "unreachable"

        all_leads.append({
            "name": biz_name,
            "category": CATEGORY,
            "area": name,
            "country": country,
            "email": email,
            "phone": phone,
            "channel": channel,
            "status": "scouted",
        })
        area_leads += 1

    print(f"  {len(elements)} checked, {area_leads} usable leads found")
    time.sleep(5)  # be polite to the shared mirror between queries

print(f"\nTotal usable leads across all areas: {len(all_leads)}")

by_channel = {}
for lead in all_leads:
    by_channel[lead["channel"]] = by_channel.get(lead["channel"], 0) + 1
print(f"Breakdown by channel: {by_channel}")

by_country = {}
for lead in all_leads:
    by_country[lead["country"]] = by_country.get(lead["country"], 0) + 1
print(f"Breakdown by country: {by_country}")

print("\nSample leads:")
print(json.dumps(all_leads[:5], ensure_ascii=False, indent=2))
