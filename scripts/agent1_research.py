import os
import sys
import json
import uuid
import feedparser
import requests
from datetime import datetime

sys.path.append('scripts')
from helpers import load_db, save_db, call_groq, send_telegram

# ── Source 1: Google Trends RSS ──────────────────────────────────────────────
def fetch_google_trends():
    try:
        feed = feedparser.parse(
            'https://trends.google.com/trends/trendingsearches/daily/rss?geo=US'
        )
        topics = [entry.title for entry in feed.entries[:15]]
        print(f"Google Trends: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"Google Trends error: {e}")
        return []

# ── Source 2: HackerNews Top Stories (no API key needed) ─────────────────────
def fetch_hackernews():
    try:
        top_ids = requests.get(
            'https://hacker-news.firebaseio.com/v0/topstories.json'
        ).json()[:10]

        topics = []
        for story_id in top_ids:
            story = requests.get(
                f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json'
            ).json()
            if story and story.get('title'):
                topics.append(story['title'])

        print(f"HackerNews: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"HackerNews error: {e}")
        return []

# ── Source 3: NewsAPI ─────────────────────────────────────────────────────────
def fetch_news_api():
    try:
        api_key = os.environ['NEWS_API_KEY']
        response = requests.get(
            'https://newsapi.org/v2/top-headlines',
            params={
                'country': 'us',
                'category': 'technology',
                'pageSize': 10,
                'apiKey': api_key
            }
        )
        articles = response.json().get('articles', [])
        topics = [a['title'] for a in articles if a.get('title')]
        print(f"NewsAPI: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"NewsAPI error: {e}")
        return []

# ── Source 4: Dev.to trending (no key needed to read) ────────────────────────
def fetch_devto_trending():
    try:
        response = requests.get(
            'https://dev.to/api/articles',
            params={'top': 7, 'per_page': 10},
            headers={'User-Agent': 'IncomeAgentBot/1.0'}
        )
        articles = response.json()
        topics = [a['title'] for a in articles if a.get('title')]
        print(f"Dev.to: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"Dev.to error: {e}")
        return []

# ── Pick best product idea using Groq ────────────────────────────────────────
def pick_product_idea(all_topics):
    topics_str = '\n'.join(f'- {t}' for t in all_topics[:30])

    prompt = f"""
You are a digital product expert who sells on Gumroad.
Based on these trending topics, suggest the single best digital product idea.

Trending topics:
{topics_str}

Rules:
- Must be creatable with AI (prompt pack, ebook, template, cheat sheet, swipe file)
- Price between $9 and $27
- Target a very specific audience
- High perceived value, easy to make with AI
- Pick topics with commercial intent (business, productivity, AI, money, career, tech)

Respond ONLY with valid JSON, no explanation, no markdown backticks:
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
}}
"""
    response = call_groq(prompt, max_tokens=600)
    cleaned = response.replace('```json', '').replace('```', '').strip()

    # Find JSON object in response
    start = cleaned.find('{')
    end = cleaned.rfind('}') + 1
    json_str = cleaned[start:end]

    return json.loads(json_str)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("Agent 1: Market Research Starting")
    print("=" * 50)

    # Gather topics from all sources
    trends   = fetch_google_trends()
    hn       = fetch_hackernews()
    news     = fetch_news_api()
    devto    = fetch_devto_trending()

    all_topics = trends + hn + news + devto
    print(f"\nTotal topics gathered: {len(all_topics)}")

    if not all_topics:
        print("No topics gathered — check API keys")
        return

    # Pick the best product idea
    print("\nAsking Groq to pick best product idea...")
    idea = pick_product_idea(all_topics)
    print(f"Selected: {idea['title']}")

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
        'devto_tags': idea.get('devto_tags', []),
        'hashnode_tags': idea.get('hashnode_tags', []),
        'blogger_labels': idea.get('blogger_labels', []),
        'telegram_teaser': idea.get('telegram_teaser', idea['title']),
        'status': 'researched',
        'created_at': datetime.now().isoformat(),
        'traffic_posted': False
    }
    db['products'].append(product)
    save_db(db)

    # Notify via Telegram
    send_telegram(
        f"🔍 <b>Agent 1 — Research Done</b>\n\n"
        f"📦 Product: {idea['title']}\n"
        f"🎯 Type: {idea['product_type']}\n"
        f"👥 Audience: {idea['target_audience']}\n"
        f"💰 Price: ${idea['price']}\n\n"
        f"Status: Moving to Agent 2 in 1 hour..."
    )

    print("\nAgent 1: Done ✓")

if __name__ == '__main__':
    main()
