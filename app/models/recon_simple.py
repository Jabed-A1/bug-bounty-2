"""
Simplified Recon Models - NO CONFLICTS
"""
from datetime import datetime
from app import db

class ReconJob(db.Model):
    """Recon job tracking"""
    __tablename__ = 'recon_jobs'
    __table_args__ = {'extend_existing': True}  # Allow redefining if exists
    
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False)
    stage = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='CREATED', index=True)
    celery_task_id = db.Column(db.String(100))
    results_count = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    raw_output = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'target_id': self.target_id,
            'stage': self.stage,
            'status': self.status,
            'results_count': self.results_count,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Subdomain(db.Model):
    """Discovered subdomains"""
    __tablename__ = 'subdomains'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False)
    subdomain = db.Column(db.String(255), nullable=False)
    source = db.Column(db.String(50))
    alive = db.Column(db.Boolean)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('target_id', 'subdomain', name='uq_target_subdomain'),
        {'extend_existing': True}
    )

class Endpoint(db.Model):
    """Discovered endpoints"""
    __tablename__ = 'endpoints'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False)
    url = db.Column(db.Text, nullable=False)
    method = db.Column(db.String(10), default='GET')
    source = db.Column(db.String(50))
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow)
