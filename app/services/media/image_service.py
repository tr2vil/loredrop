from flask import current_app
from ...extensions import db, redis_client
from ...models.script import Script, ScriptParagraph
from ...models.scene_image import SceneImage
from ..system.settings_service import get_settings
from . import leonardo_client


def _build_prompt(scene_direction, leo_settings):
    """Combine scene direction with style suffix."""
    prompt = scene_direction.strip()
    suffix = leo_settings.get('style_prompt_suffix', '').strip()
    if suffix:
        prompt = f'{prompt}, {suffix}'
    return prompt


def generate_images(selected_topic_id, run_id, log_fn=None):
    """Generate images for all paragraphs of the English script."""

    # 1. Find the English script
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

    # 2. Load Leonardo settings
    leo_settings = get_settings('leonardo')
    num_images = int(leo_settings.get('num_images', '4'))
    width = int(leo_settings.get('width', '1024'))
    height = int(leo_settings.get('height', '576'))
    model_id = leo_settings.get('model_id', '') or None
    preset_style = leo_settings.get('preset_style', '') or None
    negative_prompt = leo_settings.get('negative_prompt', '') or None

    if log_fn:
        log_fn(f'Images: Starting generation for {len(paragraphs)} scenes')

    # 3. Initialize progress tracking
    progress_key = f'pipeline:run:{run_id}:images_progress'
    redis_client.hset(progress_key, mapping={
        'current': '0',
        'total': str(len(paragraphs)),
        'current_label': '',
    })
    redis_client.expire(progress_key, 3600)

    # 4. Process each paragraph
    scenes_processed = 0

    for i, para in enumerate(paragraphs):
        redis_client.hset(progress_key, mapping={
            'current': str(i),
            'total': str(len(paragraphs)),
            'current_label': f'P{para.paragraph_index}',
        })

        scene_text = para.scene_direction or ''
        if not scene_text.strip():
            if log_fn:
                log_fn(f'Images: P{para.paragraph_index} has no scene direction, skipping.')
            continue

        prompt = _build_prompt(scene_text, leo_settings)

        if log_fn:
            log_fn(f'Images: Generating P{para.paragraph_index} ({i + 1}/{len(paragraphs)})...')

        # Start generation
        generation_id = leonardo_client.generate_images(
            prompt=prompt,
            num_images=num_images,
            width=width,
            height=height,
            model_id=model_id,
            preset_style=preset_style,
            negative_prompt=negative_prompt,
        )

        if log_fn:
            log_fn(f'Images: P{para.paragraph_index} submitted (ID: {generation_id}), polling...')

        # Wait for completion
        image_urls = leonardo_client.wait_for_generation(generation_id)

        # Save to scene_images table
        existing = SceneImage.query.filter_by(
            script_id=en_script.id, scene_index=para.paragraph_index
        ).first()

        if existing:
            existing.prompt = prompt
            existing.generation_id = generation_id
            existing.image_urls = image_urls
            existing.selected_url = None
        else:
            scene_img = SceneImage(
                script_id=en_script.id,
                scene_index=para.paragraph_index,
                prompt=prompt,
                generation_id=generation_id,
                image_urls=image_urls,
            )
            db.session.add(scene_img)

        db.session.commit()
        scenes_processed += 1

        if log_fn:
            log_fn(f'Images: P{para.paragraph_index} done ({len(image_urls)} images)')

    # Mark progress complete
    redis_client.hset(progress_key, mapping={
        'current': str(len(paragraphs)),
        'total': str(len(paragraphs)),
        'current_label': 'done',
    })

    if log_fn:
        log_fn(f'Images: All done - {scenes_processed} scenes processed')

    return {
        'script_id': en_script.id,
        'scenes_processed': scenes_processed,
        'total_paragraphs': len(paragraphs),
    }


def generate_single_scene(paragraph_id, run_id):
    """Generate images for a single paragraph. Returns SceneImage dict."""
    para = ScriptParagraph.query.get(paragraph_id)
    if not para:
        raise ValueError('Paragraph not found.')

    scene_text = para.scene_direction or ''
    if not scene_text.strip():
        raise ValueError('Paragraph has no scene direction.')

    leo_settings = get_settings('leonardo')
    prompt = _build_prompt(scene_text, leo_settings)

    num_images = int(leo_settings.get('num_images', '4'))
    width = int(leo_settings.get('width', '1024'))
    height = int(leo_settings.get('height', '576'))
    model_id = leo_settings.get('model_id', '') or None
    preset_style = leo_settings.get('preset_style', '') or None
    negative_prompt = leo_settings.get('negative_prompt', '') or None

    generation_id = leonardo_client.generate_images(
        prompt=prompt,
        num_images=num_images,
        width=width,
        height=height,
        model_id=model_id,
        preset_style=preset_style,
        negative_prompt=negative_prompt,
    )

    image_urls = leonardo_client.wait_for_generation(generation_id)

    # Upsert scene_image
    existing = SceneImage.query.filter_by(
        script_id=para.script_id, scene_index=para.paragraph_index
    ).first()

    if existing:
        existing.prompt = prompt
        existing.generation_id = generation_id
        existing.image_urls = image_urls
        existing.selected_url = None
        scene_img = existing
    else:
        scene_img = SceneImage(
            script_id=para.script_id,
            scene_index=para.paragraph_index,
            prompt=prompt,
            generation_id=generation_id,
            image_urls=image_urls,
        )
        db.session.add(scene_img)

    db.session.commit()
    return scene_img.to_dict()


def select_image(scene_image_id, selected_url):
    """Select an image for a scene. Updates SceneImage and ScriptParagraph."""
    scene_img = SceneImage.query.get(scene_image_id)
    if not scene_img:
        raise ValueError('Scene image not found.')

    if selected_url not in (scene_img.image_urls or []):
        raise ValueError('Selected URL is not in the generated images.')

    scene_img.selected_url = selected_url

    # Also update the paragraph's image_path
    para = ScriptParagraph.query.filter_by(
        script_id=scene_img.script_id,
        paragraph_index=scene_img.scene_index,
    ).first()
    if para:
        para.image_path = selected_url
        para.image_prompt = scene_img.prompt

    db.session.commit()
    return scene_img.to_dict()


def get_scene_images(run_id):
    """Get all scene images for a pipeline run."""
    from ...models.pipeline_run import PipelineRun
    run = PipelineRun.query.get(run_id)
    if not run:
        return []

    en_script = Script.query.filter_by(
        selected_topic_id=run.selected_topic_id, language='en'
    ).order_by(Script.created_at.desc()).first()

    if not en_script:
        return []

    images = SceneImage.query.filter_by(
        script_id=en_script.id
    ).order_by(SceneImage.scene_index).all()

    return [img.to_dict() for img in images]
