"""
Unified Job Tracking Models
Provides consistent job state across all phases (Recon, Intelligence, Testing)
"""
from datetime import datetime
from enum import Enum
from app.extensions import db


class JobStatus(Enum):
    """Job status constants"""
    IDLE = "IDLE"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class ReconModuleType(Enum):
    """Recon module types"""
    SUBDOMAIN = "subdomain_enum"
    LIVE_HOST = "livehost_detect"
    PORT_SCAN = "port_scan"
    ENDPOINTS = "endpoint_collect"
    DIRECTORIES = "directory_fuzz"
    JS_ANALYSIS = "js_analysis"


class ReconJob(db.Model):
    """
    Recon Job - Phase 2 Control
    Single source of truth for all recon operations
    """
    __tablename__ = 'recon_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False, index=True)
    
    # Module being run
    module = db.Column(db.String(50), nullable=False)  # subdomain_enum, livehost_detect, etc.
    status = db.Column(db.String(20), default='IDLE', index=True)  # IDLE, QUEUED, RUNNING, DONE, FAILED, STOPPED
    
    # Celery integration
    celery_task_id = db.Column(db.String(100), unique=True, nullable=True)
    
    # Progress tracking
    results_count = db.Column(db.Integer, default=0)
    progress_percent = db.Column(db.Integer, default=0)
    
    # Timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    
    # Error tracking
    error_message = db.Column(db.Text, nullable=True)
    
    # Configuration
    config_json = db.Column(db.Text, nullable=True)  # Module-specific config
    
    def __repr__(self):
        return f'<ReconJob {self.id} - {self.module} - {self.status}>'
    
    @property
    def duration_seconds(self):
        """Calculate duration in seconds"""
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds())
        elif self.started_at:
            return int((datetime.utcnow() - self.started_at).total_seconds())
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'target_id': self.target_id,
            'module': self.module,
            'status': self.status,
            'celery_task_id': self.celery_task_id,
            'results_count': self.results_count,
            'progress_percent': self.progress_percent,
            'duration_seconds': self.duration_seconds,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'error_message': self.error_message
        }


class IntelligenceCandidate(db.Model):
    """
    Attack Candidate - Phase 3 Control
    Endpoint identified as potential attack target
    Requires explicit user approval before Phase 4 testing
    """
    __tablename__ = 'intelligence_candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False, index=True)
    
    # Identification
    endpoint_url = db.Column(db.Text, nullable=False)
    http_method = db.Column(db.String(10), default='GET')
    
    # Analysis
    confidence_score = db.Column(db.Float, default=0.0)  # 0.0 to 1.0
    reason = db.Column(db.Text, nullable=False)  # Why is this a candidate?
    
    # Risk level
    risk_level = db.Column(db.String(20), default='MEDIUM')  # LOW, MEDIUM, HIGH, CRITICAL
    
    # User control
    reviewed = db.Column(db.Boolean, default=False, index=True)
    approved_for_testing = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    
    # Notes
    user_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<IntelligenceCandidate {self.id} - {self.endpoint_url} - {self.confidence_score:.2f}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'target_id': self.target_id,
            'endpoint_url': self.endpoint_url,
            'http_method': self.http_method,
            'confidence_score': self.confidence_score,
            'reason': self.reason,
            'risk_level': self.risk_level,
            'reviewed': self.reviewed,
            'approved_for_testing': self.approved_for_testing,
            'rejected': self.rejected,
            'user_notes': self.user_notes,
            'discovered_at': self.discovered_at.isoformat(),
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None
        }


class TestJob(db.Model):
    """
    Test Job - Phase 4 Control
    Individual testing operation for an approved candidate
    """
    __tablename__ = 'test_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('intelligence_candidates.id'), nullable=False, index=True)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False, index=True)
    
    # Test configuration
    payload_category = db.Column(db.String(50), nullable=False)  # xss, sqli, lfi, api, auth, etc.
    status = db.Column(db.String(20), default='IDLE', index=True)  # IDLE, QUEUED, RUNNING, DONE, FAILED, STOPPED
    
    # Celery integration
    celery_task_id = db.Column(db.String(100), unique=True, nullable=True)
    
    # Test tracking
    requests_sent = db.Column(db.Integer, default=0)
    responses_received = db.Column(db.Integer, default=0)
    
    # Rate limiting
    rate_limit_per_second = db.Column(db.Integer, default=5)
    
    # Results
    vulnerability_found = db.Column(db.Boolean, default=False)
    confidence_change = db.Column(db.Float, default=0.0)  # Change in confidence score
    
    # Error tracking
    error_message = db.Column(db.Text, nullable=True)
    
    # Timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<TestJob {self.id} - {self.payload_category} - {self.status}>'
    
    @property
    def duration_seconds(self):
        """Calculate duration in seconds"""
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds())
        elif self.started_at:
            return int((datetime.utcnow() - self.started_at).total_seconds())
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'target_id': self.target_id,
            'payload_category': self.payload_category,
            'status': self.status,
            'celery_task_id': self.celery_task_id,
            'requests_sent': self.requests_sent,
            'responses_received': self.responses_received,
            'vulnerability_found': self.vulnerability_found,
            'confidence_change': self.confidence_change,
            'error_message': self.error_message,
            'duration_seconds': self.duration_seconds,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None
        }


class VerifiedFinding(db.Model):
    """
    Verified Finding - Final Phase 4 Output
    Only created from successful test jobs
    """
    __tablename__ = 'verified_findings'
    
    id = db.Column(db.Integer, primary_key=True)
    test_job_id = db.Column(db.Integer, db.ForeignKey('test_jobs.id'), nullable=False, index=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('intelligence_candidates.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False, index=True)
    
    # Vulnerability details
    vulnerability_type = db.Column(db.String(50), nullable=False)  # xss, sqli, lfi, api, auth, etc.
    severity = db.Column(db.String(20), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    
    # Evidence
    proof_of_concept = db.Column(db.Text, nullable=False)
    impact_description = db.Column(db.Text, nullable=True)
    
    # Human review
    human_reviewed = db.Column(db.Boolean, default=False, index=True)
    human_confirmed = db.Column(db.Boolean, default=False)
    reviewer_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<VerifiedFinding {self.id} - {self.vulnerability_type} - {self.severity}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'test_job_id': self.test_job_id,
            'candidate_id': self.candidate_id,
            'target_id': self.target_id,
            'vulnerability_type': self.vulnerability_type,
            'severity': self.severity,
            'proof_of_concept': self.proof_of_concept,
            'impact_description': self.impact_description,
            'human_reviewed': self.human_reviewed,
            'human_confirmed': self.human_confirmed,
            'reviewer_notes': self.reviewer_notes,
            'discovered_at': self.discovered_at.isoformat(),
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None
        }
