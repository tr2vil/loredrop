from flask import Blueprint, render_template, jsonify, request
from ..extensions import db
from ..models.topic import RecommendedTopic, SelectedTopic

topics_bp = Blueprint('topics', __name__)


@topics_bp.route('/')
def index():
    return render_template('topics/index.html')


@topics_bp.route('/api/list', methods=['GET'])
def list_topics():
    query = RecommendedTopic.query.order_by(RecommendedTopic.created_at.desc())

    filter_date = request.args.get('date')
    if filter_date:
        query = query.filter(RecommendedTopic.batch_date == filter_date)

    filter_status = request.args.get('status')
    if filter_status == 'selected':
        query = query.filter(RecommendedTopic.is_selected == True)
    elif filter_status == 'recommended':
        query = query.filter(RecommendedTopic.is_selected == False)

    topics = query.limit(100).all()
    return jsonify({'topics': [t.to_dict() for t in topics]})


@topics_bp.route('/generate', methods=['POST'])
def generate_topics():
    """Generate topic recommendations via Claude API."""
    from ..services.content.topic_service import generate_topics as gen_topics
    from ..services.distribution.telegram_service import send_topic_choices
    from ..extensions import redis_client

    try:
        topics = gen_topics()

        # Send to Telegram if enabled
        telegram_enabled = redis_client.hget('settings:general', 'telegram_enabled')
        if telegram_enabled != 'false' and len(topics) > 0:
            try:
                send_topic_choices(topics)
            except Exception as e:
                # Don't fail the whole request if Telegram fails
                print(f'Telegram send failed: {e}')

        return jsonify({
            'ok': True,
            'topics': [t.to_dict() for t in topics],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@topics_bp.route('/<int:topic_id>/select', methods=['POST'])
def select_topic(topic_id):
    """Mark a recommended topic as selected."""
    from ..services.content.topic_service import select_topic as do_select
    from ..services.distribution.telegram_service import send_message

    data = request.get_json(silent=True) or {}
    video_type = data.get('video_type', 'short')

    try:
        selected = do_select(topic_id, video_type)

        # Notify via Telegram
        try:
            send_message(
                f'<b>Topic Selected</b>\n\n'
                f'{selected.title}\n'
                f'Type: {selected.video_type}'
            )
        except Exception:
            pass

        return jsonify({'ok': True, 'selected_topic': selected.to_dict()})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
