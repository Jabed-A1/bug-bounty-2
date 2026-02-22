"""
Phase 1: Target & Scope Management Models
Consistent model for all phases to use
"""
from datetime import datetime
from app.extensions import db


class Target(db.Model):
    """
    Target model from Phase 1
    Extended with control fields for dashboard
    """
    __tablename__ = 'targets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    domain = db.Column(db.String(255), nullable=False, unique=True, index=True)
    program_url = db.Column(db.String(500))
    scope_rules = db.Column(db.Text)  # JSON string
    
    # Control fields - CRITICAL
    status = db.Column(db.String(20), default='active', index=True)  # active, paused, archived
    enabled = db.Column(db.Boolean, default=True, index=True)  # Must be True to run jobs
    paused = db.Column(db.Boolean, default=False, index=True)  # Pause ALL activity
    
    # Activity tracking
    last_action_at = db.Column(db.DateTime, nullable=True)  # Last time ANY job ran
    last_modified_at = db.Column(db.DateTime, nullable=True)  # Last config change
    
    # Metadata
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Phase 2 relationships (if needed)
    # These will be added by Phase 2 models via backref
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'name': self.name,
            'domain': self.domain,
            'program_url': self.program_url,
            'scope_rules': json.loads(self.scope_rules) if self.scope_rules else {},
            'status': self.status,
            'enabled': self.enabled,
            'paused': self.paused,
            'last_action_at': self.last_action_at.isoformat() if self.last_action_at else None,
            'last_modified_at': self.last_modified_at.isoformat() if self.last_modified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def active_jobs_count(self):
        """Get count of currently running/queued jobs"""
        from app.models.jobs import ReconJob, TestJob
        recon_count = ReconJob.query.filter(
            ReconJob.target_id == self.id,
            ReconJob.status.in_(['RUNNING', 'QUEUED'])
        ).count()
        test_count = TestJob.query.filter(
            TestJob.target_id == self.id,
            TestJob.status.in_(['RUNNING', 'QUEUED'])
        ).count()
        return recon_count + test_count
    
    @property
    def can_run_jobs(self):
        """Check if target can run jobs (enabled AND not paused)"""
        return self.enabled and not self.paused


class ScopeRule(db.Model):
    """
    Scope rules from Phase 1
    This is a simplified version - replace with your actual Phase 1 model
    """
    __tablename__ = 'scope_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False)
    rule_type = db.Column(db.String(20), nullable=False)  # domain, subdomain, ip, path
    value = db.Column(db.String(500), nullable=False)
    in_scope = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    target = db.relationship('Target', backref=db.backref('rules', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'target_id': self.target_id,
            'rule_type': self.rule_type,
            'value': self.value,
            'in_scope': self.in_scope,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# NOTE: This is a minimal Phase 1 model implementation
# In a real deployment, you would:
# 1. Have more comprehensive Phase 1 models
# 2. Include user authentication
# 3. Have program/organization models
# 4. Include API key management
# 5. Have more detailed scope management
#
# Phase 2 is designed to work with ANY Phase 1 implementation
# as long as the Target model has at minimum:
# - id
# - domain
# - scope_rules (optional, can be None)