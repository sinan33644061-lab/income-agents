import os
import sys
import requests
sys.path.append('scripts')
from helpers import get_products_by_status, update_product_status, send_telegram

def create_gumroad_product(product, token):
    response = requests.post(
        'https://api.gumroad.com/v2/products',
        headers={'Authorization': f'Bearer {token}'},
        data={
            'name': product.get('gumroad_title', product['title']),
            'description': product.get('gumroad_desc', ''),
            'price': int(float(product['price']) * 100),
            'published': 'true',
        }
    )
    result = response.json()
    if not result.get('success'):
        raise Exception(f"Gumroad create error: {result}")
    return result['product']

def upload_pdf_to_gumroad(product_id, pdf_path, token):
    if not os.path.exists(pdf_path):
        raise Exception(f"PDF not found at path: {pdf_path}")

    with open(pdf_path, 'rb') as f:
        response = requests.put(
            f'https://api.gumroad.com/v2/products/{product_id}/files',
            headers={'Authorization': f'Bearer {token}'},
            files={'file': (os.path.basename(pdf_path), f, 'application/pdf')}
        )

    # Gumroad returns empty body on success — handle gracefully
    print(f"Upload response status: {response.status_code}")
    if response.status_code in (200, 201, 204):
        print("PDF upload successful")
        return True

    # Try to parse JSON only if there's content
    if response.text.strip():
        try:
            result = response.json()
            print(f"Upload response: {result}")
            return result
        except Exception:
            print(f"Upload raw response: {response.text}")

    # If we get here with a non-success status code, raise
    if response.status_code >= 400:
        raise Exception(f"PDF upload failed with status {response.status_code}: {response.text}")

    return True

def main():
    print("Agent 3: Starting Gumroad publishing...")

    pending = get_products_by_status('pdf_ready')
    if not pending:
        print("No PDF-ready products found. Exiting.")
        return

    product = pending[0]
    token = os.environ['GUMROAD_TOKEN']

    print(f"Publishing: {product.get('gumroad_title', product['title'])}")

    # Create the product listing
    gumroad_product = create_gumroad_product(product, token)
    product_id = gumroad_product['id']
    gumroad_url = gumroad_product['short_url']
    print(f"✓ Created Gumroad product: {gumroad_url}")

    # Upload the PDF
    upload_pdf_to_gumroad(product_id, product['pdf_path'], token)

    # Update database
    update_product_status(product['id'], 'published', {
        'gumroad_product_id': product_id,
        'gumroad_url': gumroad_url,
        'gumroad_title': product.get('gumroad_title', product['title']),
        'gumroad_desc': product.get('gumroad_desc', ''),
    })

    send_telegram(
        f"🛒 <b>Agent 3 — Product Live!</b>\n\n"
        f"📦 {product.get('gumroad_title', product['title'])}\n"
        f"💰 ${product['price']}\n"
        f"🔗 {gumroad_url}\n\n"
        f"Agent 4 posts traffic in 1 hour..."
    )

    print(f"Agent 3: Done ✓  —  {gumroad_url}")

if __name__ == '__main__':
    main()
