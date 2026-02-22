"""
Target Model
Represents a bug bounty target (program/organization)
"""
from datetime import datetime
from app.extensions import db


class Target(db.Model):
    """
    Bug Bounty Target model
    Represents a target organization/program with associated scope and attack profiles
    """
    __tablename__ = 'targets'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Core fields
    name = db.Column(db.String(200), nullable=False, unique=True, index=True)
    base_domain = db.Column(db.String(255), nullable=False)
    
    # Program information
    program_platform = db.Column(
        db.String(50), 
        nullable=False, 
        default='Self',
        comment='Platform: HackerOne, Bugcrowd, Self, etc.'
    )
    
    # Status tracking
    status = db.Column(
        db.String(20), 
        nullable=False, 
        default='active',
        comment='active, paused, completed'
    )
    
    # Metadata
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (lazy loading for performance)
    scopes = db.relationship(
        'Scope', 
        backref='target', 
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Scope.created_at'
    )
    
    attack_profiles = db.relationship(
        'AttackProfile', 
        backref='target', 
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='AttackProfile.attack_type'
    )
    
    scan_results = db.relationship(
        'ScanResult', 
        backref='target', 
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='ScanResult.created_at.desc()'
    )
    
    def __repr__(self):
        return f'<Target {self.name}>'
    
    def to_dict(self):
        """Serialize target to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'base_domain': self.base_domain,
            'program_platform': self.program_platform,
            'status': self.status,
            'description': self.description,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'scope_count': self.scopes.count(),
            'attack_profile_count': self.attack_profiles.count(),
            'scan_result_count': self.scan_results.count()
        }
    
    @property
    def in_scope_count(self):
        """Count of in-scope items"""
        return self.scopes.filter_by(in_scope=True).count()
    
    @property
    def out_of_scope_count(self):
        """Count of out-of-scope items"""
        return self.scopes.filter_by(in_scope=False).count()
    
    @property
    def enabled_attacks_count(self):
        """Count of enabled attack types"""
        return self.attack_profiles.filter_by(enabled=True).count()
