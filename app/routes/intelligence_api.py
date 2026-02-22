"""
Phase 3: Intelligence API Routes
RESTful endpoints for intelligence data
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models.intelligence import (
    EndpointCluster, EndpointParameter, AttackCandidate,
    AuthSurface, ResponseDiff
)
from tasks.intelligence_tasks import (
    task_full_intelligence_pipeline,
    task_run_endpoint_clustering,
    task_analyze_parameters,
    task_generate_attack_candidates
)
from services.endpoint_normalizer import EndpointNormalizer
from services.parameter_analyzer import ParameterAnalyzer
from services.attack_decision_engine import AttackDecisionEngine
from datetime import datetime
import logging

intel_api = Blueprint('intel_api', __name__, url_prefix='/api/intel')
logger = logging.getLogger(__name__)


@intel_api.route('/targets/<int:target_id>/run', methods=['POST'])
def run_intelligence(target_id):
    """
    Start intelligence pipeline for target
    POST /api/intel/targets/<target_id>/run
    """
    try:
        from app.models.phase1 import Target
        target = Target.query.get_or_404(target_id)
        
        data = request.get_json() or {}
        stages = data.get('stages', ['all'])
        
        if 'all' in stages:
            task = task_full_intelligence_pipeline.apply_async(args=[target_id])
            return jsonify({
                'status': 'success',
                'message': 'Full intelligence pipeline started',
                'task_id': task.id,
                'target_id': target_id
            }), 202
        
        tasks_started = []
        
        if 'clustering' in stages:
            task = task_run_endpoint_clustering.apply_async(args=[target_id])
            tasks_started.append({'stage': 'clustering', 'task_id': task.id})
        
        if 'parameters' in stages:
            task = task_analyze_parameters.apply_async(args=[target_id])
            tasks_started.append({'stage': 'parameters', 'task_id': task.id})
        
        if 'candidates' in stages:
            task = task_generate_attack_candidates.apply_async(args=[target_id])
            tasks_started.append({'stage': 'candidates', 'task_id': task.id})
        
        return jsonify({
            'status': 'success',
            'message': f'Started {len(tasks_started)} intelligence stages',
            'tasks': tasks_started
        }), 202
    
    except Exception as e:
        logger.error(f"Error starting intelligence: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@intel_api.route('/targets/<int:target_id>/summary', methods=['GET'])
def get_intelligence_summary(target_id):
    """
    Get intelligence summary for target
    GET /api/intel/targets/<target_id>/summary
    """
    try:
        cluster_stats = EndpointNormalizer.get_statistics(target_id)
        param_stats = ParameterAnalyzer.get_statistics(target_id)
        candidate_stats = AttackDecisionEngine.get_statistics(target_id)
        
        return jsonify({
            'status': 'success',
            'data': {
                'target_id': target_id,
                'clusters': cluster_stats,
                'parameters': param_stats,
                'attack_candidates': candidate_stats
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting summary: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@intel_api.route('/endpoints', methods=['GET'])
def get_endpoint_clusters():
    """
    Get endpoint clusters with filters
    GET /api/intel/endpoints?target_id=1&has_params=true&limit=50
    """
    try:
        target_id = request.args.get('target_id', type=int)
        has_params = request.args.get('has_params')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = EndpointCluster.query
        
        if target_id:
            query = query.filter_by(target_id=target_id)
        
        if has_params == 'true':
            query = query.filter(EndpointCluster.parameter_signature != 'no_params')
        elif has_params == 'false':
            query = query.filter_by(parameter_signature='no_params')
        
        total = query.count()
        clusters = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'clusters': [c.to_dict() for c in clusters]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting clusters: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@intel_api.route('/parameters', methods=['GET'])
def get_parameters():
    """
    Get parameter intelligence
    GET /api/intel/parameters?cluster_id=1&role=identifier
    """
    try:
        cluster_id = request.args.get('cluster_id', type=int)
        role = request.args.get('role')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = EndpointParameter.query
        
        if cluster_id:
            query = query.filter_by(cluster_id=cluster_id)
        
        if role:
            query = query.filter_by(semantic_role=role)
        
        total = query.count()
        parameters = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'parameters': [p.to_dict() for p in parameters]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting parameters: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@intel_api.route('/candidates', methods=['GET'])
def get_attack_candidates():
    """
    Get attack candidates with filters
    GET /api/intel/candidates?target_id=1&attack_type=XSS&reviewed=false&risk=high
    """
    try:
        target_id = request.args.get('target_id', type=int)
        attack_type = request.args.get('attack_type')
        reviewed = request.args.get('reviewed')
        risk_level = request.args.get('risk')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = AttackCandidate.query
        
        if target_id:
            query = query.filter_by(target_id=target_id)
        
        if attack_type:
            query = query.filter_by(attack_type=attack_type)
        
        if reviewed == 'true':
            query = query.filter_by(reviewed=True)
        elif reviewed == 'false':
            query = query.filter_by(reviewed=False)
        
        if risk_level:
            query = query.filter_by(risk_level=risk_level)
        
        query = query.order_by(AttackCandidate.created_at.desc())
        
        total = query.count()
        candidates = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'candidates': [c.to_dict() for c in candidates]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting candidates: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@intel_api.route('/candidates/<int:candidate_id>/review', methods=['POST'])
def mark_candidate_reviewed(candidate_id):
    """
    Mark attack candidate as reviewed
    POST /api/intel/candidates/<candidate_id>/review
    Body: {"approved": true, "reviewed_by": "analyst_name"}
    """
    try:
        candidate = AttackCandidate.query.get_or_404(candidate_id)
        
        data = request.get_json() or {}
        
        candidate.reviewed = True
        candidate.reviewed_at = datetime.utcnow()
        candidate.reviewed_by = data.get('reviewed_by', 'unknown')
        candidate.approved_for_testing = data.get('approved', False)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Candidate marked as reviewed',
            'data': candidate.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error reviewing candidate: {str(e)}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@intel_api.route('/candidates/bulk-review', methods=['POST'])
def bulk_review_candidates():
    """
    Mark multiple candidates as reviewed
    POST /api/intel/candidates/bulk-review
    Body: {"candidate_ids": [1,2,3], "approved": false, "reviewed_by": "analyst"}
    """
    try:
        data = request.get_json() or {}
        candidate_ids = data.get('candidate_ids', [])
        approved = data.get('approved', False)
        reviewed_by = data.get('reviewed_by', 'unknown')
        
        if not candidate_ids:
            return jsonify({
                'status': 'error',
                'message': 'No candidate_ids provided'
            }), 400
        
        candidates = AttackCandidate.query.filter(
            AttackCandidate.id.in_(candidate_ids)
        ).all()
        
        for candidate in candidates:
            candidate.reviewed = True
            candidate.reviewed_at = datetime.utcnow()
            candidate.reviewed_by = reviewed_by
            candidate.approved_for_testing = approved
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Marked {len(candidates)} candidates as reviewed',
            'count': len(candidates)
        }), 200
    
    except Exception as e:
        logger.error(f"Error bulk reviewing: {str(e)}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@intel_api.route('/auth-surfaces', methods=['GET'])
def get_auth_surfaces():
    """
    Get authentication surface data
    GET /api/intel/auth-surfaces?target_id=1&is_authenticated=true
    """
    try:
        target_id = request.args.get('target_id', type=int)
        is_authenticated = request.args.get('is_authenticated')
        limit = request.args.get('limit', 50, type=int)
        
        if not target_id:
            return jsonify({
                'status': 'error',
                'message': 'target_id required'
            }), 400
        
        clusters = EndpointCluster.query.filter_by(target_id=target_id).all()
        cluster_ids = [c.id for c in clusters]
        
        query = AuthSurface.query.filter(AuthSurface.cluster_id.in_(cluster_ids))
        
        if is_authenticated == 'true':
            query = query.filter_by(is_authenticated=True)
        elif is_authenticated == 'false':
            query = query.filter_by(is_authenticated=False)
        
        surfaces = query.limit(limit).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': len(surfaces),
                'auth_surfaces': [s.to_dict() for s in surfaces]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting auth surfaces: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500