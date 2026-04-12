import json
import re
from ...extensions import db, redis_client
from ...models.script import Script, ScriptParagraph
from ...models.topic import SelectedTopic
from ..ai.claude_client import generate


def get_prompt(name):
    """Get a prompt pair from Redis."""
    data = redis_client.hgetall(f'prompt:{name}')
    return data.get('system_prompt', ''), data.get('user_prompt', '')


def generate_script(selected_topic_id):
    """Generate a structured script for a selected topic via Claude API.

    The response is expected as JSON with paragraphs containing narration, scene, mood.
    """
    topic = SelectedTopic.query.get(selected_topic_id)
    if not topic:
        raise ValueError(f'Selected topic {selected_topic_id} not found')

    topic_context = topic.title
    if topic.recommended_topic and topic.recommended_topic.description:
        topic_context += '\n\n' + topic.recommended_topic.description

    prompt_name = 'script_short' if topic.video_type == 'short' else 'script_long'
    system_prompt, user_prompt = get_prompt(prompt_name)

    if not system_prompt and not user_prompt:
        raise ValueError(f'{prompt_name} prompt not configured')

    user_prompt = user_prompt.replace('{topic}', topic_context)

    response_text = generate(system_prompt, user_prompt)

    # Parse structured JSON response
    paragraphs_data = _parse_structured_response(response_text)

    # Build full narration text
    narration_texts = [p['narration'] for p in paragraphs_data]
    full_text = '\n\n'.join(narration_texts)
    word_count = len(full_text)
    estimated_duration = word_count // 3  # Korean: ~3 chars/sec

    script = Script(
        selected_topic_id=selected_topic_id,
        full_text=full_text,
        language='ko',
        word_count=word_count,
        estimated_duration=estimated_duration,
        prompt_used=prompt_name,
    )
    db.session.add(script)
    db.session.flush()

    for i, p in enumerate(paragraphs_data):
        para = ScriptParagraph(
            script_id=script.id,
            paragraph_index=i,
            text=p['narration'],
            scene_direction=p.get('scene', ''),
            mood=p.get('mood', ''),
        )
        db.session.add(para)

    topic.status = 'scripted'
    db.session.commit()
    return script


def _parse_structured_response(text):
    """Parse Claude's JSON response into paragraph dicts.

    Expected format: { "paragraphs": [ { "narration": "...", "scene": "...", "mood": "..." } ] }
    Falls back to plain text splitting if JSON parsing fails.
    """
    text = text.strip()
    # Remove markdown code block
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Find JSON
    match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and 'paragraphs' in data:
                return data['paragraphs']
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Fallback: plain text split
    paragraphs = []
    for block in text.split('\n\n'):
        block = block.strip()
        if block:
            paragraphs.append({'narration': block, 'scene': '', 'mood': ''})
    return paragraphs if paragraphs else [{'narration': text, 'scene': '', 'mood': ''}]


def translate_script(selected_topic_id):
    """Translate the Korean script to English via Claude API."""
    topic = SelectedTopic.query.get(selected_topic_id)
    if not topic:
        raise ValueError(f'Selected topic {selected_topic_id} not found')

    ko_script = Script.query.filter_by(
        selected_topic_id=selected_topic_id, language='ko'
    ).order_by(Script.created_at.desc()).first()

    if not ko_script:
        raise ValueError('No Korean script found. Generate script first.')

    ko_paragraphs = ko_script.paragraphs.order_by(ScriptParagraph.paragraph_index).all()

    system_prompt, user_prompt = get_prompt('script_translate')

    if not system_prompt:
        system_prompt = (
            '당신은 "LoreDrop" 유튜브 채널의 전문 번역가입니다.\n'
            'LoreDrop은 10-20대 영어권 시청자에게 한국 이야기를 전달하는 채널입니다.\n'
            '한국어 대본을 자연스럽고 몰입감 있는 영어로 번역하세요.\n'
            '장면 묘사와 분위기 키워드도 영어로 번역하세요.\n'
            '중요: JSON 구조로만 출력할 것.'
        )
    if not user_prompt:
        user_prompt = (
            '아래 한국어 유튜브 대본을 영어로 번역하세요.\n'
            '모든 필드를 번역: narration, scene, mood.\n\n'
            '규칙:\n'
            '- narration: TTS용 자연스러운 영어\n'
            '- scene: AI 이미지 생성용 비주얼 장면 묘사 (25-40단어).\n'
            '  포함 필수: 주체/초점, 구체적 동작이나 포즈, 배경/환경,\n'
            '  조명 방향 (예: 역광, 골든아워, 촛불), 카메라 앵글 (예: 와이드샷, 클로즈업, 버드아이뷰).\n'
            '  추상적 개념 금지 — 카메라가 보는 것만 묘사.\n'
            '  나쁜 예: "A tense moment of confrontation between two rivals"\n'
            '  좋은 예: "Close-up of a samurai gripping a katana hilt, rain-soaked courtyard, torchlight casting long shadows, low angle shot"\n'
            '- mood: 영어 키워드 (예: tense, mysterious, triumphant)\n'
            '- JSON만 출력, 설명 없이\n\n'
            '한국어 대본:\n{script}\n\n'
            'JSON 출력 (코드블록 없이):\n'
            '{{\n'
            '  "paragraphs": [\n'
            '    {{\n'
            '      "narration": "번역된 영어 나레이션",\n'
            '      "scene": "주체, 동작, 배경, 조명, 카메라 앵글이 포함된 비주얼 장면 묘사",\n'
            '      "mood": "영어 분위기 키워드"\n'
            '    }}\n'
            '  ]\n'
            '}}'
        )

    # Build structured input with scene/mood for translation
    script_parts = []
    for p in ko_paragraphs:
        part = f'나레이션: {p.text}'
        if p.scene_direction:
            part += f'\n장면: {p.scene_direction}'
        if p.mood:
            part += f'\n분위기: {p.mood}'
        script_parts.append(part)
    script_input = '\n\n---\n\n'.join(script_parts)
    user_prompt = user_prompt.replace('{script}', script_input)

    response_text = generate(system_prompt, user_prompt)

    # Parse structured response
    en_data = _parse_structured_response(response_text)

    # Build full text from narration
    narrations = [p.get('narration', p.get('text', '')) for p in en_data]
    full_text = '\n\n'.join(narrations)
    en_words = len(full_text.split())
    estimated_duration = int(en_words / 2.5)

    en_script = Script(
        selected_topic_id=selected_topic_id,
        full_text=full_text,
        language='en',
        word_count=len(full_text),
        estimated_duration=estimated_duration,
        prompt_used='script_translate',
    )
    db.session.add(en_script)
    db.session.flush()

    for i, p in enumerate(en_data):
        # Use translated scene/mood, fallback to Korean version
        scene = p.get('scene', '')
        mood = p.get('mood', '')
        if i < len(ko_paragraphs):
            if not scene:
                scene = ko_paragraphs[i].scene_direction or ''
            if not mood:
                mood = ko_paragraphs[i].mood or ''

        para = ScriptParagraph(
            script_id=en_script.id,
            paragraph_index=i,
            text=p.get('narration', p.get('text', '')),
            scene_direction=scene,
            mood=mood,
        )
        db.session.add(para)

    topic.status = 'translated'
    db.session.commit()
    return en_script


def _split_plain(text):
    paragraphs = []
    for block in text.split('\n\n'):
        block = block.strip()
        if block:
            paragraphs.append(block)
    return paragraphs if paragraphs else [text.strip()]
