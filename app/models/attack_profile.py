"""
Attack Profile Model
Defines which attack types are enabled for each target
"""
from datetime import datetime
from app.extensions import db


class AttackProfile(db.Model):
    """
    Attack Profile configuration for targets
    Defines which attack types to run and their parameters
    """
    __tablename__ = 'attack_profiles'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key
    target_id = db.Column(
        db.Integer, 
        db.ForeignKey('targets.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Attack configuration
    attack_type = db.Column(
        db.String(50), 
        nullable=False,
        comment='Type of attack: recon, xss, sqli, lfi, api, auth, etc.'
    )
    
    enabled = db.Column(
        db.Boolean, 
        nullable=False, 
        default=True,
        comment='Whether this attack type is enabled'
    )
    
    # Rate limiting and safety
    rate_limit = db.Column(
        db.Integer, 
        nullable=False, 
        default=10,
        comment='Requests per second limit'
    )
    
    max_threads = db.Column(
        db.Integer, 
        nullable=False, 
        default=5,
        comment='Maximum concurrent threads for this attack'
    )
    
    # Configuration (JSON-like text for flexibility)
    # Future: Could migrate to JSON column type if using PostgreSQL
    config_json = db.Column(
        db.Text, 
        nullable=True,
        comment='JSON string for attack-specific configuration'
    )
    
    # Metadata
    notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique attack types per target
    __table_args__ = (
        db.UniqueConstraint('target_id', 'attack_type', name='unique_target_attack'),
    )
    
    def __repr__(self):
        status = 'ENABLED' if self.enabled else 'DISABLED'
        return f'<AttackProfile {self.attack_type} - {status}>'
    
    def to_dict(self):
        """Serialize attack profile to dictionary for API responses"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'attack_type': self.attack_type,
            'enabled': self.enabled,
            'rate_limit': self.rate_limit,
            'max_threads': self.max_threads,
            'config_json': self.config_json,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def get_attack_types():
        """Return available attack types"""
        return [
            'recon',
            'subdomain_enum',
            'port_scan',
            'directory_brute',
            'xss',
            'sqli',
            'lfi',
            'rfi',
            'ssrf',
            'api_fuzzing',
            'auth_bypass',
            'idor',
            'xxe',
            'deserialization',
            'custom'
        ]
    
    @staticmethod
    def get_default_profiles():
        """Return default attack profiles for new targets"""
        return [
            {'attack_type': 'recon', 'enabled': True, 'rate_limit': 5},
            {'attack_type': 'subdomain_enum', 'enabled': True, 'rate_limit': 10},
            {'attack_type': 'port_scan', 'enabled': False, 'rate_limit': 5},
            {'attack_type': 'directory_brute', 'enabled': False, 'rate_limit': 10},
            {'attack_type': 'xss', 'enabled': False, 'rate_limit': 20},
            {'attack_type': 'sqli', 'enabled': False, 'rate_limit': 10},
        ]
