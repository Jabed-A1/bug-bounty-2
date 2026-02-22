"""
Logging utility module
Provides structured logging for audit trails and debugging
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(app):
    """
    Configure application logging with rotating file handler
    
    Args:
        app: Flask application instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(app.config['LOG_FILE']).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set logging level
    log_level = getattr(logging, app.config['LOG_LEVEL'].upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Configure app logger
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    
    # Remove default Flask handler to avoid duplicates
    app.logger.handlers = [h for h in app.logger.handlers if not isinstance(h, logging.StreamHandler) or h == console_handler]
    
    app.logger.info('Logging configured successfully')


class AuditLogger:
    """
    Structured audit logger for tracking security-relevant actions
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    def log_action(self, action, entity_type, entity_id=None, details=None, user_id=None):
        """
        Log an audit event
        
        Args:
            action: Action performed (create, update, delete, enable, disable)
            entity_type: Type of entity (target, scope, attack_profile, scan)
            entity_id: ID of the entity (optional)
            details: Additional details as dictionary (optional)
            user_id: User who performed the action (optional, for future auth)
        """
        log_message = f"[AUDIT] action={action} entity={entity_type}"
        
        if entity_id:
            log_message += f" id={entity_id}"
        
        if user_id:
            log_message += f" user={user_id}"
        
        if details:
            detail_str = " ".join([f"{k}={v}" for k, v in details.items()])
            log_message += f" {detail_str}"
        
        self.logger.info(log_message)
    
    def log_target_created(self, target_id, target_name):
        """Log target creation"""
        self.log_action('create', 'target', target_id, {'name': target_name})
    
    def log_target_updated(self, target_id, changes):
        """Log target update"""
        self.log_action('update', 'target', target_id, changes)
    
    def log_target_deleted(self, target_id):
        """Log target deletion"""
        self.log_action('delete', 'target', target_id)
    
    def log_scope_added(self, scope_id, target_id, scope_type, value):
        """Log scope addition"""
        self.log_action('create', 'scope', scope_id, {
            'target_id': target_id,
            'type': scope_type,
            'value': value
        })
    
    def log_scope_deleted(self, scope_id, target_id):
        """Log scope deletion"""
        self.log_action('delete', 'scope', scope_id, {'target_id': target_id})
    
    def log_attack_profile_updated(self, profile_id, attack_type, enabled):
        """Log attack profile update"""
        status = 'enabled' if enabled else 'disabled'
        self.log_action('update', 'attack_profile', profile_id, {
            'attack_type': attack_type,
            'status': status
        })
    
    def log_scan_started(self, scan_id, target_id, attack_type):
        """Log scan start"""
        self.log_action('start', 'scan', scan_id, {
            'target_id': target_id,
            'attack_type': attack_type
        })
    
    def log_scan_completed(self, scan_id, status, duration):
        """Log scan completion"""
        self.log_action('complete', 'scan', scan_id, {
            'status': status,
            'duration': duration
        })
