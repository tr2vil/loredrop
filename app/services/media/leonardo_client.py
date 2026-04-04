import json
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


def upload_init_image(image_bytes, extension='jpg'):
    """Upload an image to Leonardo via presigned URL. Returns init_image_id."""
    # Step 1: Get presigned URL
    resp = requests.post(
        f'{BASE_URL}/init-image',
        headers=_headers(),
        json={'extension': extension},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()['uploadInitImage']
    init_image_id = data['id']
    presigned_url = data['url']
    fields = json.loads(data['fields'])

    # Step 2: Upload to S3 via presigned URL
    upload_resp = requests.post(
        presigned_url,
        data=fields,
        files={'file': ('image.' + extension, image_bytes)},
        timeout=60,
    )
    upload_resp.raise_for_status()

    return init_image_id


def download_image_from_url(url):
    """Download an image from a URL. Returns (bytes, extension)."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    content_type = resp.headers.get('Content-Type', '')
    if 'png' in content_type or url.lower().endswith('.png'):
        ext = 'png'
    elif 'webp' in content_type or url.lower().endswith('.webp'):
        ext = 'webp'
    else:
        ext = 'jpg'
    return resp.content, ext


def generate_images(prompt, num_images=4, width=1024, height=576,
                    model_id=None, preset_style=None, negative_prompt=None,
                    alchemy=True, guidance_scale=7,
                    init_image_id=None, init_strength=None):
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
    if init_image_id:
        payload['init_image_id'] = init_image_id
        if init_strength is not None:
            payload['init_strength'] = float(init_strength)

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
    and 'images' (list of {id, url} dicts when complete).
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
        result['images'] = [
            {'id': img['id'], 'url': img['url']}
            for img in data['generated_images']
        ]

    return result


def wait_for_generation(generation_id, poll_interval=5, max_wait=120):
    """Poll until generation is complete. Returns list of {id, url} dicts."""
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


def generate_variation(generated_image_id, prompt, init_strength=0.25,
                       num_images=4, width=576, height=1024,
                       model_id=None, preset_style=None, negative_prompt=None,
                       alchemy=True):
    """Generate variations of a previously generated Leonardo image.

    Uses init_generation_image_id to reference the source image.
    init_strength: 0.15-0.35 = subtle, 0.55-0.80 = strong.
    """
    payload = {
        'prompt': prompt,
        'num_images': num_images,
        'width': width,
        'height': height,
        'alchemy': alchemy,
        'init_generation_image_id': generated_image_id,
        'init_strength': float(init_strength),
    }
    if model_id:
        payload['modelId'] = model_id
    if preset_style:
        payload['presetStyle'] = preset_style
    if negative_prompt:
        payload['negative_prompt'] = negative_prompt

    resp = requests.post(f'{BASE_URL}/generations', headers=_headers(), json=payload, timeout=30)
    if resp.status_code == 402:
        raise ValueError('Leonardo API quota exceeded.')
    resp.raise_for_status()
    return resp.json()['sdGenerationJob']['generationId']
