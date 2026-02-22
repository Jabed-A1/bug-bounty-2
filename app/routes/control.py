"""
Unified Dashboard Control Routes
Master control center for all phases (1-4)
Single source of truth for all operations
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime, timedelta
from app.extensions import db
from app.models.phase1 import Target, ScopeRule
from app.models.jobs import ReconJob, IntelligenceCandidate, TestJob, VerifiedFinding, JobStatus
from app.models.control import ScopeEnforcer, RateLimiter, KillSwitch
from app.services.control_service import (
    TargetController, ReconController, IntelligenceController,
    TestingController, SafetyController, MonitoringController
)
import logging

control_bp = Blueprint('control', __name__, url_prefix='/control')
logger = logging.getLogger(__name__)


# ============================================================================
# MAIN DASHBOARD - UNIFIED CONTROL CENTER
# ============================================================================

@control_bp.route('/')
def dashboard():
    """
    Main Control Dashboard
    Single source of truth for entire system state
    """
    # System-wide state
    kill_switch_active = KillSwitch.is_active()
    
    # Phase 1: Targets
    targets = Target.query.all()
    targets_enabled = Target.query.filter_by(enabled=True).count()
    targets_paused = Target.query.filter_by(paused=True).count()
    targets_total = len(targets)
    
    # Phase 2: Recon
    recon_running = ReconJob.query.filter_by(status='RUNNING').count()
    recon_queued = ReconJob.query.filter_by(status='QUEUED').count()
    recon_idle = ReconJob.query.filter_by(status='IDLE').count()
    recon_failed = ReconJob.query.filter_by(status='FAILED').count()
    
    # Phase 3: Intelligence
    candidates_total = IntelligenceCandidate.query.count()
    candidates_pending = IntelligenceCandidate.query.filter_by(reviewed=False).count()
    candidates_approved = IntelligenceCandidate.query.filter_by(approved_for_testing=True).count()
    candidates_rejected = IntelligenceCandidate.query.filter_by(rejected=True).count()
    
    # Phase 4: Testing
    tests_running = TestJob.query.filter_by(status='RUNNING').count()
    tests_queued = TestJob.query.filter_by(status='QUEUED').count()
    findings_total = VerifiedFinding.query.count()
    findings_unreviewed = VerifiedFinding.query.filter_by(human_reviewed=False).count()
    
    # Recent activity (last 30 minutes)
    thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
    recent_jobs = ReconJob.query.filter(ReconJob.created_at >= thirty_min_ago).order_by(
        ReconJob.created_at.desc()
    ).limit(20).all()
    
    recent_tests = TestJob.query.filter(TestJob.created_at >= thirty_min_ago).order_by(
        TestJob.created_at.desc()
    ).limit(20).all()
    
    # Latest findings
    latest_findings = VerifiedFinding.query.order_by(
        VerifiedFinding.discovered_at.desc()
    ).limit(10).all()
    
    stats = {
        'kill_switch_active': kill_switch_active,
        'targets': {
            'total': targets_total,
            'enabled': targets_enabled,
            'paused': targets_paused
        },
        'recon': {
            'running': recon_running,
            'queued': recon_queued,
            'idle': recon_idle,
            'failed': recon_failed
        },
        'intelligence': {
            'total': candidates_total,
            'pending': candidates_pending,
            'approved': candidates_approved,
            'rejected': candidates_rejected
        },
        'testing': {
            'running': tests_running,
            'queued': tests_queued,
            'findings_total': findings_total,
            'findings_unreviewed': findings_unreviewed
        }
    }
    
    return render_template(
        'control/dashboard.html',
        stats=stats,
        targets=targets,
        recent_jobs=recent_jobs,
        recent_tests=recent_tests,
        latest_findings=latest_findings,
        kill_switch_active=kill_switch_active
    )


# ============================================================================
# PHASE 1 - TARGET CONTROL
# ============================================================================

@control_bp.route('/target/<int:target_id>')
def target_control(target_id):
    """Target control panel"""
    target = Target.query.get_or_404(target_id)
    
    # Count active jobs
    active_recon = ReconJob.query.filter(
        ReconJob.target_id == target_id,
        ReconJob.status.in_(['RUNNING', 'QUEUED'])
    ).all()
    
    active_tests = TestJob.query.filter(
        TestJob.target_id == target_id,
        TestJob.status.in_(['RUNNING', 'QUEUED'])
    ).all()
    
    # Get recon history
    recon_history = ReconJob.query.filter_by(target_id=target_id).order_by(
        ReconJob.created_at.desc()
    ).limit(20).all()
    
    # Get scope config
    scope_enforcer = ScopeEnforcer.query.filter_by(target_id=target_id).first()
    if not scope_enforcer:
        scope_enforcer = ScopeEnforcer(target_id=target_id)
        db.session.add(scope_enforcer)
        db.session.commit()
    
    rate_limiter = RateLimiter.query.filter_by(target_id=target_id).first()
    if not rate_limiter:
        rate_limiter = RateLimiter(target_id=target_id)
        db.session.add(rate_limiter)
        db.session.commit()
    
    return render_template(
        'control/target_control.html',
        target=target,
        active_recon=active_recon,
        active_tests=active_tests,
        recon_history=recon_history,
        scope_enforcer=scope_enforcer,
        rate_limiter=rate_limiter
    )


@control_bp.route('/target/<int:target_id>/enable', methods=['POST'])
def target_enable(target_id):
    """Enable target (allow jobs to run)"""
    success, message = TargetController.enable_target(target_id)
    return jsonify({'success': success, 'message': message})


@control_bp.route('/target/<int:target_id>/disable', methods=['POST'])
def target_disable(target_id):
    """Disable target (prevent ALL jobs from running)"""
    success, message = TargetController.disable_target(target_id)
    return jsonify({'success': success, 'message': message})


@control_bp.route('/target/<int:target_id>/pause', methods=['POST'])
def target_pause(target_id):
    """Pause ALL activity for target (STOP running jobs)"""
    success, message = TargetController.pause_target(target_id)
    return jsonify({'success': success, 'message': message})


@control_bp.route('/target/<int:target_id>/resume', methods=['POST'])
def target_resume(target_id):
    """Resume activity for target"""
    success, message = TargetController.resume_target(target_id)
    return jsonify({'success': success, 'message': message})


# ============================================================================
# PHASE 2 - RECON CONTROL
# ============================================================================

@control_bp.route('/recon/<int:target_id>')
def recon_control(target_id):
    """Recon control panel for target"""
    target = Target.query.get_or_404(target_id)
    
    # Check if target can run jobs
    can_run = target.can_run_jobs
    kill_switch_active = KillSwitch.is_active()
    
    # Get all recon modules possible
    modules = [
        'subdomain_enum',
        'livehost_detect',
        'port_scan',
        'endpoint_collect',
        'directory_fuzz',
        'js_analysis'
    ]
    
    # Get current status for each module
    module_status = {}
    for module in modules:
        job = ReconJob.query.filter_by(
            target_id=target_id,
            module=module
        ).order_by(ReconJob.created_at.desc()).first()
        
        if job:
            module_status[module] = {
                'status': job.status,
                'job_id': job.id,
                'results_count': job.results_count,
                'progress_percent': job.progress_percent,
                'error_message': job.error_message,
                'duration_seconds': job.duration_seconds,
                'created_at': job.created_at,
                'started_at': job.started_at
            }
        else:
            module_status[module] = {
                'status': 'IDLE',
                'job_id': None,
                'results_count': 0,
                'progress_percent': 0,
                'error_message': None,
                'duration_seconds': None,
                'created_at': None,
                'started_at': None
            }
    
    # Get full history
    all_jobs = ReconJob.query.filter_by(target_id=target_id).order_by(
        ReconJob.created_at.desc()
    ).all()
    
    return render_template(
        'control/recon_control.html',
        target=target,
        can_run=can_run,
        kill_switch_active=kill_switch_active,
        modules=modules,
        module_status=module_status,
        all_jobs=all_jobs
    )


@control_bp.route('/recon/<int:target_id>/start/<module>', methods=['POST'])
def recon_start_module(target_id, module):
    """Start specific recon module"""
    success, message, job_id = ReconController.start_recon_module(target_id, module)
    if not success:
        return jsonify({'success': False, 'error': message}), 403
    return jsonify({
        'success': True,
        'message': message,
        'job_id': job_id,
        'status': 'QUEUED'
    })


@control_bp.route('/recon/<int:job_id>/stop', methods=['POST'])
def recon_stop_job(job_id):
    """Stop running recon job"""
    success, message = ReconController.stop_recon_job(job_id)
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    return jsonify({'success': True, 'message': message})


@control_bp.route('/recon/<int:job_id>/status', methods=['GET'])
def recon_job_status(job_id):
    """Get current status of recon job"""
    job = ReconJob.query.get_or_404(job_id)
    return jsonify(job.to_dict())


# ============================================================================
# PHASE 3 - INTELLIGENCE CONTROL
# ============================================================================

@control_bp.route('/intelligence/<int:target_id>')
def intelligence_control(target_id):
    """Intelligence control panel - review and approve candidates"""
    target = Target.query.get_or_404(target_id)
    
    # Get all candidates for this target
    candidates = IntelligenceCandidate.query.filter_by(target_id=target_id).order_by(
        IntelligenceCandidate.discovered_at.desc()
    ).all()
    
    # Group by status
    pending = [c for c in candidates if not c.reviewed]
    approved = [c for c in candidates if c.approved_for_testing]
    rejected = [c for c in candidates if c.rejected]
    
    stats = {
        'total': len(candidates),
        'pending': len(pending),
        'approved': len(approved),
        'rejected': len(rejected)
    }
    
    return render_template(
        'control/intelligence_control.html',
        target=target,
        stats=stats,
        pending_candidates=pending,
        approved_candidates=approved,
        rejected_candidates=rejected
    )


@control_bp.route('/intelligence/candidate/<int:candidate_id>/approve', methods=['POST'])
def approve_candidate(candidate_id):
    """Manually approve candidate for testing"""
    success, message = IntelligenceController.approve_candidate(candidate_id)
    return jsonify({'success': success, 'message': message})


@control_bp.route('/intelligence/candidate/<int:candidate_id>/reject', methods=['POST'])
def reject_candidate(candidate_id):
    """Safely reject candidate (no testing will occur)"""
    success, message = IntelligenceController.reject_candidate(candidate_id)
    return jsonify({'success': success, 'message': message})


@control_bp.route('/intelligence/candidate/<int:candidate_id>/addnote', methods=['POST'])
def candidate_add_note(candidate_id):
    """Add user notes to candidate"""
    candidate = IntelligenceCandidate.query.get_or_404(candidate_id)
    note = request.json.get('note', '')
    
    candidate.user_notes = note
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Note added'})


# ============================================================================
# PHASE 4 - TESTING CONTROL
# ============================================================================

@control_bp.route('/testing/<int:target_id>')
def testing_control(target_id):
    """Testing control panel"""
    target = Target.query.get_or_404(target_id)
    
    # Get all test jobs for target
    test_jobs = TestJob.query.filter_by(target_id=target_id).order_by(
        TestJob.created_at.desc()
    ).all()
    
    # Get all findings for target
    findings = VerifiedFinding.query.filter_by(target_id=target_id).order_by(
        VerifiedFinding.discovered_at.desc()
    ).all()
    
    # Status breakdown
    running_tests = [t for t in test_jobs if t.status == 'RUNNING']
    queued_tests = [t for t in test_jobs if t.status == 'QUEUED']
    done_tests = [t for t in test_jobs if t.status == 'DONE']
    failed_tests = [t for t in test_jobs if t.status == 'FAILED']
    
    # Finding breakdown
    unreviewed_findings = [f for f in findings if not f.human_reviewed]
    confirmed_findings = [f for f in findings if f.human_confirmed]
    
    can_run = target.can_run_jobs and not KillSwitch.is_active()
    
    return render_template(
        'control/testing_control.html',
        target=target,
        can_run=can_run,
        test_jobs=test_jobs,
        findings=findings,
        running_tests=running_tests,
        queued_tests=queued_tests,
        done_tests=done_tests,
        failed_tests=failed_tests,
        unreviewed_findings=unreviewed_findings,
        confirmed_findings=confirmed_findings
    )


@control_bp.route('/testing/<int:candidate_id>/start', methods=['POST'])
def test_start(candidate_id):
    """Start testing approved candidate"""
    candidate = IntelligenceCandidate.query.get_or_404(candidate_id)
    
    # Safety checks
    if not candidate.approved_for_testing:
        return jsonify({'success': False, 'error': 'Candidate not approved'}), 403
    
    if KillSwitch.is_active():
        return jsonify({'success': False, 'error': 'System kill switch is ACTIVE'}), 403
    
    target = Target.query.get(candidate.target_id)
    if not target.can_run_jobs:
        return jsonify({'success': False, 'error': f'Target {target.name} is disabled or paused'}), 403
    
    # Get payload category from request
    payload_category = request.json.get('payload_category', 'xss')
    
    # Create test job
    test_job = TestJob(
        candidate_id=candidate_id,
        target_id=candidate.target_id,
        payload_category=payload_category,
        status='QUEUED'
    )
    db.session.add(test_job)
    db.session.commit()
    
    logger.info(f'Test job created: Job#{test_job.id} / Candidate#{candidate_id} / {payload_category}')
    
    # TODO: Submit to Celery
    # task = celery_app.send_task('testing.payload_test', args=[test_job.id])
    # test_job.celery_task_id = task.id
    # db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Started testing with {payload_category}',
        'job_id': test_job.id,
        'status': 'QUEUED'
    })


@control_bp.route('/testing/<int:job_id>/stop', methods=['POST'])
def test_stop(job_id):
    """Stop running test job"""
    test_job = TestJob.query.get_or_404(job_id)
    
    if test_job.status not in ['RUNNING', 'QUEUED']:
        return jsonify({'success': False, 'error': f'Job is {test_job.status}'}), 400
    
    test_job.status = 'STOPPED'
    test_job.finished_at = datetime.utcnow()
    db.session.commit()
    
    logger.warning(f'Test job STOPPED: Job#{test_job.id}')
    
    return jsonify({'success': True, 'message': f'Stopped test job {job_id}'})


@control_bp.route('/findings/<int:finding_id>/review', methods=['POST'])
def finding_review(finding_id):
    """Mark finding as human reviewed"""
    finding = VerifiedFinding.query.get_or_404(finding_id)
    
    data = request.json or {}
    confirmed = data.get('confirmed', False)
    notes = data.get('notes', '')
    
    finding.human_reviewed = True
    finding.human_confirmed = confirmed
    finding.reviewer_notes = notes
    finding.reviewed_at = datetime.utcnow()
    db.session.commit()
    
    logger.info(f'Finding reviewed: {finding.id} - confirmed={confirmed}')
    return jsonify({'success': True, 'message': 'Finding reviewed'})


# ============================================================================
# GLOBAL SAFETY CONTROLS
# ============================================================================

@control_bp.route('/kill-switch/status', methods=['GET'])
def kill_switch_status():
    """Check kill switch status"""
    status = SafetyController.get_kill_switch_status()
    return jsonify(status)


@control_bp.route('/kill-switch/activate', methods=['POST'])
def kill_switch_activate():
    """EMERGENCY: Activate kill switch - STOP ALL OPERATIONS"""
    data = request.json or {}
    reason = data.get('reason', 'Emergency kill switch activated')
    
    success, message, jobs_stopped = SafetyController.activate_kill_switch(reason)
    return jsonify({
        'success': success,
        'message': message,
        'jobs_stopped': jobs_stopped
    })


@control_bp.route('/kill-switch/deactivate', methods=['POST'])
def kill_switch_deactivate():
    """Deactivate kill switch"""
    success, message = SafetyController.deactivate_kill_switch()
    return jsonify({'success': success, 'message': message})


# ============================================================================
# JOB MONITOR - REAL-TIME VISIBILITY
# ============================================================================

@control_bp.route('/monitor/jobs')
def job_monitor():
    """Real-time job monitor for all phases"""
    # Get recent activity (last 2 hours)
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    
    recent_jobs = ReconJob.query.filter(
        ReconJob.created_at >= two_hours_ago
    ).order_by(ReconJob.created_at.desc()).all()
    
    recent_tests = TestJob.query.filter(
        TestJob.created_at >= two_hours_ago
    ).order_by(TestJob.created_at.desc()).all()
    
    # Status breakdown
    stats = {
        'recon': {
            'running': ReconJob.query.filter_by(status='RUNNING').count(),
            'queued': ReconJob.query.filter_by(status='QUEUED').count(),
            'done': ReconJob.query.filter_by(status='DONE').count(),
            'failed': ReconJob.query.filter_by(status='FAILED').count(),
            'stopped': ReconJob.query.filter_by(status='STOPPED').count()
        },
        'testing': {
            'running': TestJob.query.filter_by(status='RUNNING').count(),
            'queued': TestJob.query.filter_by(status='QUEUED').count(),
            'done': TestJob.query.filter_by(status='DONE').count(),
            'failed': TestJob.query.filter_by(status='FAILED').count(),
            'stopped': TestJob.query.filter_by(status='STOPPED').count()
        }
    }
    
    return render_template(
        'control/job_monitor.html',
        recent_jobs=recent_jobs,
        recent_tests=recent_tests,
        stats=stats
    )


@control_bp.route('/api/jobs/recent')
def api_recent_jobs():
    """API endpoint for recent jobs (for AJAX polling)"""
    limit = int(request.args.get('limit', 50))
    
    recent_jobs = ReconJob.query.order_by(ReconJob.created_at.desc()).limit(limit).all()
    recent_tests = TestJob.query.order_by(TestJob.created_at.desc()).limit(limit).all()
    
    return jsonify({
        'recon_jobs': [j.to_dict() for j in recent_jobs],
        'test_jobs': [j.to_dict() for j in recent_tests]
    })
