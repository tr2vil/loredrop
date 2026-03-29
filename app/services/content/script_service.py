from ...extensions import db, redis_client
from ...models.script import Script, ScriptParagraph
from ...models.topic import SelectedTopic
from ..ai.claude_client import generate


def get_prompt(name):
    """Get a prompt pair from Redis."""
    data = redis_client.hgetall(f'prompt:{name}')
    return data.get('system_prompt', ''), data.get('user_prompt', '')


def generate_script(selected_topic_id):
    """Generate a script for a selected topic via Claude API.

    Returns the Script model instance with paragraphs.
    """
    topic = SelectedTopic.query.get(selected_topic_id)
    if not topic:
        raise ValueError(f'Selected topic {selected_topic_id} not found')

    # Build topic context from recommended topic's description
    topic_context = topic.title
    if topic.recommended_topic and topic.recommended_topic.description:
        topic_context += '\n\n' + topic.recommended_topic.description

    # Choose prompt based on video type
    prompt_name = 'script_short' if topic.video_type == 'short' else 'script_long'
    system_prompt, user_prompt = get_prompt(prompt_name)

    if not system_prompt and not user_prompt:
        raise ValueError(f'{prompt_name} prompt not configured')

    user_prompt = user_prompt.replace('{topic}', topic_context)

    # Call Claude API
    response_text = generate(system_prompt, user_prompt)

    # Split into paragraphs
    paragraphs = _split_paragraphs(response_text)

    # Calculate stats
    word_count = len(response_text)
    # Rough estimate: Korean ~3 chars/sec narration
    estimated_duration = word_count // 3

    # Save to DB
    script = Script(
        selected_topic_id=selected_topic_id,
        full_text=response_text,
        language='ko',
        word_count=word_count,
        estimated_duration=estimated_duration,
        prompt_used=f'{prompt_name} (system: {len(system_prompt)} chars, user: {len(user_prompt)} chars)',
    )
    db.session.add(script)
    db.session.flush()

    for i, para_text in enumerate(paragraphs):
        para = ScriptParagraph(
            script_id=script.id,
            paragraph_index=i,
            text=para_text,
        )
        db.session.add(para)

    # Update topic status
    topic.status = 'scripted'
    db.session.commit()

    return script


def _split_paragraphs(text):
    """Split script text into paragraphs by double newline."""
    paragraphs = []
    for block in text.split('\n\n'):
        block = block.strip()
        if block:
            paragraphs.append(block)
    return paragraphs if paragraphs else [text.strip()]
