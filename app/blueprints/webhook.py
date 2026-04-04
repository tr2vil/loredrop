import json
from flask import Blueprint, request, jsonify
from ..extensions import redis_client

webhook_bp = Blueprint('webhook', __name__)

# Redis key to track "waiting for custom topic input" state per chat
CUSTOM_TOPIC_STATE_KEY = 'telegram:waiting_custom:{chat_id}'


@webhook_bp.route('/telegram', methods=['POST'])
def telegram_webhook():
    """Receive Telegram Bot API updates (callback_query, message)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'ok': False}), 400

    if 'callback_query' in data:
        return _handle_callback_query(data['callback_query'])

    if 'message' in data and 'text' in data.get('message', {}):
        return _handle_text_message(data['message'])

    return jsonify({'ok': True})


def _handle_callback_query(callback_query):
    """Process inline keyboard button presses."""
    from ..services.distribution.telegram_service import answer_callback, send_message, send_topic_choices
    from ..services.content.topic_service import select_topic, generate_topics

    callback_id = callback_query.get('id')
    chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
    data_str = callback_query.get('data', '{}')

    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        answer_callback(callback_id, 'Invalid data')
        return jsonify({'ok': True})

    action = data.get('a') or data.get('action')

    # Select topic
    if action in ('sel', 'select_topic'):
        topic_id = data.get('id') or data.get('topic_id')
        try:
            selected = select_topic(topic_id, video_type='short')
            answer_callback(callback_id, f'Selected!')
            send_message(
                f'✅ <b>주제 선택 완료</b>\n\n'
                f'<b>{selected.title}</b>\n\n'
                f'웹 UI에서 Pipeline을 시작하세요:\n'
                f'http://localhost:8000/topics/',
                chat_id=chat_id
            )
        except ValueError as e:
            answer_callback(callback_id, str(e))

    # Regenerate topics
    elif action == 'regen':
        answer_callback(callback_id, 'Regenerating...')
        send_message('🔄 <b>주제를 다시 생성하고 있습니다...</b>', chat_id=chat_id)
        try:
            topics = generate_topics()
            if topics:
                send_topic_choices(topics)
        except Exception as e:
            send_message(f'❌ 주제 생성 실패: {e}', chat_id=chat_id)

    # Custom topic input mode
    elif action == 'custom':
        try:
            answer_callback(callback_id, 'Enter your topic')
            redis_client.set(CUSTOM_TOPIC_STATE_KEY.format(chat_id=chat_id), '1', ex=300)  # 5min timeout
            send_message(
                '✏️ <b>직접 주제를 입력해주세요.</b>\n\n'
                '이 메시지에 <b>답장</b>으로 주제를 입력해주세요.\n'
                '주제와 간단한 설명을 함께 적어주면 더 좋은 대본이 만들어집니다.\n\n'
                '예시:\n'
                '<i>한국의 PC방 문화: 1997년 외환위기 이후 PC방이 급증한 배경과 '
                '한국이 세계 최초 e스포츠 강국이 된 과정</i>',
                chat_id=chat_id,
                reply_markup={'force_reply': True, 'selective': True}
            )
        except Exception as e:
            print(f'[Webhook] Custom topic error: {e}', flush=True)

    else:
        answer_callback(callback_id, 'Unknown action')

    return jsonify({'ok': True})


def _handle_text_message(message):
    """Process text messages."""
    from ..services.distribution.telegram_service import send_message
    from ..extensions import db
    from ..models.topic import RecommendedTopic, SelectedTopic
    from datetime import date

    text = message.get('text', '').strip()
    chat_id = message['chat']['id']

    # Ignore bot commands
    if text.startswith('/'):
        if text == '/topics':
            send_message('📋 웹 UI에서 주제를 관리하세요:\nhttp://localhost:8000/topics/', chat_id=chat_id)
        elif text == '/status':
            send_message('📊 웹 UI에서 Pipeline 상태를 확인하세요:\nhttp://localhost:8000/pipeline/', chat_id=chat_id)
        else:
            send_message(
                'Available commands:\n/topics - Topic management\n/status - Pipeline status',
                chat_id=chat_id
            )
        return jsonify({'ok': True})

    # Check if we're waiting for custom topic input
    state_key = CUSTOM_TOPIC_STATE_KEY.format(chat_id=chat_id)
    if redis_client.get(state_key):
        redis_client.delete(state_key)

        # Parse: first line as title, rest as description
        lines = text.split('\n', 1)
        title = lines[0].strip()
        # If title contains ':', split into title and description
        if ':' in title and len(lines) == 1:
            parts = title.split(':', 1)
            title = parts[0].strip()
            description = parts[1].strip()
        else:
            description = lines[1].strip() if len(lines) > 1 else ''

        # Save as recommended + selected
        topic = RecommendedTopic(
            title=title,
            description=description,
            category='custom',
            source='manual',
            batch_date=date.today(),
            is_selected=True,
        )
        db.session.add(topic)
        db.session.flush()

        selected = SelectedTopic(
            recommended_topic_id=topic.id,
            title=title,
            video_type='short',
        )
        db.session.add(selected)
        db.session.commit()

        send_message(
            f'✅ <b>커스텀 주제 등록 완료</b>\n\n'
            f'<b>{title}</b>\n'
            + (f'{description}\n\n' if description else '\n')
            + f'웹 UI에서 Pipeline을 시작하세요:\n'
            f'http://localhost:8000/topics/',
            chat_id=chat_id
        )
        return jsonify({'ok': True})

    # Default: suggest using commands
    send_message(
        '💡 주제를 입력하려면 먼저 추천 메시지의 "✏️ 직접 입력" 버튼을 눌러주세요.\n\n'
        '/topics - 주제 관리\n'
        '/status - Pipeline 상태',
        chat_id=chat_id
    )
    return jsonify({'ok': True})
