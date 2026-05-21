import os
import sys
import json
import requests
from datetime import datetime

sys.path.append('scripts')
from helpers import get_products_by_status, update_product_status, send_telegram, call_groq

# ── Generate social copy — one section at a time to avoid parsing issues ──────
def generate_devto(product):
    prompt = f"""Write a helpful 300-word article for developers about {product['niche']}.

Product to mention: {product['gumroad_title']} — {product['gumroad_url']}
Audience: {product['target_audience']}

Structure:
- Line 1: Article title (max 80 chars, helpful not salesy)
- Line 2: blank
- Rest: 3 paragraphs. Para 1 teaches something useful. Para 2 explains a common problem. Para 3 mentions the product naturally with the link.

Start your response with the title on the very first line. No labels, no preamble."""

    response = call_groq(prompt, max_tokens=600)
    lines = response.strip().split('\n')
    title = lines[0].strip().lstrip('#').strip()
    body = '\n'.join(lines[1:]).strip()
    return title, body

def generate_telegraph(product):
    prompt = f"""Write a short 200-word article about {product['niche']} for general readers.

Mention this product naturally at the end: {product['gumroad_title']}
Link: {product['gumroad_url']}

Structure:
- Line 1: Article title (max 70 chars, catchy)
- Line 2: blank  
- Rest: 3 short paragraphs in plain text. End with the product link.

Start with the title on the very first line. No labels, no preamble."""

    response = call_groq(prompt, max_tokens=400)
    lines = response.strip().split('\n')
    title = lines[0].strip().lstrip('#').strip()
    body = '\n\n'.join([p.strip() for p in '\n'.join(lines[1:]).split('\n\n') if p.strip()])
    return title, body

def generate_mastodon(product):
    prompt = f"""Write a single Mastodon post (max 450 chars) about {product['niche']}.

Include:
- A helpful tip or insight
- Natural mention of: {product['gumroad_title']}
- This link: {product['gumroad_url']}
- 2-3 hashtags at the end

Write ONLY the post text. No labels, no quotes, no preamble."""

    response = call_groq(prompt, max_tokens=200)
    return response.strip()[:480]

def generate_telegram(product):
    prompt = f"""Write a short Telegram channel post (2-3 lines max) promoting:

Product: {product['gumroad_title']}
Link: {product['gumroad_url']}
Price: ${product['price']}

Use 1-2 emojis. Be punchy and curiosity-driven. End with the link.
Write ONLY the post. No labels, no preamble."""

    response = call_groq(prompt, max_tokens=150)
    return response.strip()

# ── Platform 1: Dev.to ────────────────────────────────────────────────────────
def post_to_devto(title, body, tags):
    try:
        if not title or not body:
            print("✗ Dev.to: empty title or body")
            return ''

        print(f"  Dev.to title: {title[:60]}")
        response = requests.post(
            'https://dev.to/api/articles',
            headers={
                'api-key': os.environ['DEVTO_API_KEY'],
                'Content-Type': 'application/json'
            },
            json={
                'article': {
                    'title': title,
                    'body_markdown': body,
                    'published': True,
                    'tags': tags[:4]
                }
            },
            timeout=15
        )
        result = response.json()
        url = result.get('url', '')
        if url:
            print(f"✓ Posted to Dev.to: {url}")
        else:
            print(f"✗ Dev.to error: {result}")
        return url
    except Exception as e:
        print(f"✗ Dev.to error: {e}")
        return ''

# ── Platform 2: Telegraph ─────────────────────────────────────────────────────
def post_to_telegraph(title, body):
    try:
        access_token = os.environ.get('TELEGRAPH_ACCESS_TOKEN', '')
        if not access_token:
            print("✗ Telegraph: skipped (secret not set)")
            return ''
        if not title or not body:
            print("✗ Telegraph: empty title or body")
            return ''

        print(f"  Telegraph title: {title[:60]}")

        paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
        if not paragraphs:
            paragraphs = [body.strip()]
        content = [{'tag': 'p', 'children': [p]} for p in paragraphs]

        response = requests.post(
            'https://api.telegra.ph/createPage',
            json={
                'access_token': access_token,
                'title': title[:256],
                'content': content,
                'return_content': False
            },
            timeout=15
        )
        result = response.json()
        if result.get('ok'):
            url = result['result']['url']
            print(f"✓ Posted to Telegraph: {url}")
            return url
        else:
            print(f"✗ Telegraph error: {result}")
            return ''
    except Exception as e:
        print(f"✗ Telegraph error: {e}")
        return ''

