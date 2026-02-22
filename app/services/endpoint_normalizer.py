"""
Endpoint Normalization and Clustering Engine
Converts /user/123, /user/456 → /user/{id}
"""
import re
import hashlib
import logging
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Tuple
from app import db
from app.models.recon import Endpoint
from app.models.intelligence import EndpointCluster

logger = logging.getLogger(__name__)


class EndpointNormalizer:
    """
    Normalizes endpoints into clusters for intelligence analysis
    """
    
    # Regex patterns for normalization
    UUID_PATTERN = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
    NUMERIC_ID_PATTERN = re.compile(r'/\d+(?=/|$)')
    HEX_ID_PATTERN = re.compile(r'/[0-9a-fA-F]{24,}(?=/|$)')
    HASH_PATTERN = re.compile(r'/[0-9a-f]{32,64}(?=/|$)')
    
    def __init__(self, target_id: int):
        self.target_id = target_id
        self.clusters_created = 0
        self.endpoints_processed = 0
    
    def normalize_and_cluster(self) -> Dict:
        """
        Main entry point: normalize all endpoints and create clusters
        """
        logger.info(f"Starting endpoint normalization for target {self.target_id}")
        
        endpoints = Endpoint.query.filter_by(target_id=self.target_id).all()
        
        if not endpoints:
            logger.warning(f"No endpoints found for target {self.target_id}")
            return {'endpoints_processed': 0, 'clusters_created': 0}
        
        cluster_map = {}
        
        for endpoint in endpoints:
            try:
                normalized = self._normalize_path(endpoint.url)
                method = endpoint.method or 'GET'
                param_sig = self._generate_parameter_signature(endpoint)
                
                cluster_key = (normalized, method, param_sig)
                
                if cluster_key not in cluster_map:
                    cluster = self._create_or_get_cluster(normalized, method, param_sig)
                    cluster_map[cluster_key] = cluster
                else:
                    cluster = cluster_map[cluster_key]
                
                cluster.endpoint_count += 1
                self.endpoints_processed += 1
                
            except Exception as e:
                logger.error(f"Error normalizing endpoint {endpoint.url}: {str(e)}")
        
        db.session.commit()
        
        logger.info(f"Normalization complete: {self.endpoints_processed} endpoints, "
                   f"{len(cluster_map)} clusters")
        
        return {
            'endpoints_processed': self.endpoints_processed,
            'clusters_created': len(cluster_map)
        }
    
    def _normalize_path(self, url: str) -> str:
        """
        Normalize URL path by replacing dynamic segments
        """
        parsed = urlparse(url)
        path = parsed.path
        
        # Replace UUIDs
        path = self.UUID_PATTERN.sub('/{uuid}', path)
        
        # Replace hex IDs (MongoDB ObjectId, etc)
        path = self.HEX_ID_PATTERN.sub('/{hex_id}', path)
        
        # Replace hash values
        path = self.HASH_PATTERN.sub('/{hash}', path)
        
        # Replace numeric IDs
        path = self.NUMERIC_ID_PATTERN.sub('/{id}', path)
        
        # Normalize trailing slash
        if path != '/' and path.endswith('/'):
            path = path[:-1]
        
        return path or '/'
    
    def _generate_parameter_signature(self, endpoint: Endpoint) -> str:
        """
        Generate signature from parameter names (order-independent)
        """
        try:
            import json
            param_names = json.loads(endpoint.parameter_names) if endpoint.parameter_names else []
            
            if not param_names:
                return 'no_params'
            
            sorted_params = sorted(param_names)
            sig_string = ','.join(sorted_params)
            
            return hashlib.md5(sig_string.encode()).hexdigest()[:16]
            
        except Exception as e:
            logger.error(f"Error generating parameter signature: {str(e)}")
            return 'unknown'
    
    def _create_or_get_cluster(self, normalized_path: str, method: str, param_sig: str) -> EndpointCluster:
        """
        Create or retrieve existing cluster
        """
        cluster = EndpointCluster.query.filter_by(
            target_id=self.target_id,
            normalized_path=normalized_path,
            http_method=method,
            parameter_signature=param_sig
        ).first()
        
        if not cluster:
            cluster = EndpointCluster(
                target_id=self.target_id,
                normalized_path=normalized_path,
                http_method=method,
                parameter_signature=param_sig,
                endpoint_count=0
            )
            db.session.add(cluster)
            db.session.flush()
            self.clusters_created += 1
        
        return cluster
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get clustering statistics"""
        total_clusters = EndpointCluster.query.filter_by(target_id=target_id).count()
        
        clusters_with_params = EndpointCluster.query.filter(
            EndpointCluster.target_id == target_id,
            EndpointCluster.parameter_signature != 'no_params'
        ).count()
        
        total_endpoints = Endpoint.query.filter_by(target_id=target_id).count()
        
        return {
            'total_clusters': total_clusters,
            'clusters_with_params': clusters_with_params,
            'total_endpoints': total_endpoints,
            'avg_endpoints_per_cluster': total_endpoints / total_clusters if total_clusters > 0 else 0
        }