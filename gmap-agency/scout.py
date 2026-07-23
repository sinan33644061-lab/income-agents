import requests
import json
import time
import os

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"

CATEGORY = "restaurant"

# --- Batch control: runs this many cities per execution ---
BATCH_START = int(os.environ.get("BATCH_START", "0"))
BATCH_SIZE = 15

# name, country, lat, lon
CITY_CENTERS = [
    ("New York", "USA", 40.7580, -73.9855),
    ("Los Angeles", "USA", 34.0522, -118.2437),
    ("Chicago", "USA", 41.8781, -87.6298),
    ("Houston", "USA", 29.7604, -95.3698),
    ("Phoenix", "USA", 33.4484, -112.0740),
    ("Philadelphia", "USA", 39.9526, -75.1652),
    ("San Antonio", "USA", 29.4241, -98.4936),
    ("San Diego", "USA", 32.7157, -117.1611),
    ("Dallas", "USA", 32.7767, -96.7970),
    ("San Jose", "USA", 37.3382, -121.8863),
    ("Austin", "USA", 30.2672, -97.7431),
    ("Jacksonville", "USA", 30.3322, -81.6557),
    ("San Francisco", "USA", 37.7749, -122.4194),
    ("Columbus", "USA", 39.9612, -82.9988),
    ("Indianapolis", "USA", 39.7684, -86.1581),
    ("Seattle", "USA", 47.6062, -122.3321),
    ("Denver", "USA", 39.7392, -104.9903),
    ("Boston", "USA", 42.3601, -71.0589),
    ("Washington DC", "USA", 38.9072, -77.0369),
    ("Nashville", "USA", 36.1627, -86.7816),
    ("Portland", "USA", 45.5152, -122.6784),
    ("Miami", "USA", 25.7617, -80.1918),
    ("Atlanta", "USA", 33.7490, -84.3880),
    ("Minneapolis", "USA", 44.9778, -93.2650),
    ("Charlotte", "USA", 35.2271, -80.8431),
    ("Detroit", "USA", 42.3314, -83.0458),
    ("Las Vegas", "USA", 36.1699, -115.1398),
    ("Orlando", "USA", 28.5383, -81.3792),
    ("Tampa", "USA", 27.9506, -82.4572),
    ("Pittsburgh", "USA", 40.4406, -79.9959),
    ("Cleveland", "USA", 41.4993, -81.6944),
    ("Cincinnati", "USA", 39.1031, -84.5120),
    ("Kansas City", "USA", 39.0997, -94.5786),
    ("Sacramento", "USA", 38.5816, -121.4944),
    ("New Orleans", "USA", 29.9511, -90.0715),
    ("Toronto", "Canada", 43.6532, -79.3832),
    ("Vancouver", "Canada", 49.2827, -123.1207),
    ("Montreal", "Canada", 45.5017, -73.5673),
    ("Calgary", "Canada", 51.0447, -114.0719),
    ("Ottawa", "Canada", 45.4215, -75.6972),
    ("Edmonton", "Canada", 53.5461, -113.4938),
    ("Winnipeg", "Canada", 49.8951, -97.1384),
    ("Quebec City", "Canada", 46.8139, -71.2080),
    ("Halifax", "Canada", 44.6488, -63.5752),
    ("London", "UK", 51.5074, -0.1278),
    ("Manchester", "UK", 53.4808, -2.2426),
    ("Birmingham", "UK", 52.4862, -1.8904),
    ("Edinburgh", "UK", 55.9533, -3.1883),
    ("Glasgow", "UK", 55.8642, -4.2518),
    ("Leeds", "UK", 53.8008, -1.5491),
    ("Liverpool", "UK", 53.4084, -2.9916),
    ("Bristol", "UK", 51.4545, -2.5879),
    ("Cardiff", "UK", 51.4816, -3.1791),
    ("Belfast", "UK", 54.5973, -5.9301),
    ("Paris", "France", 48.8566, 2.3522),
    ("Lyon", "France", 45.7640, 4.8357),
    ("Marseille", "France", 43.2965, 5.3698),
    ("Toulouse", "France", 43.6047, 1.4442),
    ("Bordeaux", "France", 44.8378, -0.5792),
    ("Nice", "France", 43.7102, 7.2620),
    ("Berlin", "Germany", 52.5200, 13.4050),
    ("Munich", "Germany", 48.1351, 11.5820),
    ("Frankfurt", "Germany", 50.1109, 8.6821),
    ("Hamburg", "Germany", 53.5511, 9.9937),
    ("Cologne", "Germany", 50.9375, 6.9603),
    ("Stuttgart", "Germany", 48.7758, 9.1829),
    ("Dusseldorf", "Germany", 51.2277, 6.7735),
    ("Madrid", "Spain", 40.4168, -3.7038),
    ("Barcelona", "Spain", 41.3851, 2.1734),
    ("Rome", "Italy", 41.9028, 12.4964),
    ("Milan", "Italy", 45.4642, 9.1900),
    ("Turin", "Italy", 45.0703, 7.6869),
    ("Naples", "Italy", 40.8518, 14.2681),
    ("Amsterdam", "Netherlands", 52.3676, 4.9041),
    ("Rotterdam", "Netherlands", 51.9244, 4.4777),
    ("The Hague", "Netherlands", 52.0705, 4.3007),
    ("Brussels", "Belgium", 50.8503, 4.3517),
    ("Antwerp", "Belgium", 51.2194, 4.4025),
    ("Vienna", "Austria", 48.2082, 16.3738),
    ("Zurich", "Switzerland", 47.3769, 8.5417),
    ("Geneva", "Switzerland", 46.2044, 6.1432),
    ("Stockholm", "Sweden", 59.3293, 18.0686),
    ("Copenhagen", "Denmark", 55.6761, 12.5683),
    ("Helsinki", "Finland", 60.1699, 24.9384),
    ("Oslo", "Norway", 59.9139, 10.7522),
    ("Dublin", "Ireland", 53.3498, -6.2603),
    ("Lisbon", "Portugal", 38.7223, -9.1393),
    ("Porto", "Portugal", 41.1579, -8.6291),
    ("Warsaw", "Poland", 52.2297, 21.0122),
    ("Krakow", "Poland", 50.0647, 19.9450),
    ("Prague", "Czech Republic", 50.0755, 14.4378),
    ("Budapest", "Hungary", 47.4979, 19.0402),
    ("Bratislava", "Slovakia", 48.1486, 17.1077),
    ("Ljubljana", "Slovenia", 46.0569, 14.5058),
    ("Zagreb", "Croatia", 45.8150, 15.9819),
    ("Athens", "Greece", 37.9838, 23.7275),
    ("Bucharest", "Romania", 44.4268, 26.1025),
    ("Sofia", "Bulgaria", 42.6977, 23.3219),
    ("Reykjavik", "Iceland", 64.1466, -21.9426),
    ("Luxembourg City", "Luxembourg", 49.6116, 6.1319),
    ("Tokyo", "Japan", 35.6762, 139.6503),
    ("Osaka", "Japan", 34.6937, 135.5023),
    ("Nagoya", "Japan", 35.1815, 136.9066),
    ("Yokohama", "Japan", 35.4437, 139.6380),
    ("Fukuoka", "Japan", 33.5904, 130.4017),
    ("Seoul", "South Korea", 37.5665, 126.9780),
    ("Busan", "South Korea", 35.1796, 129.0756),
    ("Singapore", "Singapore", 1.3521, 103.8198),
    ("Hong Kong", "Hong Kong", 22.3193, 114.1694),
    ("Taipei", "Taiwan", 25.0330, 121.5654),
    ("Kaohsiung", "Taiwan", 22.6273, 120.3014),
    ("Sydney", "Australia", -33.8688, 151.2093),
    ("Melbourne", "Australia", -37.8136, 144.9631),
    ("Brisbane", "Australia", -27.4698, 153.0251),
    ("Perth", "Australia", -31.9505, 115.8605),
    ("Auckland", "New Zealand", -36.8485, 174.7633),
    ("Wellington", "New Zealand", -41.2865, 174.7762),
    ("Dubai", "UAE", 25.2048, 55.2708),
    ("Abu Dhabi", "UAE", 24.4539, 54.3773),
    ("Doha", "Qatar", 25.2854, 51.5310),
    ("Riyadh", "Saudi Arabia", 24.7136, 46.6753),
    ("Kuwait City", "Kuwait", 29.3759, 47.9774),
    ("Manama", "Bahrain", 26.2285, 50.5860),
    ("Muscat", "Oman", 23.5859, 58.4059),
]

