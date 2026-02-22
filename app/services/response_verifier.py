"""
Phase 4: Response Verification Engine
Analyzes responses for vulnerability signals
"""
import re
import logging
from typing import Dict, Tuple
import hashlib

logger = logging.getLogger(__name__)


class ResponseVerifier:
    """
    Analyzes HTTP responses for vulnerability indicators
    Returns signals and confidence deltas
    """
    
    # Error patterns for SQLi detection
    SQL_ERROR_PATTERNS = [
        r'SQL syntax.*MySQL',
        r'Warning.*mysql_',
        r'MySQLSyntaxErrorException',
        r'valid MySQL result',
        r'check the manual that corresponds to your MySQL',
        r'PostgreSQL.*ERROR',
        r'Warning.*pg_',
        r'SQLite.*error',
        r'Microsoft SQL Native Client error',
        r'ODBC SQL Server Driver',
        r'SQLServer JDBC Driver',
        r'Oracle error',
        r'ORA-\d{5}',
        r'DB2 SQL error'
    ]
    
    def verify_xss(self, payload: str, response_body: str, 
                   detection_pattern: str = None) -> Tuple[bool, int, str]:
        """
        Verify XSS reflection
        Returns: (signal_detected, confidence_delta, evidence)
        """
        if not response_body:
            return False, 0, "Empty response"
        
        # Check for exact payload reflection
        if payload in response_body:
            # Additional context check
            context = self._get_reflection_context(payload, response_body)
            
            if '<script>' in payload.lower() and '<script>' in context.lower():
                return True, 20, f"Payload reflected in script context: {context[:100]}"
            elif 'onerror=' in payload.lower() and 'onerror=' in context.lower():
                return True, 18, f"Payload reflected in event handler: {context[:100]}"
            else:
                return True, 10, f"Payload reflected: {context[:100]}"
        
        # Check for pattern match if provided
        if detection_pattern:
            if re.search(detection_pattern, response_body, re.IGNORECASE):
                return True, 15, f"Detection pattern matched: {detection_pattern}"
        
        return False, 0, "No reflection detected"
    
    def verify_sqli(self, payload: str, response_body: str, 
                    response_status: int) -> Tuple[bool, int, str]:
        """
        Verify SQL injection via error messages
        Returns: (signal_detected, confidence_delta, evidence)
        """
        if not response_body:
            return False, 0, "Empty response"
        
        # Check for SQL error patterns
        for pattern in self.SQL_ERROR_PATTERNS:
            match = re.search(pattern, response_body, re.IGNORECASE)
            if match:
                error_snippet = match.group(0)
                return True, 18, f"SQL error detected: {error_snippet[:100]}"
        
        # Check for 500 errors (potential SQL errors)
        if response_status == 500:
            if any(keyword in response_body.lower() for keyword in ['error', 'exception', 'warning']):
                return True, 8, "500 error with error keywords"
        
        return False, 0, "No SQL error detected"
    
    def verify_idor(self, baseline_response: Dict, test_response: Dict) -> Tuple[bool, int, str]:
        """
        Verify IDOR via response comparison
        Returns: (signal_detected, confidence_delta, evidence)
        """
        if not baseline_response or not test_response:
            return False, 0, "Missing baseline or test response"
        
        baseline_status = baseline_response.get('response_status')
        test_status = test_response.get('response_status')
        
        # Different status codes = behavioral change
        if baseline_status != test_status:
            if test_status == 200 and baseline_status == 403:
                return True, 25, f"Access granted: {baseline_status} -> {test_status}"
            elif test_status == 200 and baseline_status == 404:
                return True, 20, f"Resource found: {baseline_status} -> {test_status}"
            else:
                return True, 10, f"Status change: {baseline_status} -> {test_status}"
        
        # Content length comparison
        baseline_length = len(baseline_response.get('response_body', ''))
        test_length = len(test_response.get('response_body', ''))
        
        if baseline_length > 0 and test_length > 0:
            diff_percent = abs(baseline_length - test_length) / baseline_length * 100
            
            if diff_percent > 30:
                return True, 15, f"Significant content difference: {diff_percent:.1f}%"
            elif diff_percent > 10:
                return True, 8, f"Moderate content difference: {diff_percent:.1f}%"
        
        return False, 0, "No significant behavioral difference"
    
    def verify_open_redirect(self, payload: str, response_headers: Dict,
                             response_status: int) -> Tuple[bool, int, str]:
        """
        Verify open redirect via Location header
        Returns: (signal_detected, confidence_delta, evidence)
        """
        # Check for redirect status codes
        if response_status not in [301, 302, 303, 307, 308]:
            return False, 0, "No redirect status"
        
        location = response_headers.get('Location', response_headers.get('location', ''))
        
        if not location:
            return False, 0, "No Location header"
        
        # Check if payload domain is in Location header
        payload_clean = payload.replace('https://', '').replace('http://', '').replace('//', '')
        
        if payload_clean in location:
            return True, 22, f"External redirect to payload domain: {location[:100]}"
        
        # Check for protocol-relative redirect
        if location.startswith('//') and payload_clean in location:
            return True, 20, f"Protocol-relative redirect: {location[:100]}"
        
        return False, 0, "Redirect not to payload domain"
    
    def verify_ssrf(self, payload: str, response_status: int, 
                    response_time_ms: int, response_body: str) -> Tuple[bool, int, str]:
        """
        Verify SSRF via timing and content analysis
        Returns: (signal_detected, confidence_delta, evidence)
        """
        # Check for successful connection to internal resource
        if response_status == 200:
            # Check for common internal service responses
            internal_indicators = [
                'localhost',
                '127.0.0.1',
                'metadata',
                'instance-id',
                'ami-id'
            ]
            
            for indicator in internal_indicators:
                if indicator in response_body.lower():
                    return True, 22, f"Internal resource indicator found: {indicator}"
        
        # Timing-based detection for localhost
        if 'localhost' in payload or '127.0.0.1' in payload:
            if response_time_ms < 100:  # Very fast response suggests loopback
                return True, 12, f"Fast loopback response: {response_time_ms}ms"
        
        # Cloud metadata endpoint
        if '169.254.169.254' in payload:
            if response_status == 200 and len(response_body) > 0:
                return True, 25, "Cloud metadata endpoint accessible"
        
        return False, 0, "No SSRF indicator detected"
    
    def verify_lfi(self, payload: str, response_body: str, 
                   detection_pattern: str = None) -> Tuple[bool, int, str]:
        """
        Verify LFI via file content detection
        Returns: (signal_detected, confidence_delta, evidence)
        """
        if not response_body:
            return False, 0, "Empty response"
        
        # Check for /etc/passwd pattern
        if detection_pattern:
            if re.search(detection_pattern, response_body):
                return True, 25, f"LFI pattern matched: {detection_pattern[:50]}"
        
        # Common LFI indicators
        lfi_indicators = [
            (r'root:.*:0:0:', 25, '/etc/passwd content'),
            (r'\[extensions\]', 20, 'php.ini content'),
            (r'DAEMON\\\\CurrentVersion', 18, 'Windows registry'),
            (r'<\?php', 15, 'PHP source code')
        ]
        
        for pattern, confidence, description in lfi_indicators:
            if re.search(pattern, response_body, re.IGNORECASE):
                return True, confidence, f"LFI indicator: {description}"
        
        return False, 0, "No LFI indicator detected"
    
    def _get_reflection_context(self, payload: str, response_body: str, 
                                context_size: int = 50) -> str:
        """Get surrounding context of payload reflection"""
        index = response_body.find(payload)
        if index == -1:
            return ""
        
        start = max(0, index - context_size)
        end = min(len(response_body), index + len(payload) + context_size)
        
        return response_body[start:end]
    
    def detect_false_positive_signals(self, test_results: list) -> Tuple[bool, str]:
        """
        Detect false positive patterns
        Returns: (is_false_positive, reason)
        """
        if not test_results:
            return False, ""
        
        # All payloads reflect equally = likely echo endpoint
        if len(test_results) > 2:
            reflection_count = sum(1 for r in test_results if r.signal_detected)
            if reflection_count == len(test_results):
                return True, "All payloads reflect equally (echo endpoint)"
        
        # Response always same status regardless of payload
        statuses = [r.response_status for r in test_results if hasattr(r, 'response_status')]
        if len(set(statuses)) == 1 and len(statuses) > 2:
            return True, "Response status unchanged across all payloads"
        
        # Content length always identical
        lengths = []
        for r in test_results:
            if hasattr(r, 'response_body') and r.response_body:
                lengths.append(len(r.response_body))
        
        if len(set(lengths)) == 1 and len(lengths) > 2:
            return True, "Response length identical across all payloads"
        
        return False, ""