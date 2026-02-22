"""
Scan Result Model
Stores results from automated scans and attacks
"""
from datetime import datetime
from app.extensions import db


class ScanResult(db.Model):
    """
    Scan result storage
    Phase 1: Basic placeholder for future scan data
    Phase 2+: Will be expanded with detailed findings
    """
    __tablename__ = 'scan_results'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key
    target_id = db.Column(
        db.Integer, 
        db.ForeignKey('targets.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Scan metadata
    attack_type = db.Column(
        db.String(50), 
        nullable=False,
        index=True,
        comment='Type of attack that generated this result'
    )
    
    status = db.Column(
        db.String(20), 
        nullable=False, 
        default='pending',
        comment='pending, running, completed, failed, cancelled'
    )
    
    severity = db.Column(
        db.String(20), 
        nullable=True,
        comment='critical, high, medium, low, info'
    )
    
    # Result data
    result_summary = db.Column(db.Text, nullable=True, comment='Brief summary of findings')
    
    # Detailed results (JSON-like text for flexibility)
    # Future: Migrate to JSON column for PostgreSQL
    result_data = db.Column(
        db.Text, 
        nullable=True,
        comment='Detailed JSON result data'
    )
    
    # Metrics
    requests_sent = db.Column(db.Integer, nullable=True, default=0)
    vulnerabilities_found = db.Column(db.Integer, nullable=True, default=0)
    duration_seconds = db.Column(db.Integer, nullable=True)
    
    # Error tracking
    error_message = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<ScanResult {self.id} - {self.attack_type} - {self.status}>'
    
    def to_dict(self):
        """Serialize scan result to dictionary for API responses"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'attack_type': self.attack_type,
            'status': self.status,
            'severity': self.severity,
            'result_summary': self.result_summary,
            'requests_sent': self.requests_sent,
            'vulnerabilities_found': self.vulnerabilities_found,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    @property
    def duration_formatted(self):
        """Return formatted duration string"""
        if not self.duration_seconds:
            return "N/A"
        
        hours, remainder = divmod(self.duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    @staticmethod
    def get_status_options():
        """Return available status options"""
        return ['pending', 'running', 'completed', 'failed', 'cancelled']
    
    @staticmethod
    def get_severity_options():
        """Return available severity options"""
        return ['critical', 'high', 'medium', 'low', 'info']
