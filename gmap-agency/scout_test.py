import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# --- Config: change these for your batch ---
CATEGORY = "restaurant"     # OSM tag value, e.g. restaurant, cafe, dentist
AREA_NAME = "Lahore"        # city/area name exactly as it appears in OSM
COUNTRY = "Pakistan"        # display only for now

query = f"""
[out:json][timeout:25];
area["name"="{AREA_NAME}"]["boundary"="administrative"]->.searchArea;
(
  node["amenity"="{CATEGORY}"](area.searchArea);
  way["amenity"="{CATEGORY}"](area.searchArea);
);
out center tags;
"""

headers = {
    "User-Agent": "gmap-agency-scout/1.0 (contact: your-email@example.com)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
}

response = requests.post(OVERPASS_URL, data={"data": query}, headers=headers)
response.raise_for_status()
data = response.json()

elements = data.get("elements", [])
print(f"Found {len(elements)} {CATEGORY} listings in {AREA_NAME}, {COUNTRY}\n")

no_website_count = 0
for el in elements:
    tags = el.get("tags", {})
    name = tags.get("name", "(no name)")
    website = tags.get("website") or tags.get("contact:website")
    phone = tags.get("phone") or tags.get("contact:phone")
    if not website:
        no_website_count += 1
    print(f"- {name} | website: {website or 'MISSING'} | phone: {phone or 'none'}")

print(f"\n{no_website_count} of {len(elements)} have no website listed.")
