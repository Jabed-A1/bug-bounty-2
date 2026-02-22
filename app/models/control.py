"""
Safety and Control Models
Manages system-wide safety: scope compliance, rate limits, kill switches
"""
from datetime import datetime
from app.extensions import db


class ScopeEnforcer(db.Model):
    """
    Tracks scope enforcement status per target
    Ensures no requests go outside defined scope
    """
    __tablename__ = 'scope_enforcers'
    
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False, unique=True, index=True)
    
    # Status
    enabled = db.Column(db.Boolean, default=True)
    
    # Metrics
    requests_allowed = db.Column(db.Integer, default=0)
    requests_blocked = db.Column(db.Integer, default=0)
    
    # Last check
    last_check_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'target_id': self.target_id,
            'enabled': self.enabled,
            'requests_allowed': self.requests_allowed,
            'requests_blocked': self.requests_blocked,
            'last_check_at': self.last_check_at.isoformat() if self.last_check_at else None
        }


class RateLimiter(db.Model):
    """
    Rate limiting enforcement per target
    """
    __tablename__ = 'rate_limiters'
    
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False, unique=True, index=True)
    
    # Limits
    requests_per_second = db.Column(db.Integer, default=5)
    max_concurrent_jobs = db.Column(db.Integer, default=3)
    
    # Status
    active = db.Column(db.Boolean, default=True)
    current_rate = db.Column(db.Float, default=0.0)
    current_jobs = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'target_id': self.target_id,
            'requests_per_second': self.requests_per_second,
            'max_concurrent_jobs': self.max_concurrent_jobs,
            'active': self.active,
            'current_rate': self.current_rate,
            'current_jobs': self.current_jobs
        }


class KillSwitch(db.Model):
    """
    Emergency kill switch
    ONE switch for entire system
    """
    __tablename__ = 'kill_switch'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # All operations stop when this is True
    active = db.Column(db.Boolean, default=False, index=True)
    
    # Reason for activation
    reason = db.Column(db.Text, nullable=True)
    
    # Timestamps
    activated_at = db.Column(db.DateTime, nullable=True)
    deactivated_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def is_active():
        """Check if kill switch is active"""
        switch = KillSwitch.query.first()
        if not switch:
            # Create default if doesn't exist
            switch = KillSwitch(active=False)
            db.session.add(switch)
            db.session.commit()
        return switch.active
    
    def to_dict(self):
        return {
            'id': self.id,
            'active': self.active,
            'reason': self.reason,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'deactivated_at': self.deactivated_at.isoformat() if self.deactivated_at else None
        }
