from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app
from ..extensions import db, redis_client
from ..models.topic import SelectedTopic
from ..models.script import Script, ScriptParagraph
from ..models.pipeline_run import PipelineRun, PipelineStep
from ..pipeline.engine import PIPELINE_STEPS, execute_step

pipeline_bp = Blueprint('pipeline', __name__)


@pipeline_bp.route('/')
def index():
    runs = PipelineRun.query.order_by(PipelineRun.created_at.desc()).limit(50).all()
    return render_template('pipeline/index.html', runs=runs)


@pipeline_bp.route('/<int:run_id>')
def detail(run_id):
    run = PipelineRun.query.get_or_404(run_id)
    return render_template('pipeline/detail.html', run=run)


@pipeline_bp.route('/start/<int:topic_id>', methods=['GET', 'POST'])
def start_pipeline(topic_id):
    """Create a new pipeline run for a selected topic, or navigate to existing one."""
    # Check if selected topic exists via recommended_topic_id
    topic = SelectedTopic.query.filter_by(recommended_topic_id=topic_id).first()
    if not topic:
        topic = SelectedTopic.query.get(topic_id)
    if not topic:
        return jsonify({'error': 'Selected topic not found'}), 404

    # Check for existing active run
    existing = PipelineRun.query.filter_by(
        selected_topic_id=topic.id
    ).filter(
        PipelineRun.status.in_(['pending', 'running', 'paused'])
    ).first()

    if existing:
        return redirect(url_for('pipeline.detail', run_id=existing.id))

    # Create new run
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

    return redirect(url_for('pipeline.detail', run_id=run.id))


@pipeline_bp.route('/<int:run_id>/step/<step_name>/execute', methods=['POST'])
def execute_step_route(run_id, step_name):
    if step_name not in PIPELINE_STEPS:
        return jsonify({'error': 'Invalid step'}), 400

    run = PipelineRun.query.get_or_404(run_id)
    step = PipelineStep.query.filter_by(run_id=run_id, step_name=step_name).first_or_404()

    if step.status == 'running':
        return jsonify({'error': 'Step already running'}), 400

    execute_step(current_app._get_current_object(), run_id, step_name)
    return jsonify({'ok': True})


@pipeline_bp.route('/<int:run_id>/run-all', methods=['POST'])
def run_all(run_id):
    """Run all remaining steps sequentially (auto-mode)."""
    run = PipelineRun.query.get_or_404(run_id)
    run.auto_mode = True
    db.session.commit()

    # Find the first pending step and execute it (auto_mode will chain the rest)
    first_pending = PipelineStep.query.filter_by(
        run_id=run_id, status='pending'
    ).order_by(PipelineStep.id).first()

    if first_pending:
        execute_step(current_app._get_current_object(), run_id, first_pending.step_name)

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


# ─── Script API ───

@pipeline_bp.route('/api/<int:run_id>/script/<lang>', methods=['GET'])
def get_script(run_id, lang='ko'):
    """Get the generated script for a pipeline run by language (ko/en)."""
    run = PipelineRun.query.get_or_404(run_id)
    script = Script.query.filter_by(
        selected_topic_id=run.selected_topic_id, language=lang
    ).order_by(Script.created_at.desc()).first()
    if not script:
        return jsonify({'error': f'No {lang} script found'}), 404
    return jsonify(script.to_dict())


@pipeline_bp.route('/api/<int:run_id>/script/<lang>', methods=['PUT'])
def update_script(run_id, lang='ko'):
    """Update/edit the generated script."""
    run = PipelineRun.query.get_or_404(run_id)
    script = Script.query.filter_by(
        selected_topic_id=run.selected_topic_id, language=lang
    ).order_by(Script.created_at.desc()).first()
    if not script:
        return jsonify({'error': f'No {lang} script found'}), 404

    data = request.get_json()

    # Update paragraph-level data if provided
    if 'paragraphs' in data:
        for p_data in data['paragraphs']:
            para = ScriptParagraph.query.get(p_data.get('id'))
            if para and para.script_id == script.id:
                if 'text' in p_data:
                    para.text = p_data['text']
                if 'scene_direction' in p_data:
                    para.scene_direction = p_data['scene_direction']
                if 'mood' in p_data:
                    para.mood = p_data['mood']

    # Update full_text (rebuild from paragraphs or use provided)
    if 'full_text' in data:
        script.full_text = data['full_text']
        script.word_count = len(data['full_text'])

        # If no paragraph-level data, re-split
        if 'paragraphs' not in data:
            ScriptParagraph.query.filter_by(script_id=script.id).delete()
            for i, text in enumerate(_split_paragraphs(data['full_text'])):
                para = ScriptParagraph(script_id=script.id, paragraph_index=i, text=text)
                db.session.add(para)

    db.session.commit()
    return jsonify({'ok': True, 'script': script.to_dict()})


def _split_paragraphs(text):
    paragraphs = []
    for block in text.split('\n\n'):
        block = block.strip()
        if block:
            paragraphs.append(block)
    return paragraphs if paragraphs else [text.strip()]
