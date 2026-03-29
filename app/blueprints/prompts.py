import json
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request
from ..extensions import redis_client

prompts_bp = Blueprint('prompts', __name__)


@prompts_bp.route('/')
def index():
    return render_template('prompts/index.html')


@prompts_bp.route('/api/list', methods=['GET'])
def list_prompts():
    names = redis_client.smembers('prompt:list')
    prompts = []
    for name in sorted(names):
        data = redis_client.hgetall(f'prompt:{name}')
        data['name'] = name
        prompts.append(data)
    return jsonify({'prompts': prompts})


@prompts_bp.route('/api/<name>', methods=['GET'])
def get_prompt(name):
    data = redis_client.hgetall(f'prompt:{name}')
    if not data:
        return jsonify({'error': 'Prompt not found'}), 404
    data['name'] = name
    return jsonify(data)


@prompts_bp.route('/api/', methods=['POST'])
def create_prompt():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    if redis_client.sismember('prompt:list', name):
        return jsonify({'error': 'Prompt already exists'}), 409

    redis_client.hset(f'prompt:{name}', mapping={
        'template': data.get('template', ''),
        'description': data.get('description', ''),
        'updated_at': datetime.utcnow().isoformat(),
    })
    redis_client.sadd('prompt:list', name)
    return jsonify({'ok': True}), 201


@prompts_bp.route('/api/<name>', methods=['PUT'])
def update_prompt(name):
    if not redis_client.sismember('prompt:list', name):
        return jsonify({'error': 'Prompt not found'}), 404
    data = request.get_json()
    redis_client.hset(f'prompt:{name}', mapping={
        'template': data.get('template', ''),
        'description': data.get('description', ''),
        'updated_at': datetime.utcnow().isoformat(),
    })
    return jsonify({'ok': True})


@prompts_bp.route('/api/<name>', methods=['DELETE'])
def delete_prompt(name):
    redis_client.delete(f'prompt:{name}')
    redis_client.srem('prompt:list', name)
    return jsonify({'ok': True})
