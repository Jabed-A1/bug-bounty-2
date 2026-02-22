"""
Phase 4: Safe Payload Library
Non-destructive, verification-only payloads
"""
import logging
from typing import List, Dict
from app import db
from app.models.testing import Payload

logger = logging.getLogger(__name__)


class PayloadLibrary:
    """
    Centralized safe payload management
    All payloads are non-destructive and verification-focused
    """
    
    @staticmethod
    def initialize_library():
        """Initialize default safe payloads"""
        logger.info("Initializing safe payload library")
        
        payloads = []
        
        # XSS Payloads (reflection detection only)
        payloads.extend([
            {
                'attack_type': 'XSS',
                'payload_string': '<script>alert(1)</script>',
                'payload_type': 'basic_reflection',
                'detection_pattern': '<script>alert\\(1\\)</script>',
                'confidence_weight': 15,
                'description': 'Basic XSS reflection test'
            },
            {
                'attack_type': 'XSS',
                'payload_string': '"><script>alert(document.domain)</script>',
                'payload_type': 'quote_escape',
                'detection_pattern': '"><script>alert\\(document\\.domain\\)</script>',
                'confidence_weight': 20,
                'description': 'XSS with quote escape'
            },
            {
                'attack_type': 'XSS',
                'payload_string': '<img src=x onerror=alert(1)>',
                'payload_type': 'event_handler',
                'detection_pattern': '<img src=x onerror=alert\\(1\\)>',
                'confidence_weight': 18,
                'description': 'Event handler XSS'
            },
            {
                'attack_type': 'XSS',
                'payload_string': 'xss_test_12345',
                'payload_type': 'canary_string',
                'detection_pattern': 'xss_test_12345',
                'confidence_weight': 5,
                'description': 'Simple reflection canary'
            }
        ])
        
        # SQLi Payloads (error-based detection only)
        payloads.extend([
            {
                'attack_type': 'SQLi',
                'payload_string': "'",
                'payload_type': 'single_quote',
                'detection_pattern': '(SQL|MySQL|syntax|query) error',
                'confidence_weight': 10,
                'description': 'Basic SQL error detection'
            },
            {
                'attack_type': 'SQLi',
                'payload_string': "' OR '1'='1",
                'payload_type': 'boolean_logic',
                'detection_pattern': '(SQL|MySQL|syntax|query) error',
                'confidence_weight': 15,
                'description': 'Boolean-based SQL error'
            },
            {
                'attack_type': 'SQLi',
                'payload_string': "1' AND '1'='1",
                'payload_type': 'and_logic',
                'detection_pattern': '(SQL|MySQL|syntax|query) error',
                'confidence_weight': 12,
                'description': 'AND-based SQL test'
            },
            {
                'attack_type': 'SQLi',
                'payload_string': "admin'--",
                'payload_type': 'comment_injection',
                'detection_pattern': '(SQL|MySQL|syntax|query) error',
                'confidence_weight': 18,
                'description': 'Comment-based SQL test'
            }
        ])
        
        # IDOR Payloads (behavioral comparison)
        payloads.extend([
            {
                'attack_type': 'IDOR',
                'payload_string': '1',
                'payload_type': 'sequential_id',
                'detection_pattern': None,
                'confidence_weight': 10,
                'description': 'Sequential ID test'
            },
            {
                'attack_type': 'IDOR',
                'payload_string': '2',
                'payload_type': 'sequential_id',
                'detection_pattern': None,
                'confidence_weight': 10,
                'description': 'Sequential ID test +1'
            },
            {
                'attack_type': 'IDOR',
                'payload_string': '999999',
                'payload_type': 'high_id',
                'detection_pattern': None,
                'confidence_weight': 8,
                'description': 'High ID boundary test'
            }
        ])
        
        # Open Redirect Payloads
        payloads.extend([
            {
                'attack_type': 'Open Redirect',
                'payload_string': 'https://evil.com',
                'payload_type': 'external_domain',
                'detection_pattern': 'evil\\.com',
                'confidence_weight': 20,
                'description': 'External domain redirect'
            },
            {
                'attack_type': 'Open Redirect',
                'payload_string': '//evil.com',
                'payload_type': 'protocol_relative',
                'detection_pattern': '//evil\\.com',
                'confidence_weight': 18,
                'description': 'Protocol-relative redirect'
            },
            {
                'attack_type': 'Open Redirect',
                'payload_string': '/\\evil.com',
                'payload_type': 'backslash_bypass',
                'detection_pattern': 'evil\\.com',
                'confidence_weight': 15,
                'description': 'Backslash bypass redirect'
            }
        ])
        
        # SSRF Payloads (safe internal domains only)
        payloads.extend([
            {
                'attack_type': 'SSRF',
                'payload_string': 'http://localhost',
                'payload_type': 'localhost',
                'detection_pattern': None,
                'confidence_weight': 15,
                'description': 'Localhost SSRF test'
            },
            {
                'attack_type': 'SSRF',
                'payload_string': 'http://127.0.0.1',
                'payload_type': 'loopback',
                'detection_pattern': None,
                'confidence_weight': 15,
                'description': 'Loopback SSRF test'
            },
            {
                'attack_type': 'SSRF',
                'payload_string': 'http://169.254.169.254',
                'payload_type': 'metadata',
                'detection_pattern': None,
                'confidence_weight': 20,
                'description': 'Cloud metadata SSRF test'
            }
        ])
        
        # LFI Payloads (non-destructive)
        payloads.extend([
            {
                'attack_type': 'LFI',
                'payload_string': '../../../etc/passwd',
                'payload_type': 'path_traversal',
                'detection_pattern': 'root:.*:0:0:',
                'confidence_weight': 25,
                'description': 'Path traversal to /etc/passwd'
            },
            {
                'attack_type': 'LFI',
                'payload_string': '....//....//....//etc/passwd',
                'payload_type': 'double_encoding',
                'detection_pattern': 'root:.*:0:0:',
                'confidence_weight': 22,
                'description': 'Double-encoded path traversal'
            },
            {
                'attack_type': 'LFI',
                'payload_string': '/etc/passwd',
                'payload_type': 'absolute_path',
                'detection_pattern': 'root:.*:0:0:',
                'confidence_weight': 20,
                'description': 'Absolute path LFI'
            }
        ])
        
        # Insert payloads
        for payload_data in payloads:
            existing = Payload.query.filter_by(
                attack_type=payload_data['attack_type'],
                payload_string=payload_data['payload_string']
            ).first()
            
            if not existing:
                payload = Payload(**payload_data)
                db.session.add(payload)
        
        db.session.commit()
        logger.info(f"Initialized {len(payloads)} safe payloads")
    
    @staticmethod
    def get_payloads_for_attack_type(attack_type: str) -> List[Payload]:
        """Get all active payloads for attack type"""
        return Payload.query.filter_by(
            attack_type=attack_type,
            is_active=True,
            is_safe=True
        ).all()
    
    @staticmethod
    def add_custom_payload(attack_type: str, payload_string: str, 
                          payload_type: str, detection_pattern: str = None,
                          confidence_weight: int = 10, description: str = None) -> Payload:
        """Add custom safe payload"""
        payload = Payload(
            attack_type=attack_type,
            payload_string=payload_string,
            payload_type=payload_type,
            detection_pattern=detection_pattern,
            confidence_weight=confidence_weight,
            is_safe=True,
            description=description
        )
        db.session.add(payload)
        db.session.commit()
        return payload