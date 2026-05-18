import json
import os
import requests
from datetime import datetime

DB_PATH = 'products.json'

def load_db():
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def save_db(data):
    data['last_updated'] = datetime.now().isoformat()
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def call_groq(prompt, max_tokens=4000):
    api_key = os.environ['GROQ_API_KEY']
    response = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'llama3-8b-8192',
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}]
        }
    )
    return response.json()['choices'][0]['message']['content']

def send_telegram(message):
    token = os.environ['TELEGRAM_TOKEN']
    chat_id = os.environ['TELEGRAM_CHAT_ID']
    requests.post(
        f'https://api.telegram.org/bot{token}/sendMessage',
        json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
    )

def get_products_by_status(status):
    db = load_db()
    return [p for p in db['products'] if p.get('status') == status]

def update_product_status(product_id, status, extra_fields=None):
    db = load_db()
    for p in db['products']:
        if p['id'] == product_id:
            p['status'] = status
            p['updated_at'] = datetime.now().isoformat()
            if extra_fields:
                p.update(extra_fields)
            break
    save_db(db)
