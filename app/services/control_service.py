"""
Control Center Service Layer
Unified business logic for all control operations
Reduces duplication and ensures consistent behavior
"""
from datetime import datetime
from app.extensions import db
from app.models.phase1 import Target
from app.models.jobs import ReconJob, IntelligenceCandidate, TestJob, VerifiedFinding, JobStatus
from app.models.control import ScopeEnforcer, RateLimiter, KillSwitch
import logging

logger = logging.getLogger(__name__)


class TargetController:
    """Phase 1: Target control operations"""
    
    @staticmethod
    def enable_target(target_id):
        """Enable target (allow jobs to run)"""
        target = Target.query.get(target_id)
        if not target:
            return False, "Target not found"
        
        target.enabled = True
        target.last_modified_at = datetime.utcnow()
        db.session.commit()
        logger.info(f'Target enabled: {target.name}')
        return True, f'{target.name} enabled'
    
    @staticmethod
    def disable_target(target_id):
        """Disable target (prevent ALL jobs)"""
        target = Target.query.get(target_id)
        if not target:
            return False, "Target not found"
        
        target.enabled = False
        target.last_modified_at = datetime.utcnow()
        db.session.commit()
        logger.info(f'Target disabled: {target.name}')
        return True, f'{target.name} disabled'
    
    @staticmethod
    def pause_target(target_id):
        """Pause ALL operations for target (STOP running jobs)"""
        target = Target.query.get(target_id)
        if not target:
            return False, "Target not found"
        
        target.paused = True
        target.last_modified_at = datetime.utcnow()
        db.session.commit()
        
        # Stop all running jobs
        running_jobs = ReconJob.query.filter(
            ReconJob.target_id == target_id,
            ReconJob.status == 'RUNNING'
        ).all()
        
        for job in running_jobs:
            job.status = 'STOPPED'
            job.finished_at = datetime.utcnow()
        
        db.session.commit()
        logger.warning(f'Target PAUSED: {target.name} ({len(running_jobs)} jobs stopped)')
        return True, f'{target.name} paused - {len(running_jobs)} jobs stopped'
    
    @staticmethod
    def resume_target(target_id):
        """Resume target operations"""
        target = Target.query.get(target_id)
        if not target:
            return False, "Target not found"
        
        target.paused = False
        target.last_modified_at = datetime.utcnow()
        db.session.commit()
        logger.info(f'Target resumed: {target.name}')
        return True, f'{target.name} resumed'
    
    @staticmethod
    def can_target_run_jobs(target_id):
        """Check if target is allowed to run jobs"""
        target = Target.query.get(target_id)
        if not target:
            return False
        return target.enabled and not target.paused


class ReconController:
    """Phase 2: Recon job control"""
    
    @staticmethod
    def start_recon_module(target_id, module):
        """Start recon module for target"""
        # Safety checks
        if KillSwitch.is_active():
            return False, "System kill switch is ACTIVE", None
        
        target = Target.query.get(target_id)
        if not target:
            return False, "Target not found", None
        
        if not target.can_run_jobs:
            return False, f"Target {target.name} is disabled or paused", None
        
        # Create job
        job = ReconJob(
            target_id=target_id,
            module=module,
            status='QUEUED'
        )
        db.session.add(job)
        db.session.commit()
        
        logger.info(f'Recon job created: {target.name} / {module} / Job#{job.id}')
        
        # TODO: Submit to Celery
        # from app.tasks.recon_tasks import task_recon_module
        # task = task_recon_module.apply_async(args=[job.id, target_id, module])
        # job.celery_task_id = task.id
        # db.session.commit()
        
        return True, f'Started {module}', job.id
    
    @staticmethod
    def stop_recon_job(job_id):
        """Stop running recon job"""
        job = ReconJob.query.get(job_id)
        if not job:
            return False, "Job not found"
        
        if job.status not in ['RUNNING', 'QUEUED']:
            return False, f'Job is {job.status}, cannot stop'
        
        job.status = 'STOPPED'
        job.finished_at = datetime.utcnow()
        db.session.commit()
        
        logger.warning(f'Recon job STOPPED: Job#{job_id} ({job.module})')
        
        # TODO: Revoke Celery task
        # if job.celery_task_id:
        #     celery_app.control.revoke(job.celery_task_id, terminate=True)
        
        return True, f'Stopped job {job_id}'
    
    @staticmethod
    def get_job_status(job_id):
        """Get recon job status"""
        job = ReconJob.query.get(job_id)
        if job:
            return job.to_dict()
        return None


