import time
import requests
from flask import current_app

BASE_URL = 'https://cloud.leonardo.ai/api/rest/v1'


def _headers():
    api_key = current_app.config.get('LEONARDO_API_KEY', '')
    if not api_key:
        raise ValueError('LEONARDO_API_KEY is not configured. Set it in .env.')
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def generate_images(prompt, num_images=4, width=1024, height=576,
                    model_id=None, preset_style=None, negative_prompt=None,
                    alchemy=True, guidance_scale=7):
    """Start an image generation job. Returns generation_id."""
    payload = {
        'prompt': prompt,
        'num_images': num_images,
        'width': width,
        'height': height,
        'alchemy': alchemy,
        'guidance_scale': guidance_scale,
    }
    if model_id:
        payload['modelId'] = model_id
    if preset_style:
        payload['presetStyle'] = preset_style
    if negative_prompt:
        payload['negative_prompt'] = negative_prompt

    resp = requests.post(f'{BASE_URL}/generations', headers=_headers(), json=payload, timeout=30)

    if resp.status_code == 402:
        raise ValueError('Leonardo API quota exceeded. Check your plan.')
    if resp.status_code == 401:
        raise ValueError('Leonardo API key is invalid.')

    resp.raise_for_status()
    data = resp.json()
    return data['sdGenerationJob']['generationId']


def get_generation(generation_id):
    """Get the status and results of a generation job.

    Returns dict with 'status' ('PENDING', 'COMPLETE', 'FAILED')
    and 'images' (list of image URLs when complete).
    """
    resp = requests.get(f'{BASE_URL}/generations/{generation_id}',
                        headers=_headers(), timeout=15)
    resp.raise_for_status()
    data = resp.json()['generations_by_pk']

    result = {
        'status': data.get('status', 'PENDING'),
        'images': [],
    }

    if data.get('status') == 'COMPLETE' and data.get('generated_images'):
        result['images'] = [img['url'] for img in data['generated_images']]

    return result


def wait_for_generation(generation_id, poll_interval=5, max_wait=120):
    """Poll until generation is complete. Returns list of image URLs."""
    elapsed = 0
    while elapsed < max_wait:
        result = get_generation(generation_id)
        if result['status'] == 'COMPLETE':
            return result['images']
        if result['status'] == 'FAILED':
            raise ValueError(f'Leonardo generation failed (ID: {generation_id})')
        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(f'Leonardo generation timed out after {max_wait}s (ID: {generation_id})')
