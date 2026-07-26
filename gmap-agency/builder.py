import os
import re
import json
import time
import requests

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

LEADS_FILE = "gmap-agency/leads.json"
DOCS_DIR = "docs/gmap-agency"
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "50"))

PAGES_BASE = "https://sinan33644061-lab.github.io/income-agents/gmap-agency"


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "biz"


def generate_copy(name, category, area, country):
    prompt = f"""Write short marketing copy for a one-page demo website for this business:
Name: {name}
Type: {category}
Location: {area}, {country}

Respond with ONLY valid JSON, no other text, in this exact format:
{{"headline": "...", "tagline": "...", "blurb": "..."}}

- headline: the business name styled as a hero title (max 6 words)
- tagline: a short catchy line about what they offer (max 12 words)
- blurb: a warm 2-sentence paragraph describing the experience customers can expect
"""
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 250,
        },
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()
    text = re.sub(r"^```json|^```|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)


def render_html(category, area, country, copy):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{copy['headline']}</title>
<style>
  body {{ margin:0; font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#faf7f2; color:#222; }}
  .hero {{ padding: 80px 24px; text-align:center; background: linear-gradient(135deg,#2b2118,#4a3623); color:#fff; }}
  .hero h1 {{ font-size: 2.4rem; margin:0 0 12px; }}
  .hero p {{ font-size: 1.1rem; opacity:0.9; margin:0; }}
  .content {{ max-width: 640px; margin: 0 auto; padding: 48px 24px; text-align:center; }}
  .content p {{ font-size:1.05rem; line-height:1.6; }}
  .meta {{ color:#888; font-size:0.9rem; margin-top:24px; }}
  .cta {{ margin-top:32px; }}
  .cta a {{ display:inline-block; padding:14px 28px; background:#b5651d; color:#fff; text-decoration:none; border-radius:6px; font-weight:600; }}
</style>
</head>
<body>
  <div class="hero">
    <h1>{copy['headline']}</h1>
    <p>{copy['tagline']}</p>
  </div>
  <div class="content">
    <p>{copy['blurb']}</p>
    <div class="meta">{category.title()} &middot; {area}, {country}</div>
    <div class="cta"><a href="#">Get In Touch</a></div>
  </div>
</body>
</html>"""


with open(LEADS_FILE, "r", encoding="utf-8") as f:
    leads = json.load(f)

used_slugs = {l["slug"] for l in leads if l.get("slug")}
todo = [l for l in leads if l.get("status") == "scouted"][:BATCH_SIZE]

print(f"Building demo sites for {len(todo)} leads\n")

built_count = 0
for lead in todo:
    print(f"Building: {lead['name']} ({lead['area']})...")
    try:
        copy = generate_copy(lead["name"], lead["category"], lead["area"], lead["country"])
    except Exception as e:
        print(f"  failed to generate copy: {e}")
        time.sleep(2)
        continue

    base_slug = slugify(f"{lead['name']}-{lead['area']}")
    slug = base_slug
    i = 2
    while slug in used_slugs:
        slug = f"{base_slug}-{i}"
        i += 1
    used_slugs.add(slug)

    html = render_html(lead["category"], lead["area"], lead["country"], copy)

    site_dir = os.path.join(DOCS_DIR, slug)
    os.makedirs(site_dir, exist_ok=True)
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    lead["slug"] = slug
    lead["demo_url"] = f"{PAGES_BASE}/{slug}/"
    lead["status"] = "built"
    built_count += 1

    time.sleep(2)

with open(LEADS_FILE, "w", encoding="utf-8") as f:
    json.dump(leads, f, ensure_ascii=False, indent=2)

print(f"\nBuilt {built_count} demo sites this run.")
remaining = sum(1 for l in leads if l.get("status") == "scouted")
print(f"Remaining scouted (not yet built): {remaining}")