DELTA = 0.05  # ~5-6km box around each city center

headers = {
    "User-Agent": "gmap-agency-scout/1.0 (contact: your-email@example.com)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
}

def query_area(bbox, category, attempts=2):
    query = f"""
    [out:json][timeout:90];
    (
      node["amenity"="{category}"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      way["amenity"="{category}"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
    );
    out center tags;
    """
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(OVERPASS_URL, data={"data": query}, headers=headers, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"  attempt {attempt} failed: {e}")
            time.sleep(10)
    raise last_error

LEADS_FILE = "gmap-agency/leads.json"

existing_leads = []
if os.path.exists(LEADS_FILE):
    with open(LEADS_FILE, "r", encoding="utf-8") as f:
        existing_leads = json.load(f)

seen = {(l["name"], l["area"]) for l in existing_leads}
new_leads = []

batch = CITY_CENTERS[BATCH_START:BATCH_START + BATCH_SIZE]
print(f"Running batch: cities {BATCH_START} to {BATCH_START + len(batch) - 1} of {len(CITY_CENTERS)}\n")

for name, country, lat, lon in batch:
    bbox = (lat - DELTA, lon - DELTA, lat + DELTA, lon + DELTA)
    print(f"Querying {name}, {country}...")

    try:
        data = query_area(bbox, CATEGORY)
    except requests.exceptions.RequestException:
        print(f"  skipping {name} after repeated failures\n")
        time.sleep(8)
        continue

    elements = data.get("elements", [])
    area_leads = 0

    for el in elements:
        tags = el.get("tags", {})
        biz_name = tags.get("name")
        if not biz_name or (biz_name, name) in seen:
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
            continue

        new_leads.append({
            "name": biz_name,
            "category": CATEGORY,
            "area": name,
            "country": country,
            "email": email,
            "phone": phone,
            "channel": channel,
            "status": "scouted",
        })
        seen.add((biz_name, name))
        area_leads += 1

    print(f"  {len(elements)} checked, {area_leads} new reachable leads\n")
    time.sleep(8)

all_leads = existing_leads + new_leads
print(f"New leads this batch: {len(new_leads)}")
print(f"Total leads saved so far: {len(all_leads)}")

by_channel = {}
for lead in all_leads:
    by_channel[lead["channel"]] = by_channel.get(lead["channel"], 0) + 1
print(f"Breakdown by channel: {by_channel}")

os.makedirs("gmap-agency", exist_ok=True)
with open(LEADS_FILE, "w", encoding="utf-8") as f:
    json.dump(all_leads, f, ensure_ascii=False, indent=2)

next_start = BATCH_START + BATCH_SIZE
if next_start < len(CITY_CENTERS):
    print(f"\nNext batch: set BATCH_START = {next_start} and re-run.")
else:
    print("\nAll cities covered.")
