import asyncio
import edge_tts


def text_to_speech(text, voice='en-US-GuyNeural', rate='+0%', pitch='+0Hz'):
    """Convert text to speech using Edge TTS (free, no API key).

    Returns audio data as bytes (MP3 format).
    """
    return asyncio.run(_generate(text, voice, rate, pitch))


async def _generate(text, voice, rate, pitch):
    """Async edge-tts generation."""
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    chunks = []
    async for chunk in communicate.stream():
        if chunk['type'] == 'audio':
            chunks.append(chunk['data'])
    if not chunks:
        raise ValueError(f'Edge TTS returned no audio. Check voice "{voice}" is valid.')
    return b''.join(chunks)


async def list_voices(language='en'):
    """List available voices for a language prefix."""
    voices = await edge_tts.list_voices()
    return [v for v in voices if v['Locale'].startswith(language)]
