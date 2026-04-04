import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from flask import current_app
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

    # Sub-agent validation
    topics_data = validate_topics(topics_data)

    # Sort by total score (highest first)
    topics_data.sort(key=lambda t: t.get('score_total') or 0, reverse=True)

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
            score_history=t.get('score_history'),
            score_channel_fit=t.get('score_channel_fit'),
            score_audience=t.get('score_audience'),
            score_total=t.get('score_total'),
            validation_details=json.dumps(
                t.get('validation_details', {}), ensure_ascii=False
            ) if t.get('validation_details') else None,
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


# ---------------------------------------------------------------------------
# Sub-agent validation
# ---------------------------------------------------------------------------

_AGENT_CONFIGS = [
    ('history_verification', 'agent_history_verification', 'score_history'),
    ('channel_fit', 'agent_channel_fit', 'score_channel_fit'),
    ('audience_appeal', 'agent_audience_appeal', 'score_audience'),
]

_WEIGHTS = {'score_history': 0.4, 'score_channel_fit': 0.3, 'score_audience': 0.3}


def validate_topics(topics_data):
    """Run 3 sub-agents in parallel to evaluate topics. Returns topics_data with scores."""
    topics_json = json.dumps(topics_data, ensure_ascii=False, indent=2)
    app = current_app._get_current_object()

    def _run_agent(agent_name, prompt_name):
        with app.app_context():
            system_prompt, user_prompt = get_prompt(prompt_name)
            if not system_prompt:
                return agent_name, None
            user_prompt = user_prompt.replace('{topics_json}', topics_json)
            try:
                response = generate(system_prompt, user_prompt)
                return agent_name, _parse_agent_response(response)
            except Exception as e:
                print(f'[Agent:{agent_name}] Error: {e}')
                return agent_name, None

    # Parallel execution
    agent_results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_run_agent, name, prompt_name): score_key
            for name, prompt_name, score_key in _AGENT_CONFIGS
        }
        for future in as_completed(futures):
            name, result = future.result()
            agent_results[name] = result

    # Merge scores into topics_data
    return _aggregate_scores(topics_data, agent_results)


def _parse_agent_response(text):
    """Parse a sub-agent's JSON evaluation response."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if match:
        text = match.group(1)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict) and 'evaluations' in data:
        return data['evaluations']
    if isinstance(data, list):
        return data
    return None


def _aggregate_scores(topics_data, agent_results):
    """Merge agent evaluation scores into topics_data."""
    # Build lookup: topic number -> evaluations per agent
    for topic in topics_data:
        num = topic.get('number', 0)
        details = {}

        for agent_name, prompt_name, score_key in _AGENT_CONFIGS:
            evals = agent_results.get(agent_name)
            if not evals:
                continue
            # Find matching evaluation by number
            ev = next((e for e in evals if e.get('number') == num), None)
            if not ev:
                # Fallback: match by index
                idx = topics_data.index(topic)
                ev = evals[idx] if idx < len(evals) else None
            if ev:
                score = ev.get('score', 0)
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    score = 0
                score = max(0, min(10, score))
                topic[score_key] = score
                details[agent_name] = {
                    'score': score,
                    'reasoning': ev.get('reasoning', ''),
                    'issues': ev.get('issues', []),
                    'strengths': ev.get('strengths', []),
                }

        topic['validation_details'] = details

        # Calculate weighted total
        available = []
        for score_key, weight in _WEIGHTS.items():
            val = topic.get(score_key)
            if val is not None:
                available.append((val, weight))

        if available:
            total_weight = sum(w for _, w in available)
            topic['score_total'] = round(
                sum(v * w for v, w in available) / total_weight, 1
            )

    return topics_data


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
