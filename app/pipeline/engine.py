import threading
from datetime import datetime
from ..extensions import db, redis_client
from ..models.pipeline_run import PipelineRun, PipelineStep

PIPELINE_STEPS = [
    'topic_confirmed',
    'script_generated',
    'tts_completed',
    'images_generated',
    'video_assembled',
    'uploaded',
]

STEP_LABELS = {
    'topic_confirmed': 'Topic Confirmed',
    'script_generated': 'Script Generated',
    'tts_completed': 'TTS Completed',
    'images_generated': 'Images Generated',
    'video_assembled': 'Video Assembled',
    'uploaded': 'Uploaded',
}


def _log(run_id, message):
    """Append a log message for a pipeline run."""
    timestamp = datetime.utcnow().strftime('%H:%M:%S')
    redis_client.rpush(f'pipeline:run:{run_id}:log', f'[{timestamp}] {message}')


def _update_step(run_id, step_name, status, error=None, result=None):
    """Update a step's status in both DB and Redis."""
    from flask import current_app
    with current_app.app_context():
        step = PipelineStep.query.filter_by(run_id=run_id, step_name=step_name).first()
        if step:
            step.status = status
            if status == 'running':
                step.started_at = datetime.utcnow()
            elif status in ('completed', 'failed'):
                step.completed_at = datetime.utcnow()
            if error:
                step.error_message = error
            if result:
                step.result_data = result
            db.session.commit()
        redis_client.hset(f'pipeline:run:{run_id}:progress', step_name, status)


def execute_step(app, run_id, step_name):
    """Execute a pipeline step in a background thread."""

    def _run():
        with app.app_context():
            run = PipelineRun.query.get(run_id)
            if not run:
                return

            _update_step(run_id, step_name, 'running')
            _log(run_id, f'Starting: {STEP_LABELS.get(step_name, step_name)}')

            run.status = 'running'
            run.current_step = step_name
            if not run.started_at:
                run.started_at = datetime.utcnow()
            db.session.commit()

            try:
                result = _execute_step_logic(run, step_name)
                _update_step(run_id, step_name, 'completed', result=result)
                _log(run_id, f'Completed: {STEP_LABELS.get(step_name, step_name)}')

                # Check if all steps are done
                all_done = all(
                    s.status == 'completed'
                    for s in PipelineStep.query.filter_by(run_id=run_id).all()
                )
                if all_done:
                    run.status = 'completed'
                    run.completed_at = datetime.utcnow()
                    db.session.commit()
                    _log(run_id, 'Pipeline completed!')

                # Auto-mode: trigger next step
                elif run.auto_mode:
                    next_step = _get_next_step(run_id, step_name)
                    if next_step:
                        _log(run_id, f'Auto-mode: triggering {STEP_LABELS.get(next_step, next_step)}')
                        execute_step(app, run_id, next_step)

            except Exception as e:
                _update_step(run_id, step_name, 'failed', error=str(e))
                _log(run_id, f'Failed: {STEP_LABELS.get(step_name, step_name)} - {e}')
                run.status = 'failed'
                db.session.commit()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def _execute_step_logic(run, step_name):
    """Execute the actual business logic for a step. Returns result dict."""
    if step_name == 'topic_confirmed':
        return {'message': f'Topic confirmed: {run.selected_topic.title}'}

    elif step_name == 'script_generated':
        from ..services.content.script_service import generate_script
        script = generate_script(run.selected_topic_id)
        return {
            'script_id': script.id,
            'word_count': script.word_count,
            'paragraphs': script.paragraphs.count(),
            'estimated_duration': script.estimated_duration,
        }

    elif step_name == 'tts_completed':
        # TODO: ElevenLabs TTS integration
        _log(run.id, 'TTS: Not yet implemented (stub)')
        return {'message': 'TTS stub - not yet implemented'}

    elif step_name == 'images_generated':
        # TODO: Midjourney/image generation
        _log(run.id, 'Images: Not yet implemented (stub)')
        return {'message': 'Image generation stub - not yet implemented'}

    elif step_name == 'video_assembled':
        # TODO: FFmpeg video assembly
        _log(run.id, 'Video: Not yet implemented (stub)')
        return {'message': 'Video assembly stub - not yet implemented'}

    elif step_name == 'uploaded':
        # TODO: YouTube upload
        _log(run.id, 'Upload: Not yet implemented (stub)')
        return {'message': 'Upload stub - not yet implemented'}

    return {}


def _get_next_step(run_id, current_step):
    """Get the next pending step after the current one."""
    try:
        idx = PIPELINE_STEPS.index(current_step)
    except ValueError:
        return None
    for next_name in PIPELINE_STEPS[idx + 1:]:
        step = PipelineStep.query.filter_by(run_id=run_id, step_name=next_name).first()
        if step and step.status == 'pending':
            return next_name
    return None
