"""
Phase 2: JavaScript Analysis Service
Extracts endpoints from JavaScript files
"""
import subprocess
import requests
import re
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse
from app import db
from app.models.recon import JSFile, Endpoint


logger = logging.getLogger(__name__)


class JSAnalyzer:
    """
    Analyze JavaScript files to extract hidden endpoints
    Finds API routes, fetch calls, XHR requests
    """
    
    def __init__(self, target):
        self.target = target
        self.patterns = self._compile_patterns()
    
    def analyze_all(self) -> Dict[str, any]:
        """
        Analyze all JS files for the target
        Returns: Dictionary with results and statistics
        """
        logger.info(f"Starting JS analysis for target {self.target.domain}")
        
        results = {
            'target_id': self.target.id,
            'js_files_analyzed': 0,
            'endpoints_extracted': 0,
            'files': []
        }
        
        # Get all unanalyzed JS files
        js_files = JSFile.query.filter_by(
            target_id=self.target.id,
            analyzed=False
        ).all()
        
        if not js_files:
            logger.info(f"No unanalyzed JS files found for target {self.target.id}")
            return results
        
        logger.info(f"Analyzing {len(js_files)} JS files")
        
        for js_file in js_files:
            try:
                analysis = self._analyze_js_file(js_file)
                if analysis:
                    results['js_files_analyzed'] += 1
                    results['endpoints_extracted'] += analysis['endpoints_found']
                    results['files'].append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing {js_file.url}: {str(e)}")
        
        logger.info(f"JS analysis complete: {results['js_files_analyzed']} files analyzed, "
                   f"{results['endpoints_extracted']} endpoints extracted")
        
        return results
    
    def _analyze_js_file(self, js_file: JSFile) -> Dict:
        """
        Analyze a single JS file
        Returns: Dictionary with extracted endpoints
        """
        logger.info(f"Analyzing JS file: {js_file.url}")
        
        result = {
            'js_file_id': js_file.id,
            'url': js_file.url,
            'endpoints_found': 0,
            'endpoints': []
        }
        
        try:
            # Download JS file content
            content = self._download_js_file(js_file.url)
            
            if not content:
                logger.warning(f"Failed to download {js_file.url}")
                js_file.analyzed = True
                db.session.commit()
                return result
            
            # Calculate content hash for deduplication
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            js_file.content_hash = content_hash
            
            # Check if we've already analyzed this content
            if self._is_duplicate_content(js_file.id, content_hash):
                logger.info(f"JS file {js_file.url} is duplicate, skipping analysis")
                js_file.analyzed = True
                db.session.commit()
                return result
            
            # Extract endpoints
            endpoints = self._extract_endpoints(content, js_file.url)
            
            # Save endpoints
            for endpoint_url in endpoints:
                if self._save_endpoint(endpoint_url, 'js_analysis'):
                    result['endpoints'].append(endpoint_url)
                    result['endpoints_found'] += 1
            
            # Update JS file status
            js_file.analyzed = True
            js_file.endpoints_found = result['endpoints_found']
            db.session.commit()
            
            logger.info(f"Extracted {result['endpoints_found']} endpoints from {js_file.url}")
        
        except Exception as e:
            logger.error(f"Error analyzing JS file {js_file.url}: {str(e)}")
            js_file.analyzed = True  # Mark as analyzed to avoid retry loops
            db.session.commit()
        
        return result
    
    def _download_js_file(self, url: str) -> str:
        """
        Download JS file content
        Returns: File content as string
        """
        try:
            response = requests.get(
                url,
                timeout=30,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; BugBountyBot/1.0; +security-research)'
                },
                verify=False  # In production, handle SSL properly
            )
            
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Failed to download {url}: HTTP {response.status_code}")
                return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error downloading {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return None
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """
        Compile regex patterns for endpoint extraction
        Returns: Dictionary of compiled patterns
        """
        return {
            # API endpoints
            'api_routes': re.compile(r'["\']/(api|v\d+)/[a-zA-Z0-9_/\-{}:]+["\']'),
            
            # fetch() calls
            'fetch': re.compile(r'fetch\s*\(\s*["\']([^"\']+)["\']'),
            
            # axios calls
            'axios': re.compile(r'axios\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'),
            
            # XMLHttpRequest
            'xhr': re.compile(r'\.open\s*\(\s*["\'](?:GET|POST|PUT|DELETE|PATCH)["\']\s*,\s*["\']([^"\']+)["\']'),
            
            # URL patterns
            'urls': re.compile(r'["\']https?://[^"\']+["\']'),
            
            # Relative paths that look like endpoints
            'relative': re.compile(r'["\']/([\w\-/]+\.(json|xml|txt|php|asp|aspx|jsp))["\']'),
            
            # GraphQL endpoints
            'graphql': re.compile(r'["\']/(graphql|gql)["\']'),
        }
    
    def _extract_endpoints(self, content: str, base_url: str) -> Set[str]:
        """
        Extract endpoints from JS content using patterns
        Returns: Set of discovered endpoint URLs
        """
        endpoints = set()
        
        # Apply each pattern
        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(content)
            
            for match in matches:
                # Handle different match types
                if isinstance(match, tuple):
                    # From patterns with groups (like axios)
                    endpoint = match[-1] if match else None
                else:
                    endpoint = match
                
                if endpoint:
                    # Clean the endpoint
                    endpoint = endpoint.strip('\'"')
                    
                    # Convert to absolute URL if relative
                    if endpoint.startswith('/'):
                        full_url = urljoin(base_url, endpoint)
                    elif endpoint.startswith('http'):
                        full_url = endpoint
                    else:
                        # Try to construct URL
                        full_url = urljoin(base_url, '/' + endpoint)
                    
                    # Validate and add
                    if self._is_valid_endpoint(full_url):
                        endpoints.add(full_url)
        
        return endpoints
    
    def _is_valid_endpoint(self, url: str) -> bool:
        """Check if extracted URL is a valid endpoint"""
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Must be in domain scope
            if not parsed.netloc.endswith(self.target.domain):
                return False
            
            # Skip static assets
            skip_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.css', '.woff', 
                             '.woff2', '.ttf', '.eot', '.ico', '.mp4', '.mp3']
            
            if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
                return False
            
            return True
        
        except Exception:
            return False
    
    def _is_duplicate_content(self, js_file_id: int, content_hash: str) -> bool:
        """Check if JS content has already been analyzed"""
        existing = JSFile.query.filter(
            JSFile.id != js_file_id,
            JSFile.target_id == self.target.id,
            JSFile.content_hash == content_hash,
            JSFile.analyzed == True
        ).first()
        
        return existing is not None
    
    def _save_endpoint(self, url: str, source: str) -> bool:
        """Save discovered endpoint to database"""
        try:
            import json
            from urllib.parse import parse_qs
            
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            existing = Endpoint.query.filter_by(
                target_id=self.target.id,
                url=url
            ).first()
            
            if existing:
                # Update source if different
                if source not in existing.source:
                    existing.source = f"{existing.source},{source}"
                db.session.commit()
                return False  # Not new
            else:
                # Create new
                new_endpoint = Endpoint(
                    target_id=self.target.id,
                    url=url,
                    method='GET',  # Default, could be enhanced
                    parameter_names=json.dumps(list(params.keys())),
                    has_params=bool(params),
                    source=source,
                    discovered_at=datetime.utcnow()
                )
                db.session.add(new_endpoint)
                db.session.commit()
                return True  # New
        
        except Exception as e:
            logger.error(f"Error saving endpoint {url}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get JS analysis statistics for a target"""
        total_js = JSFile.query.filter_by(target_id=target_id).count()
        analyzed_js = JSFile.query.filter_by(target_id=target_id, analyzed=True).count()
        
        # Count endpoints discovered from JS
        js_endpoints = Endpoint.query.filter(
            Endpoint.target_id == target_id,
            Endpoint.source.like('%js_analysis%')
        ).count()
        
        return {
            'total_js_files': total_js,
            'analyzed': analyzed_js,
            'unanalyzed': total_js - analyzed_js,
            'endpoints_from_js': js_endpoints
        }