class IntelligenceController:
    """Phase 3: Intelligence/Candidate control"""
    
    @staticmethod
    def approve_candidate(candidate_id):
        """Approve candidate for testing"""
        candidate = IntelligenceCandidate.query.get(candidate_id)
        if not candidate:
            return False, "Candidate not found"
        
        candidate.reviewed = True
        candidate.approved_for_testing = True
        candidate.rejected = False
        candidate.reviewed_at = datetime.utcnow()
        candidate.approved_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f'Candidate approved: {candidate.endpoint_url}')
        return True, f'Approved: {candidate.endpoint_url}'
    
    @staticmethod
    def reject_candidate(candidate_id):
        """Reject candidate"""
        candidate = IntelligenceCandidate.query.get(candidate_id)
        if not candidate:
            return False, "Candidate not found"
        
        candidate.reviewed = True
        candidate.rejected = True
        candidate.approved_for_testing = False
        candidate.reviewed_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f'Candidate rejected: {candidate.endpoint_url}')
        return True, f'Rejected: {candidate.endpoint_url}'
    
    @staticmethod
    def add_candidate_note(candidate_id, note):
        """Add notes to candidate"""
        candidate = IntelligenceCandidate.query.get(candidate_id)
        if not candidate:
            return False, "Candidate not found"
        
        candidate.user_notes = note
        db.session.commit()
        return True, 'Note added'


class TestingController:
    """Phase 4: Testing job control"""
    
    @staticmethod
    def start_test(candidate_id, payload_category):
        """Start test for approved candidate"""
        candidate = IntelligenceCandidate.query.get(candidate_id)
        if not candidate:
            return False, "Candidate not found", None
        
        if not candidate.approved_for_testing:
            return False, "Candidate not approved", None
        
        if KillSwitch.is_active():
            return False, "System kill switch is ACTIVE", None
        
        target = Target.query.get(candidate.target_id)
        if not target.can_run_jobs:
            return False, f"Target {target.name} is disabled or paused", None
        
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
        # from app.tasks.testing_tasks import task_payload_test
        # task = task_payload_test.apply_async(args=[test_job.id])
        # test_job.celery_task_id = task.id
        # db.session.commit()
        
        return True, f'Started testing with {payload_category}', test_job.id
    
    @staticmethod
    def stop_test(job_id):
        """Stop running test job"""
        test_job = TestJob.query.get(job_id)
        if not test_job:
            return False, "Test job not found"
        
        if test_job.status not in ['RUNNING', 'QUEUED']:
            return False, f'Job is {test_job.status}'
        
        test_job.status = 'STOPPED'
        test_job.finished_at = datetime.utcnow()
        db.session.commit()
        
        logger.warning(f'Test job STOPPED: Job#{job_id}')
        return True, f'Stopped test job {job_id}'
    
    @staticmethod
    def review_finding(finding_id, confirmed, notes):
        """Mark finding as reviewed"""
        finding = VerifiedFinding.query.get(finding_id)
        if not finding:
            return False, "Finding not found"
        
        finding.human_reviewed = True
        finding.human_confirmed = confirmed
        finding.reviewer_notes = notes
        finding.reviewed_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f'Finding reviewed: {finding_id} - confirmed={confirmed}')
        return True, 'Finding reviewed'


