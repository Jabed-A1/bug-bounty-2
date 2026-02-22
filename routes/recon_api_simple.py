from flask import Blueprint, request, jsonify
from app import db
from app.models.phase1 import Target
from app.models.recon_simple import ReconJob, Subdomain
from datetime import datetime

recon_api = Blueprint('recon_api', __name__, url_prefix='/api/recon')

@recon_api.route('/targets/<int:target_id>/start-subdomain', methods=['POST'])
def start_subdomain_enum(target_id):
    try:
        target = Target.query.get_or_404(target_id)
        
        # Create job record
        job = ReconJob(
            target_id=target_id,
            stage='subdomain',
            status='CREATED'
        )
        db.session.add(job)
        db.session.commit()
        
        # Try to dispatch celery task, but don't fail if celery isn't running
        try:
            from tasks.recon_tasks_simple import task_run_subdomain_enum
            task = task_run_subdomain_enum.delay(job.id, target.domain)
            job.celery_task_id = task.id
            db.session.commit()
            message = 'Subdomain enumeration started'
        except Exception as e:
            # Celery not running - just create the job
            message = f'Job created (Celery not available: {str(e)})'
        
        return jsonify({
            'status': 'success',
            'message': message,
            'job_id': job.id
        }), 202
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@recon_api.route('/jobs', methods=['GET'])
def list_jobs():
    try:
        jobs = ReconJob.query.order_by(ReconJob.created_at.desc()).limit(50).all()
        
        # Get target info
        from app.models.phase1 import Target
        result = []
        for job in jobs:
            job_dict = job.to_dict()
            target = Target.query.get(job.target_id)
            if target:
                job_dict['target_domain'] = target.domain
            result.append(job_dict)
        
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@recon_api.route('/targets/<int:target_id>/subdomains', methods=['GET'])
def get_subdomains(target_id):
    try:
        subdomains = Subdomain.query.filter_by(target_id=target_id).all()
        return jsonify({
            'status': 'success',
            'count': len(subdomains),
            'data': [
                {
                    'id': s.id,
                    'subdomain': s.subdomain,
                    'source': s.source,
                    'alive': s.alive
                } for s in subdomains
            ]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
