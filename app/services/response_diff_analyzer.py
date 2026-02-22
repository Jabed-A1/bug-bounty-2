"""
Response Differential Analysis
Detects suspicious variations for IDOR and business logic flaws
"""
import logging
import hashlib
from typing import Dict, List
from app import db
from app.models.recon import Endpoint
from app.models.intelligence import EndpointCluster, ResponseDiff

logger = logging.getLogger(__name__)


class ResponseDiffAnalyzer:
    """
    Analyzes response differences across similar endpoints
    Prepares data for IDOR testing - NO active testing
    """
    
    def __init__(self, target_id: int):
        self.target_id = target_id
        self.diffs_recorded = 0
    
    def analyze_response_diffs(self) -> Dict:
        """
        Analyze response differences across clusters
        """
        logger.info(f"Starting response diff analysis for target {self.target_id}")
        
        clusters = EndpointCluster.query.filter_by(target_id=self.target_id).all()
        
        for cluster in clusters:
            try:
                self._analyze_cluster_diffs(cluster)
            except Exception as e:
                logger.error(f"Error analyzing diffs for cluster {cluster.id}: {str(e)}")
        
        db.session.commit()
        
        logger.info(f"Response diff analysis complete: {self.diffs_recorded} diffs recorded")
        
        return {
            'clusters_analyzed': len(clusters),
            'diffs_recorded': self.diffs_recorded
        }
    
    def _analyze_cluster_diffs(self, cluster: EndpointCluster):
        """
        Analyze response differences within a cluster
        """
        # Get endpoints matching this cluster
        endpoints = Endpoint.query.filter_by(target_id=self.target_id).all()
        
        # Filter to matching pattern
        from services.endpoint_normalizer import EndpointNormalizer
        normalizer = EndpointNormalizer(self.target_id)
        
        matching = []
        for endpoint in endpoints:
            if normalizer._normalize_path(endpoint.url) == cluster.normalized_path:
                matching.append(endpoint)
        
        if len(matching) < 2:
            return
        
        # Compare pairs
        for i in range(len(matching) - 1):
            endpoint_a = matching[i]
            endpoint_b = matching[i + 1]
            
            self._compare_endpoints(cluster, endpoint_a, endpoint_b)
    
    def _compare_endpoints(self, cluster: EndpointCluster, 
                          endpoint_a: Endpoint, endpoint_b: Endpoint):
        """
        Compare two endpoints and record significant differences
        """
        # Check if already compared
        existing = ResponseDiff.query.filter(
            ResponseDiff.cluster_id == cluster.id,
            db.or_(
                db.and_(
                    ResponseDiff.endpoint_a == endpoint_a.url,
                    ResponseDiff.endpoint_b == endpoint_b.url
                ),
                db.and_(
                    ResponseDiff.endpoint_a == endpoint_b.url,
                    ResponseDiff.endpoint_b == endpoint_a.url
                )
            )
        ).first()
        
        if existing:
            return
        
        # For now, we don't have actual response data
        # This would be populated during Phase 4 active testing
        # We create placeholder records for suspicious patterns
        
        # Check if endpoints have different IDs (potential IDOR)
        id_diff = self._extract_id_difference(endpoint_a.url, endpoint_b.url)
        
        if not id_diff:
            return
        
        # Create diff record
        diff = ResponseDiff(
            cluster_id=cluster.id,
            endpoint_a=endpoint_a.url,
            endpoint_b=endpoint_b.url,
            status_diff=False,
            length_diff=0,
            length_diff_percent=0.0,
            hash_a=None,
            hash_b=None,
            suspicious=True,
            diff_type='id_variation',
            notes=f"Endpoints differ by ID parameter: {id_diff}"
        )
        
        db.session.add(diff)
        self.diffs_recorded += 1
    
    def _extract_id_difference(self, url_a: str, url_b: str) -> str:
        """
        Extract ID differences between URLs
        """
        import re
        
        # Extract numeric IDs
        ids_a = re.findall(r'/(\d+)(?:/|$)', url_a)
        ids_b = re.findall(r'/(\d+)(?:/|$)', url_b)
        
        if ids_a and ids_b and ids_a != ids_b:
            return f"{ids_a[0]} vs {ids_b[0]}"
        
        return None
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get response diff statistics"""
        clusters = EndpointCluster.query.filter_by(target_id=target_id).all()
        cluster_ids = [c.id for c in clusters]
        
        total = ResponseDiff.query.filter(
            ResponseDiff.cluster_id.in_(cluster_ids)
        ).count()
        
        suspicious = ResponseDiff.query.filter(
            ResponseDiff.cluster_id.in_(cluster_ids),
            ResponseDiff.suspicious == True
        ).count()
        
        return {
            'total_diffs': total,
            'suspicious_diffs': suspicious
        }