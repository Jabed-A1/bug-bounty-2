"""
Parameter Intelligence Engine
Detects data types, semantic roles, and attack surface
"""
import re
import logging
from typing import Dict, List, Set
from urllib.parse import urlparse, parse_qs
import json
from app import db
from app.models.recon import Endpoint
from app.models.intelligence import EndpointCluster, EndpointParameter

logger = logging.getLogger(__name__)


class ParameterAnalyzer:
    """
    Analyzes parameters to detect types and semantic roles
    Rule-based detection - no ML guessing
    """
    
    # Semantic role detection patterns
    ROLE_PATTERNS = {
        'identifier': [
            r'^(id|uid|user_?id|account_?id)$',
            r'^.*_id$',
            r'^pk$'
        ],
        'redirect': [
            r'^(redirect|return|next|callback|url|return_?url|continue)$',
            r'^.*_url$',
            r'^.*_redirect$'
        ],
        'file_path': [
            r'^(file|path|filename|filepath|dir|directory)$',
            r'^.*_file$',
            r'^.*_path$'
        ],
        'auth': [
            r'^(token|auth|api_?key|access_?token|session|csrf)$',
            r'^.*_token$',
            r'^.*_key$'
        ],
        'pagination': [
            r'^(page|offset|limit|per_?page|start|size)$'
        ],
        'search': [
            r'^(q|query|search|keyword|term)$'
        ],
        'filter': [
            r'^(filter|status|category|type|sort)$'
        ]
    }
    
    def __init__(self, target_id: int):
        self.target_id = target_id
        self.parameters_analyzed = 0
    
    def analyze_all_parameters(self) -> Dict:
        """
        Analyze parameters across all clusters
        """
        logger.info(f"Starting parameter analysis for target {self.target_id}")
        
        clusters = EndpointCluster.query.filter_by(target_id=self.target_id).all()
        
        for cluster in clusters:
            try:
                self._analyze_cluster_parameters(cluster)
            except Exception as e:
                logger.error(f"Error analyzing cluster {cluster.id}: {str(e)}")
        
        db.session.commit()
        
        logger.info(f"Parameter analysis complete: {self.parameters_analyzed} parameters")
        
        return {
            'clusters_analyzed': len(clusters),
            'parameters_analyzed': self.parameters_analyzed
        }
    
    def _analyze_cluster_parameters(self, cluster: EndpointCluster):
        """
        Analyze parameters for a specific cluster
        """
        # Get sample endpoints from this cluster
        endpoints = Endpoint.query.filter_by(target_id=self.target_id).all()
        
        # Filter endpoints that match this cluster's pattern
        matching_endpoints = [
            e for e in endpoints
            if self._matches_cluster(e, cluster)
        ]
        
        if not matching_endpoints:
            return
        
        # Collect all unique parameters
        param_data = {}
        
        for endpoint in matching_endpoints:
            params = self._extract_parameters(endpoint.url)
            
            for param_name, param_value in params.items():
                if param_name not in param_data:
                    param_data[param_name] = {
                        'values': [],
                        'positions': set()
                    }
                
                param_data[param_name]['values'].append(param_value)
                param_data[param_name]['positions'].add('query')
        
        # Analyze each parameter
        for param_name, data in param_data.items():
            self._create_parameter_intelligence(cluster, param_name, data['values'], list(data['positions']))
    
    def _matches_cluster(self, endpoint: Endpoint, cluster: EndpointCluster) -> bool:
        """
        Check if endpoint matches cluster pattern
        """
        from services.endpoint_normalizer import EndpointNormalizer
        
        normalizer = EndpointNormalizer(self.target_id)
        normalized = normalizer._normalize_path(endpoint.url)
        
        return (normalized == cluster.normalized_path and 
                endpoint.method == cluster.http_method)
    
    def _extract_parameters(self, url: str) -> Dict[str, str]:
        """
        Extract query parameters from URL
        """
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Flatten to first value only
        return {k: v[0] for k, v in params.items() if v}
    
    def _create_parameter_intelligence(self, cluster: EndpointCluster, 
                                      param_name: str, values: List[str], 
                                      positions: List[str]):
        """
        Create or update parameter intelligence record
        """
        existing = EndpointParameter.query.filter_by(
            cluster_id=cluster.id,
            parameter_name=param_name
        ).first()
        
        if existing:
            return
        
        # Detect data type
        data_type = self._detect_data_type(values)
        
        # Detect semantic role
        semantic_role, confidence = self._detect_semantic_role(param_name, values, data_type)
        
        # Store sample values (max 10)
        sample_values = list(set(values))[:10]
        
        param = EndpointParameter(
            cluster_id=cluster.id,
            parameter_name=param_name,
            data_type=data_type,
            semantic_role=semantic_role,
            confidence_score=confidence,
            sample_values=json.dumps(sample_values),
            position=','.join(positions)
        )
        
        db.session.add(param)
        self.parameters_analyzed += 1
    
    def _detect_data_type(self, values: List[str]) -> str:
        """
        Detect parameter data type from sample values
        """
        if not values:
            return 'unknown'
        
        # Check UUID
        uuid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        if all(uuid_pattern.match(str(v)) for v in values[:5]):
            return 'uuid'
        
        # Check integer
        try:
            if all(str(v).isdigit() for v in values[:5]):
                return 'int'
        except:
            pass
        
        # Check boolean
        bool_values = {'true', 'false', '1', '0', 'yes', 'no'}
        if all(str(v).lower() in bool_values for v in values[:5]):
            return 'bool'
        
        # Check email
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if all(email_pattern.match(str(v)) for v in values[:5]):
            return 'email'
        
        # Check URL
        url_pattern = re.compile(r'^https?://')
        if any(url_pattern.match(str(v)) for v in values[:5]):
            return 'url'
        
        return 'string'
    
    def _detect_semantic_role(self, param_name: str, values: List[str], 
                             data_type: str) -> Tuple[str, int]:
        """
        Detect semantic role of parameter
        Returns (role, confidence_score)
        """
        param_lower = param_name.lower()
        
        # Check against role patterns
        for role, patterns in self.ROLE_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, param_lower):
                    confidence = 90 if re.match(pattern + '$', param_lower) else 70
                    return role, confidence
        
        # Type-based inference
        if data_type == 'uuid' and 'id' in param_lower:
            return 'identifier', 80
        
        if data_type == 'int' and any(x in param_lower for x in ['id', 'num', 'count']):
            return 'identifier', 70
        
        if data_type == 'url':
            return 'redirect', 85
        
        return 'unknown', 0
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get parameter analysis statistics"""
        clusters = EndpointCluster.query.filter_by(target_id=target_id).all()
        cluster_ids = [c.id for c in clusters]
        
        total_params = EndpointParameter.query.filter(
            EndpointParameter.cluster_id.in_(cluster_ids)
        ).count()
        
        # Count by role
        role_counts = db.session.query(
            EndpointParameter.semantic_role,
            db.func.count(EndpointParameter.id)
        ).filter(
            EndpointParameter.cluster_id.in_(cluster_ids)
        ).group_by(
            EndpointParameter.semantic_role
        ).all()
        
        return {
            'total_parameters': total_params,
            'role_distribution': {role: count for role, count in role_counts}
        }