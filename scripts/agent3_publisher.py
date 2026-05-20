import os
import sys
import requests
sys.path.append('scripts')
from helpers import get_products_by_status, update_product_status, send_telegram

# ── Upload PDF to GitHub Releases (free, reliable, public URL) ────────────────
def upload_to_github_releases(pdf_path, product_id):
    token = os.environ['GITHUB_TOKEN']
    repo = os.environ['GITHUB_REPOSITORY']   # auto-set by GitHub Actions
    tag = f"product-{product_id[:8]}"
    pdf_name = os.path.basename(pdf_path)

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }

    # Step 1: Create a release
    release_resp = requests.post(
        f'https://api.github.com/repos/{repo}/releases',
        headers=headers,
        json={
            'tag_name': tag,
            'name': tag,
            'body': 'Auto-generated product release',
            'draft': False,
            'prerelease': False
        }
    )
    release_data = release_resp.json()

    if 'upload_url' not in release_data:
        raise Exception(f"GitHub release creation failed: {release_data}")

    upload_url = release_data['upload_url'].replace('{?name,label}', '')
    release_id = release_data['id']
    print(f"✓ GitHub release created (id: {release_id})")

    # Step 2: Upload the PDF file to the release
    with open(pdf_path, 'rb') as f:
        upload_resp = requests.post(
            f'{upload_url}?name={pdf_name}',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/pdf'
            },
            data=f
        )

    asset_data = upload_resp.json()
    if 'browser_download_url' not in asset_data:
        raise Exception(f"GitHub asset upload failed: {asset_data}")

    download_url = asset_data['browser_download_url']
    print(f"✓ PDF uploaded to GitHub: {download_url}")
    return download_url

# ── Create Gumroad product with download URL ──────────────────────────────────
def create_gumroad_product(product, token, pdf_download_url):
    description = product.get('gumroad_desc', '')

    full_description = f"""{description}

---
📥 After purchase, you will receive a download link for your PDF.

✅ Instant delivery
✅ Works on any device
✅ Lifetime access"""

    response = requests.post(
        'https://api.gumroad.com/v2/products',
        headers={'Authorization': f'Bearer {token}'},
        data={
            'name': product.get('gumroad_title', product['title']),
            'description': full_description,
            'price': int(float(product['price']) * 100),
            'published': 'true',
            'url': pdf_download_url,
        }
    )
    result = response.json()
    if not result.get('success'):
        raise Exception(f"Gumroad create error: {result}")

    return result['product']

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Agent 3: Starting Gumroad publishing...")

    pending = get_products_by_status('pdf_ready')
    if not pending:
        print("No PDF-ready products found. Exiting.")
        return

    product = pending[0]
    token = os.environ['GUMROAD_TOKEN']
    pdf_path = product['pdf_path']

    print(f"Publishing: {product.get('gumroad_title', product['title'])}")

    # Step 1: Upload PDF to GitHub Releases for a reliable public URL
    print("Uploading PDF to GitHub Releases...")
    pdf_url = upload_to_github_releases(pdf_path, product['id'])

    # Step 2: Create Gumroad listing with that URL
    print("Creating Gumroad listing...")
    gumroad_product = create_gumroad_product(product, token, pdf_url)
    gumroad_url = gumroad_product['short_url']
    product_id = gumroad_product['id']
    print(f"✓ Gumroad product live: {gumroad_url}")

    # Step 3: Update database
    update_product_status(product['id'], 'published', {
        'gumroad_product_id': product_id,
        'gumroad_url': gumroad_url,
        'gumroad_title': product.get('gumroad_title', product['title']),
        'gumroad_desc': product.get('gumroad_desc', ''),
        'pdf_download_url': pdf_url,
        'traffic_posted': False
    })

    send_telegram(
        f"🛒 <b>Agent 3 — Product Live!</b>\n\n"
        f"📦 {product.get('gumroad_title', product['title'])}\n"
        f"💰 ${product['price']}\n"
        f"🔗 {gumroad_url}\n\n"
        f"Agent 4 posts traffic in 1 hour..."
    )

    print(f"\nAgent 3: Done ✓")
    print(f"Gumroad URL: {gumroad_url}")
    print(f"PDF URL:     {pdf_url}")

if __name__ == '__main__':
    main()
