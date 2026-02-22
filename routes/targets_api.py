from flask import Blueprint, request, jsonify
from app import db
from app.models.phase1 import Target
import json

targets_api = Blueprint('targets_api', __name__, url_prefix='/api/targets')

@targets_api.route('', methods=['GET'])
def list_targets():
    try:
        targets = Target.query.all()
        return jsonify({
            'status': 'success',
            'data': [t.to_dict() for t in targets]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@targets_api.route('', methods=['POST'])
def create_target():
    try:
        data = request.get_json()
        target = Target(
            name=data['name'],
            domain=data['domain'],
            program_url=data.get('program_url', ''),
            scope_rules=json.dumps(data.get('scope_rules', {})),
            status=data.get('status', 'active')
        )
        db.session.add(target)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'data': target.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@targets_api.route('/<int:target_id>', methods=['GET'])
def get_target(target_id):
    try:
        target = Target.query.get_or_404(target_id)
        return jsonify({
            'status': 'success',
            'data': target.to_dict()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404

@targets_api.route('/<int:target_id>', methods=['DELETE'])
def delete_target(target_id):
    try:
        target = Target.query.get_or_404(target_id)
        db.session.delete(target)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Target deleted'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
