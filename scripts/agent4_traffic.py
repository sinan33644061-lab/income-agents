import os
import sys
import json
import requests
import tweepy
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

Write ALL sections below. Use exact labels:

TWITTER:
[Max 260 chars. Strong hook. Include Gumroad link. 2-3 hashtags.]

DEVTO_TITLE:
[Helpful article title, sounds like advice not an ad, max 80 chars]

DEVTO_BODY:
[300-word helpful article in markdown. Para 1: teach something useful about {product['niche']}. Para 2: explain the problem your product solves. Para 3: introduce product naturally with link {product['gumroad_url']}.]

HASHNODE_TITLE:
[Slightly different title variation from DEVTO_TITLE]

HASHNODE_BODY:
[300-word article, same structure as DEVTO_BODY but reworded. Include link {product['gumroad_url']}.]

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
        'twitter':        extract('TWITTER',        'DEVTO_TITLE'),
        'devto_title':    extract('DEVTO_TITLE',    'DEVTO_BODY'),
        'devto_body':     extract('DEVTO_BODY',     'HASHNODE_TITLE'),
        'hashnode_title': extract('HASHNODE_TITLE', 'HASHNODE_BODY'),
        'hashnode_body':  extract('HASHNODE_BODY',  'TELEGRAM'),
        'telegram':       extract('TELEGRAM',        None),
    }

# ── Platform 1: Twitter ───────────────────────────────────────────────────────
def post_to_twitter(text):
    try:
        client = tweepy.Client(
            consumer_key=os.environ['TWITTER_API_KEY'],
            consumer_secret=os.environ['TWITTER_API_SECRET'],
            access_token=os.environ['TWITTER_ACCESS_TOKEN'],
            access_token_secret=os.environ['TWITTER_ACCESS_SECRET']
        )
        client.create_tweet(text=text[:280])
        print("✓ Posted to Twitter")
        return True
    except Exception as e:
        print(f"✗ Twitter error: {e}")
        return False

# ── Platform 2: Dev.to ────────────────────────────────────────────────────────
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
            }
        )
        result = response.json()
        url = result.get('url', '')
        print(f"✓ Posted to Dev.to: {url}")
        return url
    except Exception as e:
        print(f"✗ Dev.to error: {e}")
        return ''

# ── Platform 3: Hashnode (fixed API) ─────────────────────────────────────────
def post_to_hashnode(title, body, tags, publication_id):
    try:
        api_key = os.environ.get('HASHNODE_API_KEY', '')
        if not api_key:
            print("✗ Hashnode: skipped (secret not set)")
            return ''

        # Convert tag names to Hashnode format
        tag_objects = [{'slug': t.lower().replace(' ', '-'), 'name': t} for t in tags[:5]]

        query = """
        mutation PublishPost($input: PublishPostInput!) {
          publishPost(input: $input) {
            post {
              url
            }
          }
        }
        """
        variables = {
            'input': {
                'title': title,
                'contentMarkdown': body,
                'publicationId': publication_id,
                'tags': tag_objects
            }
        }

        response = requests.post(
            'https://gql.hashnode.com/',
            headers={
                'Authorization': api_key,
                'Content-Type': 'application/json'
            },
            json={'query': query, 'variables': variables},
            timeout=15
        )

        # Debug: print raw response if something goes wrong
        if not response.text.strip():
            print("✗ Hashnode: empty response from server")
            return ''

        result = response.json()

        # Check for GraphQL errors
        if 'errors' in result:
            print(f"✗ Hashnode GraphQL error: {result['errors']}")
            return ''

        url = result.get('data', {}).get('publishPost', {}).get('post', {}).get('url', '')
        if url:
            print(f"✓ Posted to Hashnode: {url}")
        else:
            print(f"✗ Hashnode: unexpected response: {result}")
        return url

    except Exception as e:
        print(f"✗ Hashnode error: {e}")
        return ''

# ── Platform 4: Telegram channel ─────────────────────────────────────────────
def post_to_telegram_channel(text):
    try:
        token = os.environ['TELEGRAM_TOKEN']
        channel_id = os.environ['TELEGRAM_CHANNEL_ID']
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={
                'chat_id': channel_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            },
            timeout=10
        )
        print("✓ Posted to Telegram channel")
        return True
    except Exception as e:
        print(f"✗ Telegram channel error: {e}")
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

    results['twitter'] = post_to_twitter(copy['twitter'])

    results['devto'] = post_to_devto(
        copy['devto_title'],
        copy['devto_body'],
        product.get('devto_tags', ['productivity', 'ai'])
    )

    results['hashnode'] = post_to_hashnode(
        copy['hashnode_title'],
        copy['hashnode_body'],
        product.get('hashnode_tags', ['AI', 'Productivity']),
        os.environ.get('HASHNODE_PUBLICATION_ID', '')
    )

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
        f"Posted {successes}/{total} platforms:\n"
        f"{'✅' if results.get('twitter')  else '❌'} Twitter\n"
        f"{'✅' if results.get('devto')    else '❌'} Dev.to\n"
        f"{'✅' if results.get('hashnode') else '❌'} Hashnode\n"
        f"{'✅' if results.get('telegram') else '❌'} Telegram\n\n"
        f"Traffic is live! 🚀"
    )

    print(f"\nAgent 4: Done ✓  ({successes}/{total} platforms posted)")

if __name__ == '__main__':
    main()
