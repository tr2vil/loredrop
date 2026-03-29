import json
import requests
from flask import current_app


def _api_url(method):
    token = current_app.config['TELEGRAM_TOKEN']
    return f'https://api.telegram.org/bot{token}/{method}'


def _chat_id():
    return current_app.config['TELEGRAM_CHAT_ID']


def send_message(text, chat_id=None, parse_mode='HTML', reply_markup=None):
    """Send a text message to Telegram."""
    payload = {
        'chat_id': chat_id or _chat_id(),
        'text': text,
        'parse_mode': parse_mode,
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    resp = requests.post(_api_url('sendMessage'), json=payload)
    return resp.json()


def send_topic_choices(topics):
    """Send recommended topics with detailed info and inline keyboard buttons.

    Args:
        topics: list of RecommendedTopic model instances
    """
    lines = ['📋 <b>오늘의 추천 주제</b>\n']

    for i, t in enumerate(topics, 1):
        lines.append(f'<b>{i}. {t.title}</b>')
        if t.description:
            for desc_line in t.description.split('\n'):
                desc_line = desc_line.strip()
                if not desc_line:
                    continue
                if desc_line.startswith('EN:'):
                    lines.append(f'<i>({desc_line[3:].strip()})</i>')
                elif desc_line.startswith('Why:'):
                    lines.append(f'💡 {desc_line[4:].strip()}')
                elif desc_line.startswith('Points:'):
                    lines.append(f'{desc_line[7:].strip()}')
                elif desc_line.startswith('Keywords:'):
                    lines.append(f'🏷 {desc_line}')
                else:
                    lines.append(desc_line)
        lines.append('')

    lines.append('---')
    lines.append('원하는 주제를 선택하세요 👇')
    text = '\n'.join(lines)

    # Build inline keyboard: topic buttons + action buttons
    buttons = []
    for t in topics:
        # Truncate title for button (callback_data max 64 bytes)
        btn_text = t.title if len(t.title) <= 40 else t.title[:37] + '...'
        buttons.append([{
            'text': f'✅ {btn_text}',
            'callback_data': json.dumps({'a': 'sel', 'id': t.id})
        }])

    # Add regenerate and custom topic buttons
    buttons.append([
        {
            'text': '🔄 주제 재생성',
            'callback_data': json.dumps({'a': 'regen'})
        },
        {
            'text': '✏️ 직접 입력',
            'callback_data': json.dumps({'a': 'custom'})
        }
    ])

    resp = requests.post(_api_url('sendMessage'), json={
        'chat_id': _chat_id(),
        'text': text,
        'parse_mode': 'HTML',
        'reply_markup': {'inline_keyboard': buttons},
    })
    return resp.json()


def answer_callback(callback_query_id, text=''):
    """Answer a callback query (dismiss the loading indicator)."""
    requests.post(_api_url('answerCallbackQuery'), json={
        'callback_query_id': callback_query_id,
        'text': text,
    })


def set_webhook(url):
    """Set the Telegram webhook URL."""
    resp = requests.post(_api_url('setWebhook'), json={'url': url})
    return resp.json()


def delete_webhook():
    """Delete the current webhook."""
    resp = requests.post(_api_url('deleteWebhook'))
    return resp.json()