# ── Platform 3: Mastodon ──────────────────────────────────────────────────────
def post_to_mastodon(text):
    try:
        access_token = os.environ.get('MASTODON_ACCESS_TOKEN', '')
        if not access_token:
            print("✗ Mastodon: skipped (secret not set)")
            return False
        if not text:
            print("✗ Mastodon: empty text")
            return False

        instance = os.environ.get('MASTODON_INSTANCE', 'https://mastodon.social')
        print(f"  Mastodon text length: {len(text)} chars")

        response = requests.post(
            f'{instance}/api/v1/statuses',
            headers={'Authorization': f'Bearer {access_token}'},
            data={'status': text, 'visibility': 'public'},
            timeout=15
        )

        print(f"  Mastodon status code: {response.status_code}")

        if not response.text.strip():
            print("✗ Mastodon: empty response")
            return False

        result = response.json()
        if 'id' in result:
            print(f"✓ Posted to Mastodon: {result.get('url', '')}")
            return True
        else:
            print(f"✗ Mastodon error: {result}")
            return False
    except Exception as e:
        print(f"✗ Mastodon error: {type(e).__name__}: {e}")
        return False

# ── Platform 4: Telegram channel ─────────────────────────────────────────────
def post_to_telegram_channel(text):
    try:
        requests.post(
            f'https://api.telegram.org/bot{os.environ["TELEGRAM_TOKEN"]}/sendMessage',
            json={
                'chat_id': os.environ['TELEGRAM_CHANNEL_ID'],
                'text': text,
                'parse_mode': 'HTML'
            },
            timeout=10
        )
        print("✓ Posted to Telegram channel")
        return True
    except Exception as e:
        print(f"✗ Telegram error: {e}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("Agent 4: Traffic Posting Starting")
    print("=" * 50)

    published = get_products_by_status('published')
    pending = [p for p in published if not p.get('traffic_posted')]

    if not pending:
        print("No products need traffic posting. Exiting.")
        return

    product = pending[0]
    print(f"\nPosting traffic for: {product['gumroad_title']}")
    print("\nGenerating content via Groq (one call per platform)...")

    # Generate each platform separately — avoids parsing failures
    devto_title, devto_body     = generate_devto(product)
    telegraph_title, telegraph_body = generate_telegraph(product)
    mastodon_text               = generate_mastodon(product)
    telegram_text               = generate_telegram(product)

    print(f"\nContent ready. Posting to platforms...")
    results = {}

    results['devto'] = post_to_devto(
        devto_title, devto_body,
        product.get('devto_tags', ['productivity', 'ai'])
    )
    results['telegraph'] = post_to_telegraph(telegraph_title, telegraph_body)
    results['mastodon']  = post_to_mastodon(mastodon_text)
    results['telegram']  = post_to_telegram_channel(telegram_text)

    update_product_status(product['id'], 'published', {
        'traffic_posted': True,
        'traffic_posted_at': datetime.now().isoformat(),
        'post_urls': {k: v for k, v in results.items() if v}
    })

    successes = sum(1 for v in results.values() if v)
    total = len(results)

    send_telegram(
        f"📣 <b>Agent 4 — Traffic Done</b>\n\n"
        f"📦 {product['gumroad_title']}\n"
        f"🔗 {product['gumroad_url']}\n\n"
        f"{'✅' if results.get('devto')      else '❌'} Dev.to\n"
        f"{'✅' if results.get('telegraph')  else '❌'} Telegraph\n"
        f"{'✅' if results.get('mastodon')   else '❌'} Mastodon\n"
        f"{'✅' if results.get('telegram')   else '❌'} Telegram\n\n"
        f"Posted {successes}/{total} platforms 🚀"
    )

    print(f"\nAgent 4: Done ✓  ({successes}/{total} platforms posted)")

if __name__ == '__main__':
    main()
