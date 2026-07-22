import requests

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"

# --- Config: change these for your batch ---
CATEGORY = "restaurant"     # OSM tag value, e.g. restaurant, cafe, dentist
AREA_NAME = "Lahore"        # display only for now
COUNTRY = "Pakistan"        # display only for now

# Bounding box around Lahore: (south, west, north, east)
# A direct bbox skips Overpass's slow "area by name" lookup step.
BBOX = (31.35, 74.15, 31.65, 74.50)

query = f"""
[out:json][timeout:60];
(
  node["amenity"="{CATEGORY}"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["amenity"="{CATEGORY}"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out center tags;
"""

headers = {
    "User-Agent": "gmap-agency-scout/1.0 (contact: your-email@example.com)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
}

response = requests.post(OVERPASS_URL, data={"data": query}, headers=headers, timeout=90)
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
