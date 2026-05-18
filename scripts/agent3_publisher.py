import os
import sys
import requests
sys.path.append('scripts')
from helpers import get_products_by_status, update_product_status, send_telegram

def create_gumroad_product(product):
    token = os.environ['GUMROAD_TOKEN']

    response = requests.post(
        'https://api.gumroad.com/v2/products',
        headers={'Authorization': f'Bearer {token}'},
        data={
            'name': product['gumroad_title'],
            'description': product['gumroad_desc'],
            'price': int(product['price'] * 100),
            'published': 'true',
            'tags[]': product['keywords']
        }
    )
    result = response.json()
    if not result.get('success'):
        raise Exception(f"Gumroad error: {result}")
    return result['product']

def upload_pdf_to_gumroad(product_id, pdf_path, token):
    with open(pdf_path, 'rb') as f:
        response = requests.put(
            f'https://api.gumroad.com/v2/products/{product_id}/files',
            headers={'Authorization': f'Bearer {token}'},
            files={'file': (os.path.basename(pdf_path), f, 'application/pdf')}
        )
    return response.json()

def main():
    print("Agent 3: Starting Gumroad publishing...")

    pending = get_products_by_status('pdf_ready')
    if not pending:
        print("No PDF-ready products. Exiting.")
        return

    product = pending[0]
    token = os.environ['GUMROAD_TOKEN']

    gumroad_product = create_gumroad_product(product)
    product_id = gumroad_product['id']
    gumroad_url = gumroad_product['short_url']
    print(f"Created Gumroad product: {gumroad_url}")

    upload_result = upload_pdf_to_gumroad(product_id, product['pdf_path'], token)
    print(f"PDF uploaded: {upload_result}")

    update_product_status(product['id'], 'published', {
        'gumroad_product_id': product_id,
        'gumroad_url': gumroad_url
    })

    send_telegram(
        f"🛒 <b>Agent 3 done</b>\n"
        f"Product LIVE on Gumroad!\n"
        f"Title: {product['gumroad_title']}\n"
        f"Price: ${product['price']}\n"
        f"URL: {gumroad_url}"
    )
    print("Agent 3: Done.")

if __name__ == '__main__':
    main()
