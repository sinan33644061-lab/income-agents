import os
import sys
import json
import requests
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib import colors
sys.path.append('scripts')
from helpers import load_db, call_groq, update_product_status, send_telegram, get_products_by_status

def generate_content(product):
    ptype = product['product_type']
    title = product['title']
    audience = product['target_audience']

    if ptype == 'prompt_pack':
        prompt = f"""
Create a premium prompt pack called "{title}" for {audience}.

Write exactly 50 prompts. Each prompt must:
- Start with "Act as..." or a clear role setup
- Be specific and immediately usable
- Include context and expected output format
- Be genuinely valuable

Format each prompt as:
## Prompt [NUMBER]: [Short Title]
[The full prompt text]

After all prompts write:
---METADATA---
GUMROAD_TITLE: {title}
GUMROAD_DESC: [150 word compelling sales description starting with a pain point]
TWITTER_HOOK: [One punchy tweet promoting this, under 250 chars]
PINTEREST_TITLE: [SEO title under 80 chars]
"""
    elif ptype == 'ebook':
        prompt = f"""
Write a complete, valuable ebook called "{title}" for {audience}.

Structure:
- Introduction (200 words)
- Chapter 1 (400 words)
- Chapter 2 (400 words)
- Chapter 3 (400 words)
- Chapter 4 (400 words)
- Chapter 5 (400 words)
- Conclusion + Next Steps (200 words)

Make it genuinely useful. Real advice, real examples, actionable steps.

After the ebook write:
---METADATA---
GUMROAD_TITLE: {title}
GUMROAD_DESC: [150 word compelling sales description]
TWITTER_HOOK: [One punchy tweet, under 250 chars]
PINTEREST_TITLE: [SEO title under 80 chars]
"""
    else:
        prompt = f"""
Create a comprehensive cheat sheet / template called "{title}" for {audience}.

Include:
- Quick reference tables
- Step by step checklists
- Key formulas or frameworks
- Common mistakes to avoid
- Pro tips section

Make it dense with value — something worth printing and keeping.

After the content write:
---METADATA---
GUMROAD_TITLE: {title}
GUMROAD_DESC: [150 word compelling sales description]
TWITTER_HOOK: [One punchy tweet, under 250 chars]
PINTEREST_TITLE: [SEO title under 80 chars]
"""

    return call_groq(prompt, max_tokens=4000)

def parse_metadata(content):
    meta = {}
    if '---METADATA---' in content:
        parts = content.split('---METADATA---')
        body = parts[0].strip()
        meta_text = parts[1].strip()

        for line in meta_text.split('\n'):
            if line.startswith('GUMROAD_TITLE:'):
                meta['gumroad_title'] = line.replace('GUMROAD_TITLE:', '').strip()
            elif line.startswith('GUMROAD_DESC:'):
                meta['gumroad_desc'] = line.replace('GUMROAD_DESC:', '').strip()
            elif line.startswith('TWITTER_HOOK:'):
                meta['twitter_hook'] = line.replace('TWITTER_HOOK:', '').strip()
            elif line.startswith('PINTEREST_TITLE:'):
                meta['pinterest_title'] = line.replace('PINTEREST_TITLE:', '').strip()
        return body, meta
    return content, {}

def build_pdf(title, content, output_path):
    os.makedirs('output', exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=26,
        textColor=colors.HexColor('#6c63ff'),
        spaceAfter=24,
        alignment=1
    )
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#333333'),
        spaceBefore=20,
        spaceAfter=10
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=12,
        leading=22,
        spaceAfter=10
    )

    story = []
    story.append(Paragraph(title, title_style))
    story.append(HRFlowable(width='100%', color=colors.HexColor('#6c63ff')))
    story.append(Spacer(1, 0.3 * inch))

    for line in content.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.1 * inch))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], h2_style))
        elif line.startswith('# '):
            story.append(Paragraph(line[2:], h2_style))
        else:
            safe = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe, body_style))

    doc.build(story)
    print(f"PDF saved to {output_path}")

def main():
    print("Agent 2: Starting product creation...")

    pending = get_products_by_status('researched')
    if not pending:
        print("No researched products found. Exiting.")
        return

    product = pending[0]
    print(f"Creating product: {product['title']}")

    raw_content = generate_content(product)
    body, meta = parse_metadata(raw_content)

    pdf_filename = f"output/product_{product['id'][:8]}.pdf"
    build_pdf(
        meta.get('gumroad_title', product['title']),
        body,
        pdf_filename
    )

    update_product_status(product['id'], 'pdf_ready', {
        'gumroad_title': meta.get('gumroad_title', product['title']),
        'gumroad_desc': meta.get('gumroad_desc', ''),
        'twitter_hook': meta.get('twitter_hook', ''),
        'pinterest_title': meta.get('pinterest_title', product['title']),
        'pdf_path': pdf_filename
    })

    send_telegram(
        f"📄 <b>Agent 2 done</b>\n"
        f"PDF created: {meta.get('gumroad_title', product['title'])}\n"
        f"File: {pdf_filename}"
    )
    print("Agent 2: Done.")

if __name__ == '__main__':
    main()
