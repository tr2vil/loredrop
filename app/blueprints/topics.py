from datetime import date
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
    # TODO: Call AI service to generate topics
    # For now, return placeholder
    return jsonify({'ok': True, 'message': 'Topic generation not yet implemented'}), 200


@topics_bp.route('/<int:topic_id>/select', methods=['POST'])
def select_topic(topic_id):
    topic = RecommendedTopic.query.get_or_404(topic_id)
    if topic.is_selected:
        return jsonify({'error': 'Topic already selected'}), 400

    data = request.get_json() or {}
    video_type = data.get('video_type', 'short')

    topic.is_selected = True

    selected = SelectedTopic(
        recommended_topic_id=topic.id,
        title=topic.title,
        video_type=video_type,
    )
    db.session.add(selected)
    db.session.commit()

    return jsonify({'ok': True, 'selected_topic': selected.to_dict()})
