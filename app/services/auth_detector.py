"""
Auth Surface Detection Engine
Detects authentication requirements WITHOUT bypass attempts
"""
import logging
from typing import Dict
from app import db
from app.models.recon import LiveHost
from app.models.intelligence import EndpointCluster, AuthSurface
import json

logger = logging.getLogger(__name__)


class AuthDetector:
    """
    Detects authentication surfaces through passive analysis
    NO active testing or bypass attempts
    """
    
    # Status codes indicating auth requirement
    AUTH_STATUS_CODES = {401, 403, 302, 303, 307}
    
    # Headers indicating auth
    AUTH_HEADERS = {
        'www-authenticate',
        'authorization',
        'x-auth-token',
        'x-api-key'
    }
    
    def __init__(self, target_id: int):
        self.target_id = target_id
        self.surfaces_detected = 0
    
    def detect_auth_surfaces(self) -> Dict:
        """
        Detect authentication surfaces across all clusters
        """
        logger.info(f"Starting auth surface detection for target {self.target_id}")
        
        clusters = EndpointCluster.query.filter_by(target_id=self.target_id).all()
        
        for cluster in clusters:
            try:
                self._analyze_cluster_auth(cluster)
            except Exception as e:
                logger.error(f"Error detecting auth for cluster {cluster.id}: {str(e)}")
        
        db.session.commit()
        
        logger.info(f"Auth detection complete: {self.surfaces_detected} surfaces detected")
        
        return {
            'clusters_analyzed': len(clusters),
            'auth_surfaces_detected': self.surfaces_detected
        }
    
    def _analyze_cluster_auth(self, cluster: EndpointCluster):
        """
        Analyze authentication requirements for a cluster
        Uses existing Phase 2 data - NO new requests
        """
        # Check if already analyzed
        existing = AuthSurface.query.filter_by(cluster_id=cluster.id).first()
        if existing:
            return
        
        # Get live hosts that match this cluster pattern
        from app.models.recon import Subdomain
        subdomains = Subdomain.query.filter_by(target_id=self.target_id).all()
        subdomain_ids = [s.id for s in subdomains]
        
        live_hosts = LiveHost.query.filter(
            LiveHost.subdomain_id.in_(subdomain_ids)
        ).all()
        
        if not live_hosts:
            return
        
        # Analyze status codes and headers from Phase 2 data
        status_codes = [h.status_code for h in live_hosts if h.status_code]
        detected_headers = []
        
        # Check for auth indicators
        is_authenticated = self._infer_auth_requirement(status_codes, detected_headers)
        confidence = self._calculate_auth_confidence(status_codes, is_authenticated)
        
        # Detect auth type
        auth_type = self._detect_auth_type(status_codes, detected_headers)
        
        # Create auth surface record
        auth_surface = AuthSurface(
            cluster_id=cluster.id,
            is_authenticated=is_authenticated,
            auth_type=auth_type,
            status_code_authed=None,  # Would need active testing
            status_code_unauthed=status_codes[0] if status_codes else None,
            response_diff_score=0,
            confidence_score=confidence,
            detected_headers=json.dumps(detected_headers),
            analysis_method='passive_inference'
        )
        
        db.session.add(auth_surface)
        
        # Update cluster
        cluster.has_auth = is_authenticated
        
        self.surfaces_detected += 1
    
    def _infer_auth_requirement(self, status_codes: list, headers: list) -> bool:
        """
        Infer if endpoint requires authentication
        """
        if not status_codes:
            return None
        
        # Check status codes
        auth_codes_present = any(code in self.AUTH_STATUS_CODES for code in status_codes)
        
        # Check headers
        auth_headers_present = any(
            h.lower() in self.AUTH_HEADERS 
            for h in headers
        )
        
        if auth_codes_present or auth_headers_present:
            return True
        
        # Default to unknown
        return None
    
    def _calculate_auth_confidence(self, status_codes: list, is_authenticated: bool) -> int:
        """
        Calculate confidence in auth detection
        """
        if is_authenticated is None:
            return 0
        
        if not status_codes:
            return 0
        
        # High confidence for 401/403
        if any(code in {401, 403} for code in status_codes):
            return 90
        
        # Medium confidence for redirects
        if any(code in {302, 303, 307} for code in status_codes):
            return 60
        
        # Low confidence for 200
        if all(code == 200 for code in status_codes):
            return 30
        
        return 50
    
    def _detect_auth_type(self, status_codes: list, headers: list) -> str:
        """
        Detect authentication type from available data
        """
        # Check for 401 with WWW-Authenticate
        if 401 in status_codes:
            return 'basic_or_bearer'
        
        # Check for redirects (likely session-based)
        if any(code in {302, 303, 307} for code in status_codes):
            return 'session_based'
        
        # Check headers for API keys
        if any('api' in h.lower() for h in headers):
            return 'api_key'
        
        return 'unknown'
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get auth surface statistics"""
        clusters = EndpointCluster.query.filter_by(target_id=target_id).all()
        cluster_ids = [c.id for c in clusters]
        
        total = AuthSurface.query.filter(
            AuthSurface.cluster_id.in_(cluster_ids)
        ).count()
        
        authenticated = AuthSurface.query.filter(
            AuthSurface.cluster_id.in_(cluster_ids),
            AuthSurface.is_authenticated == True
        ).count()
        
        public = AuthSurface.query.filter(
            AuthSurface.cluster_id.in_(cluster_ids),
            AuthSurface.is_authenticated == False
        ).count()
        
        return {
            'total_analyzed': total,
            'authenticated_endpoints': authenticated,
            'public_endpoints': public,
            'unknown': total - authenticated - public
        }