"""
Phase 4: Testing API Routes
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models.testing import TestJob, VerifiedFinding, Payload
from app.models.intelligence import AttackCandidate
from tasks.testing_tasks import (
    task_execute_test_job,
    task_batch_test_candidates,
    task_initialize_payloads,
    task_retest_low_confidence
)
from datetime import datetime
import logging

testing_api = Blueprint('testing_api', __name__, url_prefix='/api/testing')
logger = logging.getLogger(__name__)


@testing_api.route('/initialize', methods=['POST'])
def initialize_testing():
    """Initialize testing infrastructure"""
    try:
        task = task_initialize_payloads.apply_async()
        
        return jsonify({
            'status': 'success',
            'message': 'Payload library initialization started',
            'task_id': task.id
        }), 202
    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/candidates/<int:candidate_id>/test', methods=['POST'])
def test_candidate(candidate_id):
    """
    Start test job for single candidate
    POST /api/testing/candidates/<id>/test
    """
    try:
        candidate = AttackCandidate.query.get_or_404(candidate_id)
        
        if not candidate.approved_for_testing:
            return jsonify({
                'status': 'error',
                'message': 'Candidate not approved for testing'
            }), 403
        
        task = task_execute_test_job.apply_async(args=[candidate_id])
        
        return jsonify({
            'status': 'success',
            'message': 'Test job started',
            'candidate_id': candidate_id,
            'task_id': task.id
        }), 202
    
    except Exception as e:
        logger.error(f"Test start failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/targets/<int:target_id>/test-batch', methods=['POST'])
def test_batch(target_id):
    """
    Start batch testing for target
    POST /api/testing/targets/<id>/test-batch
    Body: {"candidate_ids": [1,2,3]} (optional)
    """
    try:
        data = request.get_json() or {}
        candidate_ids = data.get('candidate_ids')
        
        task = task_batch_test_candidates.apply_async(
            args=[target_id],
            kwargs={'candidate_ids': candidate_ids}
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Batch testing started',
            'target_id': target_id,
            'task_id': task.id
        }), 202
    
    except Exception as e:
        logger.error(f"Batch test failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/jobs', methods=['GET'])
def list_test_jobs():
    """
    List test jobs
    GET /api/testing/jobs?target_id=1&status=VERIFIED&limit=50
    """
    try:
        target_id = request.args.get('target_id', type=int)
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = TestJob.query
        
        if target_id:
            query = query.filter_by(target_id=target_id)
        
        if status:
            query = query.filter_by(status=status)
        
        query = query.order_by(TestJob.created_at.desc())
        
        total = query.count()
        jobs = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'jobs': [j.to_dict() for j in jobs]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Job listing failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/jobs/<int:job_id>', methods=['GET'])
def get_test_job(job_id):
    """
    Get test job details
    GET /api/testing/jobs/<id>
    """
    try:
        job = TestJob.query.get_or_404(job_id)
        
        job_data = job.to_dict()
        job_data['test_results'] = [r.to_dict() for r in job.test_results.all()]
        
        if job.verified_finding:
            job_data['verified_finding'] = job.verified_finding.to_dict()
        
        return jsonify({
            'status': 'success',
            'data': job_data
        }), 200
    
    except Exception as e:
        logger.error(f"Job retrieval failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/jobs/<int:job_id>/retest', methods=['POST'])
def retest_job(job_id):
    """
    Retest low-confidence job
    POST /api/testing/jobs/<id>/retest
    """
    try:
        job = TestJob.query.get_or_404(job_id)
        
        if job.confidence_score >= 70:
            return jsonify({
                'status': 'error',
                'message': 'Job already high confidence'
            }), 400
        
        task = task_retest_low_confidence.apply_async(args=[job_id])
        
        return jsonify({
            'status': 'success',
            'message': 'Retest started',
            'task_id': task.id
        }), 202
    
    except Exception as e:
        logger.error(f"Retest failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/findings', methods=['GET'])
def list_findings():
    """
    List verified findings
    GET /api/testing/findings?target_id=1&severity=high&reviewed=false
    """
    try:
        target_id = request.args.get('target_id', type=int)
        severity = request.args.get('severity')
        reviewed = request.args.get('reviewed')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = VerifiedFinding.query
        
        if target_id:
            query = query.filter_by(target_id=target_id)
        
        if severity:
            query = query.filter_by(severity=severity)
        
        if reviewed is not None:
            reviewed_bool = reviewed.lower() == 'true'
            query = query.filter_by(human_reviewed=reviewed_bool)
        
        query = query.order_by(VerifiedFinding.discovered_at.desc())
        
        total = query.count()
        findings = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'findings': [f.to_dict() for f in findings]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Finding listing failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/findings/<int:finding_id>', methods='GET'])
def get_finding(finding_id):
    """
    Get finding details
    GET /api/testing/findings/<id>
    """
    try:
        finding = VerifiedFinding.query.get_or_404(finding_id)
        
        return jsonify({
            'status': 'success',
            'data': finding.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Finding retrieval failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/findings/<int:finding_id>/review', methods=['POST'])
def review_finding(finding_id):
    """
    Review finding (human-in-the-loop)
    POST /api/testing/findings/<id>/review
    Body: {"approved": true, "reviewed_by": "analyst"}
    """
    try:
        finding = VerifiedFinding.query.get_or_404(finding_id)
        data = request.get_json() or {}
        
        finding.human_reviewed = True
        finding.human_approved = data.get('approved', False)
        finding.reviewed_at = datetime.utcnow()
        finding.reviewed_by = data.get('reviewed_by', 'unknown')
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Finding reviewed',
            'data': finding.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Finding review failed: {str(e)}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/statistics', methods=['GET'])
def get_statistics():
    """
    Get testing statistics
    GET /api/testing/statistics?target_id=1
    """
    try:
        target_id = request.args.get('target_id', type=int)
        
        query = TestJob.query
        if target_id:
            query = query.filter_by(target_id=target_id)
        
        total_jobs = query.count()
        verified_jobs = query.filter_by(status='VERIFIED').count()
        failed_jobs = query.filter_by(status='FAILED').count()
        
        findings_query = VerifiedFinding.query
        if target_id:
            findings_query = findings_query.filter_by(target_id=target_id)
        
        total_findings = findings_query.count()
        high_confidence = findings_query.filter(VerifiedFinding.confidence_score >= 80).count()
        pending_review = findings_query.filter_by(human_reviewed=False).count()
        
        severity_counts = db.session.query(
            VerifiedFinding.severity,
            db.func.count(VerifiedFinding.id)
        ).filter(
            VerifiedFinding.target_id == target_id if target_id else True
        ).group_by(
            VerifiedFinding.severity
        ).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'test_jobs': {
                    'total': total_jobs,
                    'verified': verified_jobs,
                    'failed': failed_jobs
                },
                'findings': {
                    'total': total_findings,
                    'high_confidence': high_confidence,
                    'pending_review': pending_review,
                    'by_severity': {sev: count for sev, count in severity_counts}
                }
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Statistics failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@testing_api.route('/payloads', methods=['GET'])
def list_payloads():
    """
    List available payloads
    GET /api/testing/payloads?attack_type=XSS
    """
    try:
        attack_type = request.args.get('attack_type')
        
        query = Payload.query.filter_by(is_active=True)
        
        if attack_type:
            query = query.filter_by(attack_type=attack_type)
        
        payloads = query.all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': len(payloads),
                'payloads': [p.to_dict() for p in payloads]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Payload listing failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500