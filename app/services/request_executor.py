"""
Phase 4: Safe Request Execution Engine
Rate-limited, scope-respecting HTTP client
"""
import requests
import time
import logging
from typing import Dict, Optional
from urllib.parse import urlparse, urlencode, parse_qs
import json

logger = logging.getLogger(__name__)


class RequestExecutor:
    """
    Safe HTTP request executor
    Respects rate limits, timeouts, and scope
    """
    
    def __init__(self, target, rate_limit: int = 10):
        self.target = target
        self.rate_limit = rate_limit
        self.request_interval = 1.0 / rate_limit
        self.last_request_time = 0
        self.timeout = 15
        self.max_redirects = 3
    
    def execute_test_request(self, url: str, method: str, 
                            parameter: str, payload: str,
                            headers: Dict = None) -> Dict:
        """
        Execute single test request with payload
        Returns complete request/response snapshot
        """
        # Rate limiting
        self._rate_limit()
        
        # Scope validation
        if not self._is_in_scope(url):
            raise ValueError(f"URL out of scope: {url}")
        
        start_time = time.time()
        
        try:
            # Inject payload
            test_url, test_data = self._inject_payload(url, method, parameter, payload)
            
            # Prepare headers
            request_headers = {
                'User-Agent': 'Security-Research-Bot/1.0 (+security-research)',
                'Accept': '*/*'
            }
            if headers:
                request_headers.update(headers)
            
            # Execute request
            if method.upper() == 'GET':
                response = requests.get(
                    test_url,
                    headers=request_headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=False
                )
            elif method.upper() == 'POST':
                response = requests.post(
                    test_url,
                    data=test_data,
                    headers=request_headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=False
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Build snapshot
            snapshot = {
                'request_url': test_url,
                'request_method': method,
                'request_headers': json.dumps(dict(request_headers)),
                'request_body': json.dumps(test_data) if test_data else None,
                'response_status': response.status_code,
                'response_headers': json.dumps(dict(response.headers)),
                'response_body': response.text[:50000],  # Limit to 50KB
                'response_time_ms': response_time_ms,
                'success': True
            }
            
            logger.debug(f"Request executed: {method} {test_url} -> {response.status_code}")
            
            return snapshot
        
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout: {url}")
            return {
                'request_url': url,
                'request_method': method,
                'success': False,
                'error': 'timeout'
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url} - {str(e)}")
            return {
                'request_url': url,
                'request_method': method,
                'success': False,
                'error': str(e)
            }
    
    def _inject_payload(self, url: str, method: str, 
                       parameter: str, payload: str):
        """Inject payload into parameter"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if method.upper() == 'GET':
            params[parameter] = [payload]
            new_query = urlencode(params, doseq=True)
            new_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
            return new_url, None
        
        elif method.upper() == 'POST':
            data = {parameter: payload}
            return url, data
        
        return url, None
    
    def _is_in_scope(self, url: str) -> bool:
        """Validate URL is in target scope"""
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Must end with target domain
        if not domain.endswith(self.target.domain):
            logger.warning(f"URL out of scope: {url}")
            return False
        
        # Check scope rules if available
        if hasattr(self.target, 'scope_rules') and self.target.scope_rules:
            scope_rules = json.loads(self.target.scope_rules) if isinstance(self.target.scope_rules, str) else self.target.scope_rules
            
            # Check exclusions
            if 'out_of_scope' in scope_rules:
                for excluded in scope_rules['out_of_scope']:
                    if domain == excluded or domain.endswith('.' + excluded):
                        logger.warning(f"URL excluded by scope: {url}")
                        return False
        
        return True
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()