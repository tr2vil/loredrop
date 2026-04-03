import os
from mutagen.mp3 import MP3
from flask import current_app
from ...extensions import db, redis_client
from ...models.script import Script, ScriptParagraph
from ..system.settings_service import get_settings
from .elevenlabs_client import text_to_speech


def generate_tts(selected_topic_id, run_id, log_fn=None):
    """Generate TTS audio for all paragraphs of the English script."""

    # 1. Find the English script (most recent)
    en_script = Script.query.filter_by(
        selected_topic_id=selected_topic_id, language='en'
    ).order_by(Script.created_at.desc()).first()

    if not en_script:
        raise ValueError('No English script found. Run "Translate Script" first.')

    paragraphs = en_script.paragraphs.order_by(
        ScriptParagraph.paragraph_index
    ).all()

    if not paragraphs:
        raise ValueError('English script has no paragraphs.')

    # 2. Load TTS settings from Redis
    tts_settings = get_settings('tts')
    voice_id = (tts_settings.get('en_voice_id')
                or current_app.config['ELEVENLABS_EN_VOICE_ID'])
    model_id = tts_settings.get('model_id', 'eleven_multilingual_v2')
    stability = tts_settings.get('stability', '0.5')
    similarity = tts_settings.get('similarity', '0.75')
    style = tts_settings.get('style', '0.0')
    speed = tts_settings.get('speed', '1.0')

    if not voice_id:
        raise ValueError('No English voice ID configured. Set ELEVENLABS_EN_VOICE_ID in .env or Settings > TTS.')

    # 3. Prepare output directory: output/audio/run_{run_id}/
    audio_dir = os.path.join(
        current_app.config['OUTPUT_DIR'], 'audio', f'run_{run_id}'
    )
    os.makedirs(audio_dir, exist_ok=True)

    if log_fn:
        log_fn(f'TTS: Starting generation for {len(paragraphs)} paragraphs (model: {model_id})')

    # 4. Initialize progress tracking in Redis
    progress_key = f'pipeline:run:{run_id}:tts_progress'
    redis_client.hset(progress_key, mapping={
        'current': '0',
        'total': str(len(paragraphs)),
        'current_label': '',
    })
    redis_client.expire(progress_key, 3600)

    # 5. Process each paragraph
    total_duration = 0.0
    total_chars = 0

    for i, para in enumerate(paragraphs):
        redis_client.hset(progress_key, mapping={
            'current': str(i),
            'total': str(len(paragraphs)),
            'current_label': f'P{para.paragraph_index}',
        })

        if log_fn:
            log_fn(f'TTS: Generating P{para.paragraph_index} ({i + 1}/{len(paragraphs)})...')

        if not para.text or not para.text.strip():
            if log_fn:
                log_fn(f'TTS: Paragraph {i + 1} is empty, skipping.')
            continue

        # Call ElevenLabs
        audio_bytes = text_to_speech(
            text=para.text,
            voice_id=voice_id,
            model_id=model_id,
            stability=stability,
            similarity=similarity,
            style=style,
            speed=speed,
        )

        # Save MP3 file: P1.mp3, P2.mp3, ...
        filename = f'P{para.paragraph_index}.mp3'
        filepath = os.path.join(audio_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)

        # Get duration
        duration = _get_mp3_duration(filepath)

        # Update database
        para.audio_path = f'audio/run_{run_id}/{filename}'
        para.audio_duration = duration
        db.session.commit()

        total_duration += duration
        total_chars += len(para.text)

        if log_fn:
            log_fn(f'TTS: P{para.paragraph_index} done ({duration:.1f}s, {len(para.text)} chars)')

    # Mark progress complete
    redis_client.hset(progress_key, mapping={
        'current': str(len(paragraphs)),
        'total': str(len(paragraphs)),
        'current_label': 'done',
    })

    if log_fn:
        log_fn(f'TTS: All done — {len(paragraphs)} files, {total_duration:.1f}s total, {total_chars} chars used')

    return {
        'script_id': en_script.id,
        'paragraphs_processed': len(paragraphs),
        'total_duration': round(total_duration, 1),
        'total_characters': total_chars,
        'audio_dir': f'audio/run_{run_id}',
    }


def _get_mp3_duration(filepath):
    """Get duration of an MP3 file in seconds."""
    try:
        audio = MP3(filepath)
        return audio.info.length
    except Exception:
        # Fallback: estimate from file size (128kbps = 16KB/s)
        size = os.path.getsize(filepath)
        return size / 16000.0
