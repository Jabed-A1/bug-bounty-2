"""
Professional Bug Bounty Dashboard
Main UI controller for all phases
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.phase1 import Target
from app.models.recon import ReconJob, Subdomain, LiveHost, Endpoint
from app.models.intelligence import AttackCandidate, EndpointCluster
from app.models.testing import TestJob, VerifiedFinding
from datetime import datetime, timedelta
import logging

dashboard_bp = Blueprint('dashboard', __name__)
logger = logging.getLogger(__name__)


@dashboard_bp.route('/dashboard')
def index():
    """Main dashboard overview"""
    # Get overall statistics
    stats = {
        'targets': {
            'total': Target.query.count(),
            'active': Target.query.filter_by(status='active').count()
        },
        'recon': {
            'jobs_running': ReconJob.query.filter_by(status='running').count(),
            'subdomains_found': Subdomain.query.count(),
            'endpoints_found': Endpoint.query.count()
        },
        'intelligence': {
            'candidates_pending': AttackCandidate.query.filter_by(reviewed=False).count(),
            'candidates_approved': AttackCandidate.query.filter_by(approved_for_testing=True).count()
        },
        'testing': {
            'jobs_running': TestJob.query.filter_by(status='RUNNING').count(),
            'findings_total': VerifiedFinding.query.count(),
            'findings_unreviewed': VerifiedFinding.query.filter_by(human_reviewed=False).count()
        }
    }
    
    # Recent activity
    recent_jobs = ReconJob.query.order_by(ReconJob.started_at.desc()).limit(5).all()
    recent_findings = VerifiedFinding.query.order_by(VerifiedFinding.discovered_at.desc()).limit(5).all()
    
    return render_template('dashboard/index.html', 
                         stats=stats,
                         recent_jobs=recent_jobs,
                         recent_findings=recent_findings)


@dashboard_bp.route('/targets')
def targets_list():
    """Phase 1: Target management"""
    targets = Target.query.all()
    
    # Enrich with stats
    for target in targets:
        target.subdomain_count = Subdomain.query.filter_by(target_id=target.id).count()
        target.endpoint_count = Endpoint.query.filter_by(target_id=target.id).count()
        target.finding_count = VerifiedFinding.query.filter_by(target_id=target.id).count()
    
    return render_template('dashboard/targets_list.html', targets=targets)


@dashboard_bp.route('/targets/<int:target_id>')
def target_detail(target_id):
    """Phase 1: Target detail and control"""
    target = Target.query.get_or_404(target_id)
    
    # Get detailed stats
    stats = {
        'subdomains': {
            'total': Subdomain.query.filter_by(target_id=target_id).count(),
            'alive': Subdomain.query.filter_by(target_id=target_id, alive=True).count()
        },
        'endpoints': {
            'total': Endpoint.query.filter_by(target_id=target_id).count(),
            'with_params': Endpoint.query.filter_by(target_id=target_id, has_params=True).count()
        },
        'clusters': {
            'total': EndpointCluster.query.filter_by(target_id=target_id).count()
        },
        'candidates': {
            'total': AttackCandidate.query.filter_by(target_id=target_id).count(),
            'pending': AttackCandidate.query.filter_by(target_id=target_id, reviewed=False).count(),
            'approved': AttackCandidate.query.filter_by(target_id=target_id, approved_for_testing=True).count()
        },
        'findings': {
            'total': VerifiedFinding.query.filter_by(target_id=target_id).count(),
            'unreviewed': VerifiedFinding.query.filter_by(target_id=target_id, human_reviewed=False).count(),
            'critical': VerifiedFinding.query.filter_by(target_id=target_id, severity='critical').count(),
            'high': VerifiedFinding.query.filter_by(target_id=target_id, severity='high').count()
        }
    }
    
    # Recent activity
    recent_recon_jobs = ReconJob.query.filter_by(target_id=target_id).order_by(
        ReconJob.started_at.desc()
    ).limit(10).all()
    
    return render_template('dashboard/target_detail.html', target=target, stats=stats, recent_jobs=recent_recon_jobs)


@dashboard_bp.route('/targets/new', methods=['GET', 'POST'])
def target_create():
    """Create new target"""
    if request.method == 'POST':
        try:
            import json
            
            target = Target(
                name=request.form['name'],
                domain=request.form['domain'],
                program_url=request.form.get('program_url', ''),
                scope_rules=json.dumps({
                    'in_scope': request.form.getlist('in_scope'),
                    'out_of_scope': request.form.getlist('out_of_scope')
                }),
                status='active'
            )
            
            db.session.add(target)
            db.session.commit()
            
            flash(f'Target {target.domain} created successfully', 'success')
            return redirect(url_for('dashboard.target_detail', target_id=target.id))
        
        except Exception as e:
            logger.error(f"Target creation failed: {str(e)}")
            flash(f'Error creating target: {str(e)}', 'danger')
    
    return render_template('dashboard/target_form.html')


@dashboard_bp.route('/targets/<int:target_id>/edit', methods=['GET', 'POST'])
def target_edit(target_id):
    """Edit target"""
    target = Target.query.get_or_404(target_id)
    
    if request.method == 'POST':
        try:
            import json
            
            target.name = request.form['name']
            target.domain = request.form['domain']
            target.program_url = request.form.get('program_url', '')
            target.scope_rules = json.dumps({
                'in_scope': request.form.getlist('in_scope'),
                'out_of_scope': request.form.getlist('out_of_scope')
            })
            
            db.session.commit()
            
            flash('Target updated successfully', 'success')
            return redirect(url_for('dashboard.target_detail', target_id=target.id))
        
        except Exception as e:
            logger.error(f"Target update failed: {str(e)}")
            flash(f'Error updating target: {str(e)}', 'danger')
    
    return render_template('dashboard/target_form.html', target=target)


@dashboard_bp.route('/recon/jobs')
def recon_jobs():
    """Phase 2: Recon job control center"""
    target_id = request.args.get('target_id', type=int)
    status_filter = request.args.get('status')
    
    query = ReconJob.query
    
    if target_id:
        query = query.filter_by(target_id=target_id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    jobs = query.order_by(ReconJob.started_at.desc()).limit(100).all()
    targets = Target.query.all()
    
    return render_template('dashboard/recon_jobs.html', jobs=jobs, targets=targets)


@dashboard_bp.route('/recon/logs')
def recon_logs():
    """Phase 2: Recon logs viewer"""
    target_id = request.args.get('target_id', type=int)
    stage = request.args.get('stage')
    
    query = ReconJob.query
    
    if target_id:
        query = query.filter_by(target_id=target_id)
    
    if stage:
        query = query.filter_by(stage=stage)
    
    jobs = query.order_by(ReconJob.started_at.desc()).limit(50).all()
    targets = Target.query.all()
    
    return render_template('dashboard/recon_logs.html', jobs=jobs, targets=targets)


@dashboard_bp.route('/intelligence/clusters')
def intelligence_clusters():
    """Phase 3: Endpoint clusters view"""
    target_id = request.args.get('target_id', type=int)
    
    query = EndpointCluster.query
    
    if target_id:
        query = query.filter_by(target_id=target_id)
    
    clusters = query.order_by(EndpointCluster.endpoint_count.desc()).limit(100).all()
    targets = Target.query.all()
    
    return render_template('dashboard/intelligence_clusters.html', clusters=clusters, targets=targets)


@dashboard_bp.route('/intelligence/candidates')
def intelligence_candidates():
    """Phase 3: Attack candidate review"""
    target_id = request.args.get('target_id', type=int)
    attack_type = request.args.get('attack_type')
    reviewed = request.args.get('reviewed')
    
    query = AttackCandidate.query
    
    if target_id:
        query = query.filter_by(target_id=target_id)
    
    if attack_type:
        query = query.filter_by(attack_type=attack_type)
    
    if reviewed == 'false':
        query = query.filter_by(reviewed=False)
    elif reviewed == 'true':
        query = query.filter_by(reviewed=True)
    
    candidates = query.order_by(AttackCandidate.created_at.desc()).limit(100).all()
    targets = Target.query.all()
    
    # Get unique attack types for filter
    attack_types = db.session.query(AttackCandidate.attack_type).distinct().all()
    attack_types = [at[0] for at in attack_types]
    
    return render_template('dashboard/intelligence_candidates.html', 
                         candidates=candidates, 
                         targets=targets,
                         attack_types=attack_types)


@dashboard_bp.route('/testing/jobs')
def testing_jobs():
    """Phase 4: Test job monitoring"""
    target_id = request.args.get('target_id', type=int)
    status_filter = request.args.get('status')
    
    query = TestJob.query
    
    if target_id:
        query = query.filter_by(target_id=target_id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    jobs = query.order_by(TestJob.created_at.desc()).limit(100).all()
    targets = Target.query.all()
    
    return render_template('dashboard/testing_jobs.html', jobs=jobs, targets=targets)


@dashboard_bp.route('/testing/jobs/<int:job_id>')
def testing_job_detail(job_id):
    """Phase 4: Test job detail view"""
    job = TestJob.query.get_or_404(job_id)
    test_results = job.test_results.all()
    
    return render_template('dashboard/testing_job_detail.html', job=job, test_results=test_results)


@dashboard_bp.route('/findings')
def findings_list():
    """Phase 4: Verified findings management"""
    target_id = request.args.get('target_id', type=int)
    severity = request.args.get('severity')
    reviewed = request.args.get('reviewed')
    
    query = VerifiedFinding.query
    
    if target_id:
        query = query.filter_by(target_id=target_id)
    
    if severity:
        query = query.filter_by(severity=severity)
    
    if reviewed == 'false':
        query = query.filter_by(human_reviewed=False)
    elif reviewed == 'true':
        query = query.filter_by(human_reviewed=True)
    
    findings = query.order_by(VerifiedFinding.discovered_at.desc()).all()
    targets = Target.query.all()
    
    return render_template('dashboard/findings_list.html', findings=findings, targets=targets)


@dashboard_bp.route('/findings/<int:finding_id>')
def finding_detail(finding_id):
    """Phase 4: Finding detail view"""
    finding = VerifiedFinding.query.get_or_404(finding_id)
    
    return render_template('dashboard/finding_detail.html', finding=finding)


@dashboard_bp.route('/logs')
def system_logs():
    """System-wide logs viewer"""
    try:
        with open('logs/app.log', 'r') as f:
            # Read last 500 lines
            lines = f.readlines()[-500:]
            log_content = ''.join(lines)
    except FileNotFoundError:
        log_content = 'No logs available'
    
    return render_template('dashboard/system_logs.html', log_content=log_content)


@dashboard_bp.route('/settings')
def settings():
    """System settings and configuration"""
    return render_template('dashboard/settings.html')


# ============================================
# SYSTEM API ENDPOINTS
# ============================================

@dashboard_bp.route('/api/system/status')
def api_system_status():
    """Get system status"""
    try:
        # Check Celery workers (simplified)
        celery_workers = 1  # Would check actual Celery inspect
        
        pending_tasks = (
            ReconJob.query.filter_by(status='running').count() +
            TestJob.query.filter_by(status='RUNNING').count()
        )
        
        return jsonify({
            'status': 'ok',
            'celery_workers': celery_workers,
            'pending_tasks': pending_tasks,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@dashboard_bp.route('/api/system/kill-switch', methods=['POST'])
def api_kill_switch():
    """Emergency kill switch"""
    data = request.get_json()
    active = data.get('active', False)
    
    # Implementation would set a global flag that all tasks check
    # For now, just log the action
    logger.critical(f"KILL SWITCH {'ACTIVATED' if active else 'DEACTIVATED'}")
    
    return jsonify({
        'status': 'success',
        'kill_switch_active': active
    })