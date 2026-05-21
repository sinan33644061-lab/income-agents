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

Write ALL sections. Use exact labels:

TWITTER:
[Max 260 chars. Strong hook. Include Gumroad link. 2-3 hashtags.]

DEVTO_TITLE:
[Helpful article title, sounds like advice not an ad, max 80 chars]

DEVTO_BODY:
[300-word helpful article in markdown. Para 1: teach something useful about {product['niche']}. Para 2: explain the problem solved. Para 3: introduce product naturally with link {product['gumroad_url']}.]

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
    except tweepy.errors.Unauthorized as e:
        print(f"✗ Twitter 401: {e.response.text if hasattr(e, 'response') else e}")
        return False
    except Exception as e:
        print(f"✗ Twitter error: {type(e).__name__}: {e}")
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
            },
            timeout=15
        )
        result = response.json()
        url = result.get('url', '')
        print(f"✓ Posted to Dev.to: {url}")
        return url
    except Exception as e:
        print(f"✗ Dev.to error: {e}")
        return ''

# ── Platform 3: Hashnode (draft → publish flow) ───────────────────────────────
def post_to_hashnode(title, body, tags, publication_id):
    try:
        api_key = os.environ.get('HASHNODE_API_KEY', '')
        if not api_key or not publication_id:
            print("✗ Hashnode: skipped (secrets missing)")
            return ''

        headers = {
            'Authorization': api_key,   # NO "Bearer" prefix
            'Content-Type': 'application/json'
        }

        # Tags must be objects with name + slug
        tag_objects = [
            {'name': t, 'slug': t.lower().replace(' ', '-')}
            for t in tags[:5]
        ]

        # Step 1: Create draft
        create_mutation = """
        mutation CreateDraft($input: CreateDraftInput!) {
          createDraft(input: $input) {
            draft { id title }
          }
        }
        """
        r1 = requests.post(
            'https://gql.hashnode.com/',
            headers=headers,
            json={
                'query': create_mutation,
                'variables': {
                    'input': {
                        'title': title,
                        'contentMarkdown': body,
                        'publicationId': publication_id,
                        'tags': tag_objects
                    }
                }
            },
            timeout=20
        )

        print(f"Hashnode createDraft status: {r1.status_code}")

        if not r1.text.strip() or r1.text.strip().startswith('<!'):
            print(f"✗ Hashnode: got HTML instead of JSON — {r1.text[:80]}")
            return ''

        data1 = r1.json()
        if 'errors' in data1:
            print(f"✗ Hashnode createDraft errors: {data1['errors']}")
            return ''

        draft_id = data1.get('data', {}).get('createDraft', {}).get('draft', {}).get('id')
        if not draft_id:
            print(f"✗ Hashnode: no draft ID returned: {json.dumps(data1)[:200]}")
            return ''

        print(f"  Draft created: {draft_id}")

        # Step 2: Publish the draft
        publish_mutation = """
        mutation PublishDraft($input: PublishDraftInput!) {
          publishDraft(input: $input) {
            post { url title }
          }
        }
        """
        r2 = requests.post(
            'https://gql.hashnode.com/',
            headers=headers,
            json={
                'query': publish_mutation,
                'variables': {'input': {'id': draft_id}}
            },
            timeout=20
        )

        print(f"Hashnode publishDraft status: {r2.status_code}")

        if not r2.text.strip() or r2.text.strip().startswith('<!'):
            print("✗ Hashnode: bad response on publishDraft")
            return ''

        data2 = r2.json()
        if 'errors' in data2:
            print(f"✗ Hashnode publishDraft errors: {data2['errors']}")
            return ''

        url = data2.get('data', {}).get('publishDraft', {}).get('post', {}).get('url', '')
        if url:
            print(f"✓ Posted to Hashnode: {url}")
        else:
            print(f"✗ Hashnode: no URL returned: {json.dumps(data2)[:200]}")
        return url

    except Exception as e:
        print(f"✗ Hashnode error: {type(e).__name__}: {e}")
        return ''

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
        f"{'✅' if results.get('twitter')  else '❌'} Twitter\n"
        f"{'✅' if results.get('devto')    else '❌'} Dev.to\n"
        f"{'✅' if results.get('hashnode') else '❌'} Hashnode\n"
        f"{'✅' if results.get('telegram') else '❌'} Telegram\n\n"
        f"Posted {successes}/{total} platforms 🚀"
    )

    print(f"\nAgent 4: Done ✓  ({successes}/{total} platforms posted)")

if __name__ == '__main__':
    main()
