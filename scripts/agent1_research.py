import os
import sys
import json
import uuid
import requests
from datetime import datetime

sys.path.append('scripts')
from helpers import load_db, save_db, send_telegram

# ── Groq call with error handling ────────────────────────────────────────────
def call_groq_safe(prompt, max_tokens=600):
    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        raise Exception("GROQ_API_KEY secret is missing")

    response = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'llama-3.1-8b-instant',
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}]
        }
    )
    data = response.json()

    # Print full response so we can debug if it fails
    if 'choices' not in data:
        print(f"Groq error response: {json.dumps(data, indent=2)}")
        raise Exception(f"Groq API error: {data.get('error', {}).get('message', 'Unknown error')}")

    return data['choices'][0]['message']['content']

# ── Source 1: HackerNews (no API key, very reliable) ─────────────────────────
def fetch_hackernews():
    try:
        top_ids = requests.get(
            'https://hacker-news.firebaseio.com/v0/topstories.json',
            timeout=10
        ).json()[:15]

        topics = []
        for story_id in top_ids:
            try:
                story = requests.get(
                    f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json',
                    timeout=5
                ).json()
                if story and story.get('title'):
                    topics.append(story['title'])
            except:
                continue

        print(f"HackerNews: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"HackerNews error: {e}")
        return []

# ── Source 2: Dev.to trending (no API key needed to read) ────────────────────
def fetch_devto_trending():
    try:
        response = requests.get(
            'https://dev.to/api/articles',
            params={'top': 7, 'per_page': 15},
            headers={'User-Agent': 'IncomeAgentBot/1.0'},
            timeout=10
        )
        articles = response.json()
        topics = [a['title'] for a in articles if a.get('title')]
        print(f"Dev.to: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"Dev.to error: {e}")
        return []

# ── Source 3: NewsAPI (only if key exists) ────────────────────────────────────
# ── Source 3: Newsdata.io (works from servers, free tier) ────────────────────
def fetch_newsdata():
    api_key = os.environ.get('NEWSDATA_API_KEY', '')
    if not api_key:
        print("Newsdata: skipped (secret not set)")
        return []
    try:
        response = requests.get(
            'https://newsdata.io/api/1/news',
            params={
                'apikey': api_key,
                'language': 'en',
                'category': 'technology,business'
            },
            timeout=10
        )
        articles = response.json().get('results', [])
        topics = [a['title'] for a in articles if a.get('title')]
        print(f"Newsdata.io: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"Newsdata error: {e}")
        return []

# ── Source 4: GitHub trending topics via search ───────────────────────────────
def fetch_github_trending():
    try:
        # Search trending repos created this week
        response = requests.get(
            'https://api.github.com/search/repositories',
            params={
                'q': 'created:>2026-05-01',
                'sort': 'stars',
                'order': 'desc',
                'per_page': 10
            },
            headers={'User-Agent': 'IncomeAgentBot/1.0'},
            timeout=10
        )
        repos = response.json().get('items', [])
        topics = [r['description'] or r['name'] for r in repos if r.get('name')]
        print(f"GitHub trending: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"GitHub trending error: {e}")
        return []

# ── Pick best product idea ────────────────────────────────────────────────────
def pick_product_idea(all_topics):
    # Keep prompt short to avoid Groq token issues
    topics_str = '\n'.join(f'- {t}' for t in all_topics[:20])

    prompt = f"""You are a digital product expert who sells on Gumroad.

Trending topics right now:
{topics_str}

Pick the single best digital product idea (prompt pack, ebook, template, or cheat sheet).
Target a specific audience. Price $9-$27. Must be creatable with AI.

Reply with ONLY this JSON, no extra text:
{{
  "title": "50 ChatGPT Prompts for Freelance Designers",
  "product_type": "prompt_pack",
  "target_audience": "freelance graphic designers",
  "niche": "design",
  "price": 12,
  "keywords": ["chatgpt prompts", "graphic design", "freelance"],
  "devto_tags": ["productivity", "ai", "design"],
  "hashnode_tags": ["AI", "Productivity", "Design"],
  "blogger_labels": ["AI Tools", "Freelance", "Design"],
  "telegram_teaser": "Just dropped: 50 ChatGPT prompts every freelance designer needs"
}}"""

    response = call_groq_safe(prompt, max_tokens=500)
    print(f"Groq raw response:\n{response}\n")

    # Extract JSON safely
    cleaned = response.replace('```json', '').replace('```', '').strip()
    start = cleaned.find('{')
    end = cleaned.rfind('}') + 1
    if start == -1 or end == 0:
        raise Exception(f"No JSON found in Groq response: {cleaned}")

    return json.loads(cleaned[start:end])

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("Agent 1: Market Research Starting")
    print("=" * 50)

    hn      = fetch_hackernews()
    devto   = fetch_devto_trending()
    news    = fetch_newsdata()
    github  = fetch_github_trending()

    all_topics = hn + devto + news + github
    print(f"\nTotal topics gathered: {len(all_topics)}")

    if not all_topics:
        print("ERROR: No topics gathered from any source")
        send_telegram("❌ Agent 1 failed — no topics gathered from any source")
        return

    print("\nAsking Groq to pick best product idea...")
    idea = pick_product_idea(all_topics)
    print(f"✓ Selected: {idea['title']}")

    # Save to database
    db = load_db()
    product = {
        'id': str(uuid.uuid4()),
        'title': idea['title'],
        'product_type': idea['product_type'],
        'target_audience': idea['target_audience'],
        'niche': idea['niche'],
        'price': idea['price'],
        'keywords': idea['keywords'],
        'devto_tags': idea.get('devto_tags', ['productivity', 'ai']),
        'hashnode_tags': idea.get('hashnode_tags', ['AI', 'Productivity']),
        'blogger_labels': idea.get('blogger_labels', ['Digital Products']),
        'telegram_teaser': idea.get('telegram_teaser', idea['title']),
        'status': 'researched',
        'created_at': datetime.now().isoformat(),
        'traffic_posted': False
    }
    db['products'].append(product)
    save_db(db)

    send_telegram(
        f"🔍 <b>Agent 1 — Done</b>\n\n"
        f"📦 {idea['title']}\n"
        f"🎯 {idea['product_type']} for {idea['target_audience']}\n"
        f"💰 ${idea['price']}\n\n"
        f"Agent 2 runs in 1 hour..."
    )

    print("\nAgent 1: Complete ✓")

if __name__ == '__main__':
    main()