class SafetyController:
    """Safety controls: Kill switch, scope enforcement, rate limiting"""
    
    @staticmethod
    def activate_kill_switch(reason='Manual activation'):
        """EMERGENCY: Activate kill switch"""
        switch = KillSwitch.query.first()
        if not switch:
            switch = KillSwitch(active=False)
            db.session.add(switch)
        
        switch.active = True
        switch.activated_at = datetime.utcnow()
        switch.reason = reason
        db.session.commit()
        
        # Stop all running jobs
        running_recon = ReconJob.query.filter_by(status='RUNNING').all()
        running_tests = TestJob.query.filter_by(status='RUNNING').all()
        
        for job in running_recon + running_tests:
            job.status = 'STOPPED'
            job.finished_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.critical(f'KILL SWITCH ACTIVATED: {reason}')
        return True, 'KILL SWITCH ACTIVATED - ALL OPERATIONS STOPPED', len(running_recon) + len(running_tests)
    
    @staticmethod
    def deactivate_kill_switch():
        """Deactivate kill switch"""
        switch = KillSwitch.query.first()
        if not switch:
            switch = KillSwitch(active=False)
            db.session.add(switch)
        
        switch.active = False
        switch.deactivated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info('Kill switch deactivated')
        return True, 'Kill switch deactivated'
    
    @staticmethod
    def get_kill_switch_status():
        """Get kill switch status"""
        switch = KillSwitch.query.first()
        if not switch:
            switch = KillSwitch(active=False)
            db.session.add(switch)
            db.session.commit()
        return switch.to_dict()
    
    @staticmethod
    def setup_scope_enforcer(target_id):
        """Initialize scope enforcer for target"""
        enforcer = ScopeEnforcer.query.filter_by(target_id=target_id).first()
        if not enforcer:
            enforcer = ScopeEnforcer(target_id=target_id, enabled=True)
            db.session.add(enforcer)
            db.session.commit()
        return enforcer
    
    @staticmethod
    def setup_rate_limiter(target_id, requests_per_second=5, max_concurrent=3):
        """Initialize rate limiter for target"""
        limiter = RateLimiter.query.filter_by(target_id=target_id).first()
        if not limiter:
            limiter = RateLimiter(
                target_id=target_id,
                requests_per_second=requests_per_second,
                max_concurrent_jobs=max_concurrent,
                active=True
            )
            db.session.add(limiter)
            db.session.commit()
        return limiter


class MonitoringController:
    """Real-time monitoring and reporting"""
    
    @staticmethod
    def get_system_stats():
        """Get overall system statistics"""
        return {
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
            },
            'targets': {
                'total': Target.query.count(),
                'enabled': Target.query.filter_by(enabled=True).count(),
                'paused': Target.query.filter_by(paused=True).count()
            },
            'intelligence': {
                'total': IntelligenceCandidate.query.count(),
                'pending': IntelligenceCandidate.query.filter_by(reviewed=False).count(),
                'approved': IntelligenceCandidate.query.filter_by(approved_for_testing=True).count(),
                'rejected': IntelligenceCandidate.query.filter_by(rejected=True).count()
            },
            'findings': {
                'total': VerifiedFinding.query.count(),
                'unreviewed': VerifiedFinding.query.filter_by(human_reviewed=False).count(),
                'confirmed': VerifiedFinding.query.filter_by(human_confirmed=True).count()
            }
        }
    
    @staticmethod
    def get_target_activity(target_id):
        """Get activity for specific target"""
        active_recon = ReconJob.query.filter(
            ReconJob.target_id == target_id,
            ReconJob.status.in_(['RUNNING', 'QUEUED'])
        ).all()
        
        active_tests = TestJob.query.filter(
            TestJob.target_id == target_id,
            TestJob.status.in_(['RUNNING', 'QUEUED'])
        ).all()
        
        return {
            'active_recon_jobs': len(active_recon),
            'active_test_jobs': len(active_tests),
            'total_active': len(active_recon) + len(active_tests)
        }
