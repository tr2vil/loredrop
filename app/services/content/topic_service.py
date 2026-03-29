import json
from datetime import date
from ...extensions import db, redis_client
from ...models.topic import RecommendedTopic, SelectedTopic
from ..ai.claude_client import generate


def get_prompt(name):
    """Get a prompt pair from Redis."""
    data = redis_client.hgetall(f'prompt:{name}')
    return data.get('system_prompt', ''), data.get('user_prompt', '')


def get_existing_topics_text():
    """Build a text list of previously selected topics for dedup."""
    selected = SelectedTopic.query.order_by(SelectedTopic.selected_at.desc()).all()
    if not selected:
        return '(none yet)'
    lines = []
    for t in selected:
        lines.append(f'- {t.title}')
    return '\n'.join(lines)


def generate_topics(count=None):
    """Generate topic recommendations via Claude API.

    Returns list of RecommendedTopic objects saved to DB.
    """
    if count is None:
        count = int(redis_client.hget('settings:general', 'daily_topic_count') or '3')

    system_prompt, user_prompt = get_prompt('topic_generation')
    if not system_prompt and not user_prompt:
        raise ValueError('topic_generation prompt not configured')

    existing_topics = get_existing_topics_text()
    user_prompt = user_prompt.replace('{count}', str(count))
    user_prompt = user_prompt.replace('{existing_topics}', existing_topics)

    response_text = generate(system_prompt, user_prompt)

    # Parse JSON response
    topics_data = _parse_topics_json(response_text)

    # Save to DB
    today = date.today()
    saved = []
    for t in topics_data:
        topic = RecommendedTopic(
            title=t.get('title_kr') or t.get('title_en', 'Untitled'),
            description=_build_description(t),
            category=_detect_category(t),
            source='claude',
            batch_date=today,
        )
        db.session.add(topic)
        saved.append(topic)

    db.session.commit()
    return saved


def _parse_topics_json(text):
    """Extract topics array from Claude's JSON response."""
    import re
    text = text.strip()

    # Remove markdown code block if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Find JSON object/array in the response
    # Look for the first { or [ and match to the last } or ]
    match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if match:
        text = match.group(1)

    data = json.loads(text)
    if isinstance(data, dict) and 'topics' in data:
        return data['topics']
    if isinstance(data, list):
        return data
    return [data]


def _build_description(t):
    """Build description text from topic JSON fields."""
    parts = []
    if t.get('title_en'):
        parts.append(f"EN: {t['title_en']}")
    if t.get('summary_kr'):
        parts.append(t['summary_kr'])
    if t.get('why_surprising'):
        parts.append(f"Why: {t['why_surprising']}")
    if t.get('story_points'):
        parts.append(f"Points: {t['story_points']}")
    if t.get('keywords'):
        parts.append(f"Keywords: {t['keywords']}")
    return '\n'.join(parts) if parts else ''


def _detect_category(t):
    """Detect category from topic data."""
    keywords = (t.get('keywords', '') + ' ' + t.get('title_en', '')).lower()
    if any(w in keywords for w in ['war', 'dynasty', 'kingdom', 'joseon', 'goryeo', 'ancient']):
        return 'history'
    if any(w in keywords for w in ['mystery', 'unsolved', 'disappear', 'ghost']):
        return 'mystery'
    if any(w in keywords for w in ['k-pop', 'k-drama', 'culture', 'food', 'gaming']):
        return 'culture'
    return 'history'


def select_topic(topic_id, video_type='short'):
    """Mark a recommended topic as selected.

    Also marks other topics from the same batch as not selected (rejected).
    """
    topic = RecommendedTopic.query.get(topic_id)
    if not topic:
        raise ValueError(f'Topic {topic_id} not found')
    if topic.is_selected:
        raise ValueError('Topic already selected')

    topic.is_selected = True

    selected = SelectedTopic(
        recommended_topic_id=topic.id,
        title=topic.title,
        video_type=video_type,
    )
    db.session.add(selected)
    db.session.commit()
    return selected
