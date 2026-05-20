import os
import sys
import json
import requests
import tweepy
from datetime import datetime

sys.path.append('scripts')
from helpers import get_products_by_status, update_product_status, send_telegram, call_groq

# ── Generate all social copy in one Groq call ─────────────────────────────────
def generate_social_copy(product):
    prompt = f"""
Write social media and blog content for this digital product:

Title: {product['gumroad_title']}
Description: {product['gumroad_desc']}
Price: ${product['price']}
Link: {product['gumroad_url']}
Audience: {product['target_audience']}
Niche: {product['niche']}

Write ALL of the following. Use exact labels so I can parse them:

TWITTER:
[Max 260 chars. Strong hook line. Mention the product value. Include the Gumroad link. 2-3 hashtags.]

DEVTO_TITLE:
[Helpful article title, sounds like genuine advice not an ad, max 80 chars]

DEVTO_BODY:
[A 300-word helpful article. Paragraph 1: teach something genuinely useful about {product['niche']}. Paragraph 2: explain the problem your product solves. Paragraph 3: introduce the product naturally with the link {product['gumroad_url']}. Sound like a real helpful developer, not a marketer.]

HASHNODE_TITLE:
[Same as DEVTO_TITLE or a slight variation]

HASHNODE_BODY:
[A 300-word article similar to DEVTO_BODY but slightly reworded so it's not duplicate content. Same structure, different phrasing.]

BLOGGER_TITLE:
[SEO-optimized title for Google search, include main keyword, max 65 chars]

BLOGGER_BODY:
[A 400-word SEO blog post. Include keyword naturally. Structure: intro, 3 short sections with subheadings, conclusion with link to {product['gumroad_url']}. Written for Google ranking.]

TELEGRAM:
[Short punchy message for a Telegram channel. 2-3 lines max. Emoji. Link at end. Creates urgency or curiosity.]
"""

    response = call_groq(prompt, max_tokens=3000)

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
        'hashnode_body':  extract('HASHNODE_BODY',  'BLOGGER_TITLE'),
        'blogger_title':  extract('BLOGGER_TITLE',  'BLOGGER_BODY'),
        'blogger_body':   extract('BLOGGER_BODY',   'TELEGRAM'),
        'telegram':       extract('TELEGRAM',        None),
    }

# ── Platform 1: Twitter / X ───────────────────────────────────────────────────
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
        api_key = os.environ['DEVTO_API_KEY']
        response = requests.post(
            'https://dev.to/api/articles',
            headers={
                'api-key': api_key,
                'Content-Type': 'application/json'
            },
            json={
                'article': {
                    'title': title,
                    'body_markdown': body,
                    'published': True,
                    'tags': tags[:4]  # Dev.to allows max 4 tags
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

# ── Platform 3: Hashnode ──────────────────────────────────────────────────────
def post_to_hashnode(title, body, tags, publication_id):
    try:
        api_key = os.environ['HASHNODE_API_KEY']

        # Hashnode uses GraphQL API
        query = """
        mutation PublishPost($input: PublishPostInput!) {
          publishPost(input: $input) {
            post {
              url
              title
            }
          }
        }
        """
        tag_objects = [{'name': t, 'slug': t.lower().replace(' ', '-')} for t in tags[:5]]

        variables = {
            'input': {
                'title': title,
                'contentMarkdown': body,
                'publicationId': publication_id,
                'tags': tag_objects
            }
        }

        response = requests.post(
            'https://gql.hashnode.com',
            headers={
                'Authorization': api_key,
                'Content-Type': 'application/json'
            },
            json={'query': query, 'variables': variables}
        )
        result = response.json()
        post_data = result.get('data', {}).get('publishPost', {}).get('post', {})
        url = post_data.get('url', '')
        print(f"✓ Posted to Hashnode: {url}")
        return url
    except Exception as e:
        print(f"✗ Hashnode error: {e}")
        return ''

# ── Platform 4: Blogger ───────────────────────────────────────────────────────
def post_to_blogger(title, body, labels):
    try:
        api_key = os.environ['BLOGGER_API_KEY']
        blog_id = os.environ['BLOGGER_BLOG_ID']

        # Convert markdown-style body to basic HTML
        html_body = body.replace('\n\n', '</p><p>').replace('\n', '<br>')
        html_body = f'<p>{html_body}</p>'

        response = requests.post(
            f'https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts',
            params={'key': api_key},
            headers={'Content-Type': 'application/json'},
            json={
                'title': title,
                'content': html_body,
                'labels': labels
            }
        )
        result = response.json()
        url = result.get('url', '')
        print(f"✓ Posted to Blogger: {url}")
        return url
    except Exception as e:
        print(f"✗ Blogger error: {e}")
        return ''

# ── Platform 5: Telegram channel ─────────────────────────────────────────────
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
            }
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

    # Get published products that haven't been traffic-posted yet
    published = get_products_by_status('published')
    pending = [p for p in published if not p.get('traffic_posted')]

    if not pending:
        print("No products need traffic posting. Exiting.")
        return

    product = pending[0]
    print(f"\nPosting traffic for: {product['gumroad_title']}")

    # Generate all content in one Groq call
    print("\nGenerating social copy via Groq...")
    copy = generate_social_copy(product)

    results = {}

    # Post to all platforms
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
        os.environ['HASHNODE_PUBLICATION_ID']
    )

    results['blogger'] = post_to_blogger(
        copy['blogger_title'],
        copy['blogger_body'],
        product.get('blogger_labels', ['Digital Products', 'AI'])
    )

    results['telegram'] = post_to_telegram_channel(copy['telegram'])

    # Update product status
    update_product_status(product['id'], 'published', {
        'traffic_posted': True,
        'traffic_posted_at': datetime.now().isoformat(),
        'post_urls': results
    })

    # Count successes
    successes = sum(1 for v in results.values() if v)
    total = len(results)

    # Send summary alert
    send_telegram(
        f"📣 <b>Agent 4 — Traffic Done</b>\n\n"
        f"📦 Product: {product['gumroad_title']}\n"
        f"🔗 Gumroad: {product['gumroad_url']}\n\n"
        f"Posted to {successes}/{total} platforms:\n"
        f"{'✅' if results['twitter']  else '❌'} Twitter\n"
        f"{'✅' if results['devto']    else '❌'} Dev.to\n"
        f"{'✅' if results['hashnode'] else '❌'} Hashnode\n"
        f"{'✅' if results['blogger']  else '❌'} Blogger\n"
        f"{'✅' if results['telegram'] else '❌'} Telegram channel\n\n"
        f"Traffic is live — waiting for sales! 🤞"
    )

    print(f"\nAgent 4: Done ✓  ({successes}/{total} platforms posted)")

if __name__ == '__main__':
    main()
