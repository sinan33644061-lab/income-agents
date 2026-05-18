import os
import sys
import requests
from datetime import datetime, timedelta
sys.path.append('scripts')
from helpers import send_telegram, load_db, save_db

def fetch_recent_sales(hours=1):
    token = os.environ['GUMROAD_TOKEN']
    after = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%SZ')
    response = requests.get(
        'https://api.gumroad.com/v2/sales',
        headers={'Authorization': f'Bearer {token}'},
        params={'after': after}
    )
    data = response.json()
    return data.get('sales', [])

def fetch_total_revenue():
    token = os.environ['GUMROAD_TOKEN']
    response = requests.get(
        'https://api.gumroad.com/v2/user',
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json().get('user', {})

def main():
    print("Agent 5: Checking sales...")

    sales = fetch_recent_sales(hours=1)
    user = fetch_total_revenue()

    if sales:
        total_new = sum(s.get('price', 0) for s in sales) / 100
        for sale in sales:
            product_name = sale.get('product_name', 'Unknown')
            price = sale.get('price', 0) / 100
            send_telegram(
                f"💰 <b>SALE!</b>\n"
                f"Product: {product_name}\n"
                f"Amount: ${price:.2f}\n"
                f"Time: {sale.get('created_at', 'now')}\n\n"
                f"Total this hour: ${total_new:.2f}\n"
                f"Keep going — agents are working!"
            )
    else:
        print("No new sales in the last hour.")

    # Daily summary at midnight
    now = datetime.utcnow()
    if now.hour == 0:
        db = load_db()
        total_products = len(db['products'])
        published = len([p for p in db['products'] if p.get('status') == 'published'])
        send_telegram(
            f"📊 <b>Daily summary</b>\n"
            f"Total products: {total_products}\n"
            f"Live on Gumroad: {published}\n"
            f"Agents running: all 5 active"
        )

if __name__ == '__main__':
    main()
