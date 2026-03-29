from datetime import datetime
from flask import Blueprint, render_template, jsonify, request
from ..extensions import db, redis_client
from ..models.topic import SelectedTopic
from ..models.pipeline_run import PipelineRun, PipelineStep

pipeline_bp = Blueprint('pipeline', __name__)

PIPELINE_STEPS = [
    'topic_confirmed',
    'script_generated',
    'tts_completed',
    'images_generated',
    'video_assembled',
    'uploaded',
]


@pipeline_bp.route('/')
def index():
    return render_template('pipeline/index.html')


@pipeline_bp.route('/<int:run_id>')
def detail(run_id):
    run = PipelineRun.query.get_or_404(run_id)
    run.selected_topic  # eager load
    return render_template('pipeline/detail.html', run=run)


@pipeline_bp.route('/start/<int:topic_id>', methods=['POST'])
def start_pipeline(topic_id):
    topic = SelectedTopic.query.get_or_404(topic_id)

    run = PipelineRun(
        selected_topic_id=topic.id,
        status='pending',
        current_step=PIPELINE_STEPS[0],
    )
    db.session.add(run)
    db.session.flush()

    for step_name in PIPELINE_STEPS:
        step = PipelineStep(run_id=run.id, step_name=step_name, status='pending')
        db.session.add(step)

    db.session.commit()

    # Initialize Redis status
    progress = {s: 'pending' for s in PIPELINE_STEPS}
    redis_client.hset(f'pipeline:run:{run.id}:progress', mapping=progress)

    return jsonify({'ok': True, 'run': run.to_dict()})


@pipeline_bp.route('/<int:run_id>/step/<step_name>/execute', methods=['POST'])
def execute_step(run_id, step_name):
    if step_name not in PIPELINE_STEPS:
        return jsonify({'error': 'Invalid step'}), 400

    run = PipelineRun.query.get_or_404(run_id)
    step = PipelineStep.query.filter_by(run_id=run_id, step_name=step_name).first_or_404()

    if step.status == 'running':
        return jsonify({'error': 'Step already running'}), 400

    # Update status
    step.status = 'running'
    step.started_at = datetime.utcnow()
    run.status = 'running'
    run.current_step = step_name
    if not run.started_at:
        run.started_at = datetime.utcnow()
    db.session.commit()

    # Update Redis
    redis_client.hset(f'pipeline:run:{run_id}:progress', step_name, 'running')
    redis_client.rpush(f'pipeline:run:{run_id}:log',
                       f'[{datetime.utcnow().strftime("%H:%M:%S")}] Starting step: {step_name}')

    # TODO: Execute actual step logic in background thread
    # For now, mark as completed immediately
    step.status = 'completed'
    step.completed_at = datetime.utcnow()
    db.session.commit()
    redis_client.hset(f'pipeline:run:{run_id}:progress', step_name, 'completed')
    redis_client.rpush(f'pipeline:run:{run_id}:log',
                       f'[{datetime.utcnow().strftime("%H:%M:%S")}] Completed step: {step_name}')

    # Check if all steps completed
    all_completed = all(
        s.status == 'completed'
        for s in PipelineStep.query.filter_by(run_id=run_id).all()
    )
    if all_completed:
        run.status = 'completed'
        run.completed_at = datetime.utcnow()
        db.session.commit()

    return jsonify({'ok': True})


@pipeline_bp.route('/<int:run_id>/auto', methods=['POST'])
def toggle_auto(run_id):
    run = PipelineRun.query.get_or_404(run_id)
    data = request.get_json() or {}
    run.auto_mode = data.get('auto_mode', not run.auto_mode)
    db.session.commit()
    return jsonify({'ok': True, 'auto_mode': run.auto_mode})


@pipeline_bp.route('/api/<int:run_id>/status', methods=['GET'])
def get_status(run_id):
    run = PipelineRun.query.get_or_404(run_id)
    steps = PipelineStep.query.filter_by(run_id=run_id).order_by(PipelineStep.id).all()
    logs = redis_client.lrange(f'pipeline:run:{run_id}:log', 0, -1)
    return jsonify({
        'status': run.status,
        'current_step': run.current_step,
        'auto_mode': run.auto_mode,
        'steps': [s.to_dict() for s in steps],
        'logs': logs,
    })
