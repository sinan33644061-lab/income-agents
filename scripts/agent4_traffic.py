import os
import sys
import requests
import tweepy
import praw
sys.path.append('scripts')
from helpers import get_products_by_status, update_product_status, send_telegram, call_groq

def generate_social_copy(product):
    prompt = f"""
Write social media posts for this digital product:

Title: {product['gumroad_title']}
Description: {product['gumroad_desc']}
Price: ${product['price']}
Link: {product['gumroad_url']}
Audience: {product['target_audience']}

Write each post below. Use exact labels:

TWITTER:
[Max 260 chars. Strong hook. 2-3 relevant hashtags. Include the link.]

PINTEREST_DESC:
[200 chars. Keyword rich. Helpful tone. Include link at end.]

REDDIT_TITLE:
[Helpful title. No selling. Sounds like genuine advice.]

REDDIT_BODY:
[3 paragraphs. Para 1: give real useful advice on the topic. Para 2: mention you made a resource. Para 3: share the link naturally. Sound human.]
"""
    response = call_groq(prompt, max_tokens=1000)

    def extract(label, next_label):
        try:
            start = response.index(label + ':') + len(label) + 1
            if next_label and next_label + ':' in response:
                end = response.index(next_label + ':')
            else:
                end = len(response)
            return response[start:end].strip()
        except:
            return ''

    return {
        'twitter': extract('TWITTER', 'PINTEREST_DESC'),
        'pinterest_desc': extract('PINTEREST_DESC', 'REDDIT_TITLE'),
        'reddit_title': extract('REDDIT_TITLE', 'REDDIT_BODY'),
        'reddit_body': extract('REDDIT_BODY', None)
    }

def post_to_twitter(text):
    client = tweepy.Client(
        consumer_key=os.environ['TWITTER_API_KEY'],
        consumer_secret=os.environ['TWITTER_API_SECRET'],
        access_token=os.environ['TWITTER_ACCESS_TOKEN'],
        access_token_secret=os.environ['TWITTER_ACCESS_SECRET']
    )
    client.create_tweet(text=text[:280])
    print("Posted to Twitter")

def post_to_pinterest(title, description, link, image_url):
    token = os.environ['PINTEREST_TOKEN']
    board_id = os.environ['PINTEREST_BOARD_ID']
    requests.post(
        'https://api.pinterest.com/v5/pins',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'board_id': board_id,
            'title': title[:100],
            'description': description[:500],
            'link': link,
            'media_source': {
                'source_type': 'image_url',
                'url': image_url
            }
        }
    )
    print("Posted to Pinterest")

def post_to_reddit(subreddit, title, body):
    reddit = praw.Reddit(
        client_id=os.environ['REDDIT_CLIENT_ID'],
        client_secret=os.environ['REDDIT_CLIENT_SECRET'],
        username=os.environ['REDDIT_USERNAME'],
        password=os.environ['REDDIT_PASSWORD'],
        user_agent='IncomeAgentBot/1.0'
    )
    sub = reddit.subreddit(subreddit)
    sub.submit(title=title, selftext=body)
    print(f"Posted to r/{subreddit}")

def main():
    print("Agent 4: Starting traffic posting...")

    published = get_products_by_status('published')
    # Filter ones not yet traffic-posted
    pending = [p for p in published if not p.get('traffic_posted')]
    if not pending:
        print("No products need traffic posting. Exiting.")
        return

    product = pending[0]
    copy = generate_social_copy(product)

    # Placeholder cover image using product title
    cover_url = f"https://via.placeholder.com/1000x1500/6c63ff/ffffff?text={requests.utils.quote(product['gumroad_title'][:30])}"

    try:
        post_to_twitter(copy['twitter'])
    except Exception as e:
        print(f"Twitter error: {e}")

    try:
        post_to_pinterest(
            product.get('pinterest_title', product['gumroad_title']),
            copy['pinterest_desc'],
            product['gumroad_url'],
            cover_url
        )
    except Exception as e:
        print(f"Pinterest error: {e}")

    try:
        post_to_reddit(
            product.get('best_subreddit', 'entrepreneur'),
            copy['reddit_title'],
            copy['reddit_body']
        )
    except Exception as e:
        print(f"Reddit error: {e}")

    update_product_status(product['id'], 'published', {
        'traffic_posted': True,
        'social_copy': copy
    })

    send_telegram(
        f"📣 <b>Agent 4 done</b>\n"
        f"Posted to Twitter, Pinterest + Reddit\n"
        f"Product: {product['gumroad_title']}"
    )
    print("Agent 4: Done.")

if __name__ == '__main__':
    main()
