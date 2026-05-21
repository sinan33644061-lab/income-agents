import os
import sys
import json
import requests
from datetime import datetime

sys.path.append('scripts')
from helpers import get_products_by_status, update_product_status, send_telegram, call_groq

# ── Generate all social copy ──────────────────────────────────────────────────
def generate_social_copy(product):
    prompt = f"""Write social media and blog content for this digital product:

Title: {product['gumroad_title']}
Description: {product['gumroad_desc']}
Price: ${product['price']}
Link: {product['gumroad_url']}
Audience: {product['target_audience']}
Niche: {product['niche']}

Write ALL sections. Use exact labels:

DEVTO_TITLE:
[Helpful article title, sounds like advice not an ad, max 80 chars]

DEVTO_BODY:
[300-word helpful article in markdown. Para 1: teach something useful about {product['niche']}. Para 2: explain the problem solved. Para 3: introduce product naturally with link {product['gumroad_url']}.]

TELEGRAPH_TITLE:
[Catchy title for a Telegraph article, max 70 chars]

TELEGRAPH_BODY:
[250-word article. Engaging, helpful, ends with a clear call to action and link {product['gumroad_url']}. Plain text, no markdown.]

MASTODON:
[Max 480 chars. Helpful tip related to {product['niche']}. Mention the product naturally. Include link {product['gumroad_url']}. 2-3 relevant hashtags.]

TELEGRAM:
[2-3 lines. Emoji. Punchy. Link at end. Creates curiosity.]"""

    response = call_groq(prompt, max_tokens=2500)

    def extract(label, next_label=None):
        try:
            start = response.index(label + ':') + len(label) + 1
            if next_label and (next_label + ':') in response:
                end = response.index(next_label + ':')
            else:
                end = len(response)
            return response[start:end].strip()
        except:
            return ''

    return {
        'devto_title':      extract('DEVTO_TITLE',      'DEVTO_BODY'),
        'devto_body':       extract('DEVTO_BODY',        'TELEGRAPH_TITLE'),
        'telegraph_title':  extract('TELEGRAPH_TITLE',   'TELEGRAPH_BODY'),
        'telegraph_body':   extract('TELEGRAPH_BODY',    'MASTODON'),
        'mastodon':         extract('MASTODON',           'TELEGRAM'),
        'telegram':         extract('TELEGRAM',           None),
    }

# ── Platform 1: Dev.to ────────────────────────────────────────────────────────
def post_to_devto(title, body, tags):
    try:
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
            print("✗ Telegraph: skipped (TELEGRAPH_ACCESS_TOKEN not set)")
            return ''

        # Telegraph content must be in their node format
        # Simplest approach: split into paragraphs
        paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
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
            print("✗ Mastodon: skipped (MASTODON_ACCESS_TOKEN not set)")
            return False

        # Default to mastodon.social — change if you signed up on a different instance
        instance = os.environ.get('MASTODON_INSTANCE', 'https://mastodon.social')

        response = requests.post(
            f'{instance}/api/v1/statuses',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json={
                'status': text[:500],
                'visibility': 'public'
            },
            timeout=15
        )
        result = response.json()
        if 'id' in result:
            url = result.get('url', '')
            print(f"✓ Posted to Mastodon: {url}")
            return True
        else:
            print(f"✗ Mastodon error: {result}")
            return False
    except Exception as e:
        print(f"✗ Mastodon error: {e}")
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

    print("\nGenerating social copy via Groq...")
    copy = generate_social_copy(product)

    results = {}
    print("\nPosting to all platforms...")

    results['devto'] = post_to_devto(
        copy['devto_title'],
        copy['devto_body'],
        product.get('devto_tags', ['productivity', 'ai'])
    )

    results['telegraph'] = post_to_telegraph(
        copy['telegraph_title'],
        copy['telegraph_body']
    )

    results['mastodon'] = post_to_mastodon(copy['mastodon'])

    results['telegram'] = post_to_telegram_channel(copy['telegram'])

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
