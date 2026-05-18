import os
import sys
import json
import uuid
import feedparser
import requests
from datetime import datetime
sys.path.append('scripts')
from helpers import load_db, save_db, call_groq, send_telegram

def fetch_google_trends():
    feed = feedparser.parse(
        'https://trends.google.com/trends/trendingsearches/daily/rss?geo=US'
    )
    return [entry.title for entry in feed.entries[:15]]

def fetch_reddit_trending():
    headers = {'User-Agent': 'IncomeAgent/1.0'}
    subreddits = ['entrepreneur', 'productivity', 'ChatGPT', 'passive_income']
    topics = []
    for sub in subreddits:
        try:
            r = requests.get(
                f'https://www.reddit.com/r/{sub}/hot.json?limit=5',
                headers=headers
            )
            posts = r.json()['data']['children']
            topics.extend([p['data']['title'] for p in posts])
        except:
            pass
    return topics[:10]

def pick_product_idea(trends, reddit_topics):
    all_topics = trends + reddit_topics
    topics_str = '\n'.join(f'- {t}' for t in all_topics)

    prompt = f"""
You are a digital product expert. Based on these trending topics, suggest the single best digital product to sell on Gumroad right now.

Trending topics:
{topics_str}

Rules:
- Must be creatable with AI (prompt pack, ebook, template, cheat sheet, swipe file)
- Price between $9-$27
- Target a specific audience
- High perceived value, easy to make

Respond ONLY with valid JSON, no explanation, no markdown:
{{
  "title": "50 ChatGPT Prompts for Freelance Designers",
  "product_type": "prompt_pack",
  "target_audience": "freelance graphic designers",
  "niche": "design",
  "price": 12,
  "keywords": ["chatgpt prompts", "graphic design", "freelance"],
  "best_subreddit": "graphic_design",
  "pinterest_board_topic": "graphic design tips"
}}
"""
    response = call_groq(prompt, max_tokens=500)
    cleaned = response.replace('```json', '').replace('```', '').strip()
    return json.loads(cleaned)

def main():
    print("Agent 1: Starting market research...")

    trends = fetch_google_trends()
    print(f"Fetched {len(trends)} Google trends")

    reddit = fetch_reddit_trending()
    print(f"Fetched {len(reddit)} Reddit topics")

    idea = pick_product_idea(trends, reddit)
    print(f"Selected idea: {idea['title']}")

    db = load_db()
    product = {
        'id': str(uuid.uuid4()),
        'title': idea['title'],
        'product_type': idea['product_type'],
        'target_audience': idea['target_audience'],
        'niche': idea['niche'],
        'price': idea['price'],
        'keywords': idea['keywords'],
        'best_subreddit': idea['best_subreddit'],
        'pinterest_board_topic': idea['pinterest_board_topic'],
        'status': 'researched',
        'created_at': datetime.now().isoformat()
    }
    db['products'].append(product)
    save_db(db)

    send_telegram(
        f"🔍 <b>Agent 1 done</b>\n"
        f"Product idea: {idea['title']}\n"
        f"Type: {idea['product_type']}\n"
        f"Price: ${idea['price']}"
    )
    print("Agent 1: Done.")

if __name__ == '__main__':
    main()
