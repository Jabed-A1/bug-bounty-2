"""
Scope Model
Defines what is in-scope and out-of-scope for a target
"""
from datetime import datetime
from app.extensions import db


class Scope(db.Model):
    """
    Scope definition for targets
    Defines domains, wildcards, URLs, and APIs that are in or out of scope
    """
    __tablename__ = 'scopes'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key
    target_id = db.Column(
        db.Integer, 
        db.ForeignKey('targets.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Scope definition
    scope_type = db.Column(
        db.String(50), 
        nullable=False,
        comment='domain, wildcard, url, api, ip_range, mobile_app'
    )
    
    value = db.Column(db.String(500), nullable=False, comment='The actual scope value')
    
    # Scope status
    in_scope = db.Column(
        db.Boolean, 
        nullable=False, 
        default=True,
        comment='True = in scope, False = out of scope'
    )
    
    # Additional metadata
    notes = db.Column(db.Text, nullable=True, comment='Additional context or restrictions')
    priority = db.Column(
        db.Integer, 
        nullable=False, 
        default=5,
        comment='Priority level 1-10, higher = more important'
    )
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        scope_status = 'IN' if self.in_scope else 'OUT'
        return f'<Scope {scope_status}: {self.scope_type} - {self.value}>'
    
    def to_dict(self):
        """Serialize scope to dictionary for API responses"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'scope_type': self.scope_type,
            'value': self.value,
            'in_scope': self.in_scope,
            'notes': self.notes,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def get_scope_types():
        """Return available scope types"""
        return [
            'domain',
            'wildcard',
            'url',
            'api',
            'ip_range',
            'mobile_app'
        ]
