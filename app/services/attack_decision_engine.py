"""
Attack Decision Engine
Rule-based attack candidate generation - NO EXECUTION
"""
import logging
from typing import Dict, List
import json
from app import db
from app.models.intelligence import EndpointCluster, EndpointParameter, AttackCandidate

logger = logging.getLogger(__name__)


class AttackDecisionEngine:
    """
    Generates attack candidates based on endpoint intelligence
    DECISION ONLY - no payload generation or execution
    """
    
    def __init__(self, target_id: int):
        self.target_id = target_id
        self.candidates_generated = 0
    
    def generate_all_candidates(self) -> Dict:
        """
        Generate attack candidates for all clusters
        """
        logger.info(f"Generating attack candidates for target {self.target_id}")
        
        clusters = EndpointCluster.query.filter_by(target_id=self.target_id).all()
        
        for cluster in clusters:
            try:
                self._analyze_cluster_for_attacks(cluster)
            except Exception as e:
                logger.error(f"Error analyzing cluster {cluster.id}: {str(e)}")
        
        db.session.commit()
        
        logger.info(f"Attack candidate generation complete: {self.candidates_generated} candidates")
        
        return {
            'clusters_analyzed': len(clusters),
            'candidates_generated': self.candidates_generated
        }
    
    def _analyze_cluster_for_attacks(self, cluster: EndpointCluster):
        """
        Analyze single cluster for attack opportunities
        """
        parameters = cluster.parameters.all()
        
        # XSS candidates
        self._check_xss_eligibility(cluster, parameters)
        
        # SQLi candidates
        self._check_sqli_eligibility(cluster, parameters)
        
        # IDOR candidates
        self._check_idor_eligibility(cluster, parameters)
        
        # Open Redirect candidates
        self._check_redirect_eligibility(cluster, parameters)
        
        # SSRF candidates
        self._check_ssrf_eligibility(cluster, parameters)
        
        # LFI candidates
        self._check_lfi_eligibility(cluster, parameters)
        
        # Auth bypass candidates
        self._check_auth_bypass_eligibility(cluster, parameters)
        
        # Business logic candidates
        self._check_business_logic_eligibility(cluster, parameters)
    
    def _check_xss_eligibility(self, cluster: EndpointCluster, parameters: List[EndpointParameter]):
        """
        Check if XSS testing is eligible
        """
        # Look for reflected parameters
        string_params = [p for p in parameters if p.data_type == 'string']
        
        if not string_params:
            return
        
        # Exclude known safe roles
        safe_roles = {'auth', 'pagination'}
        vulnerable_params = [
            p for p in string_params 
            if p.semantic_role not in safe_roles
        ]
        
        if not vulnerable_params:
            return
        
        param_names = [p.parameter_name for p in vulnerable_params]
        
        reasoning = (
            f"Cluster has {len(vulnerable_params)} string parameters that may reflect user input: "
            f"{', '.join(param_names)}. "
            f"XSS testing recommended on these parameters."
        )
        
        self._create_candidate(
            cluster=cluster,
            attack_type='XSS',
            risk_level='medium',
            reasoning=reasoning,
            affected_params=param_names,
            confidence=60
        )
    
    def _check_sqli_eligibility(self, cluster: EndpointCluster, parameters: List[EndpointParameter]):
        """
        Check if SQLi testing is eligible
        """
        # Look for identifier parameters
        id_params = [p for p in parameters if p.semantic_role == 'identifier']
        
        if not id_params:
            return
        
        param_names = [p.parameter_name for p in id_params]
        
        reasoning = (
            f"Cluster has {len(id_params)} identifier parameters used in database queries: "
            f"{', '.join(param_names)}. "
            f"SQL injection testing recommended."
        )
        
        self._create_candidate(
            cluster=cluster,
            attack_type='SQLi',
            risk_level='high',
            reasoning=reasoning,
            affected_params=param_names,
            confidence=70
        )
    
    def _check_idor_eligibility(self, cluster: EndpointCluster, parameters: List[EndpointParameter]):
        """
        Check if IDOR testing is eligible
        """
        # Look for identifier parameters on authenticated endpoints
        id_params = [p for p in parameters if p.semantic_role == 'identifier']
        
        if not id_params:
            return
        
        # Higher confidence if auth surface detected
        confidence = 75 if cluster.has_auth else 50
        risk = 'high' if cluster.has_auth else 'medium'
        
        param_names = [p.parameter_name for p in id_params]
        
        reasoning = (
            f"Cluster contains identifier parameters: {', '.join(param_names)}. "
        )
        
        if cluster.has_auth:
            reasoning += "Endpoint requires authentication. "
        
        reasoning += "IDOR testing recommended to check for insecure direct object references."
        
        self._create_candidate(
            cluster=cluster,
            attack_type='IDOR',
            risk_level=risk,
            reasoning=reasoning,
            affected_params=param_names,
            confidence=confidence
        )
    
    def _check_redirect_eligibility(self, cluster: EndpointCluster, parameters: List[EndpointParameter]):
        """
        Check if Open Redirect testing is eligible
        """
        redirect_params = [p for p in parameters if p.semantic_role == 'redirect']
        url_params = [p for p in parameters if p.data_type == 'url']
        
        candidates = redirect_params + url_params
        
        if not candidates:
            return
        
        param_names = list(set([p.parameter_name for p in candidates]))
        
        reasoning = (
            f"Cluster has {len(param_names)} redirect/URL parameters: "
            f"{', '.join(param_names)}. "
            f"Open redirect testing recommended."
        )
        
        self._create_candidate(
            cluster=cluster,
            attack_type='Open Redirect',
            risk_level='medium',
            reasoning=reasoning,
            affected_params=param_names,
            confidence=80
        )
    
    def _check_ssrf_eligibility(self, cluster: EndpointCluster, parameters: List[EndpointParameter]):
        """
        Check if SSRF testing is eligible
        """
        # Look for URL parameters
        url_params = [p for p in parameters if p.data_type == 'url']
        
        # Look for parameters that might fetch remote resources
        fetch_params = [
            p for p in parameters 
            if any(keyword in p.parameter_name.lower() for keyword in ['url', 'uri', 'link', 'fetch', 'proxy'])
        ]
        
        candidates = list(set(url_params + fetch_params))
        
        if not candidates:
            return
        
        param_names = [p.parameter_name for p in candidates]
        
        reasoning = (
            f"Cluster has parameters that may trigger server-side requests: "
            f"{', '.join(param_names)}. "
            f"SSRF testing recommended."
        )
        
        self._create_candidate(
            cluster=cluster,
            attack_type='SSRF',
            risk_level='high',
            reasoning=reasoning,
            affected_params=param_names,
            confidence=65
        )
    
    def _check_lfi_eligibility(self, cluster: EndpointCluster, parameters: List[EndpointParameter]):
        """
        Check if LFI testing is eligible
        """
        file_params = [p for p in parameters if p.semantic_role == 'file_path']
        
        if not file_params:
            return
        
        param_names = [p.parameter_name for p in file_params]
        
        reasoning = (
            f"Cluster has file/path parameters: {', '.join(param_names)}. "
            f"Local file inclusion testing recommended."
        )
        
        self._create_candidate(
            cluster=cluster,
            attack_type='LFI',
            risk_level='high',
            reasoning=reasoning,
            affected_params=param_names,
            confidence=70
        )
    
    def _check_auth_bypass_eligibility(self, cluster: EndpointCluster, parameters: List[EndpointParameter]):
        """
        Check if auth bypass testing is eligible
        """
        if cluster.has_auth is not True:
            return
        
        auth_params = [p for p in parameters if p.semantic_role == 'auth']
        
        param_names = [p.parameter_name for p in auth_params] if auth_params else []
        
        reasoning = (
            f"Cluster requires authentication. "
            f"Auth bypass testing recommended via method tampering, header manipulation, "
            f"and parameter pollution."
        )
        
        if auth_params:
            reasoning += f" Auth parameters detected: {', '.join(param_names)}."
        
        self._create_candidate(
            cluster=cluster,
            attack_type='Auth Bypass',
            risk_level='critical',
            reasoning=reasoning,
            affected_params=param_names,
            confidence=55
        )
    
    def _check_business_logic_eligibility(self, cluster: EndpointCluster, parameters: List[EndpointParameter]):
        """
        Check if business logic testing is eligible
        """
        # Look for clusters with multiple parameters of interest
        interesting_params = [
            p for p in parameters 
            if p.semantic_role in {'identifier', 'pagination', 'filter'}
        ]
        
        if len(interesting_params) < 2:
            return
        
        param_names = [p.parameter_name for p in interesting_params]
        
        reasoning = (
            f"Cluster has {len(interesting_params)} parameters that may enable "
            f"business logic manipulation: {', '.join(param_names)}. "
            f"Testing recommended for race conditions, parameter tampering, "
            f"and workflow bypass."
        )
        
        self._create_candidate(
            cluster=cluster,
            attack_type='Business Logic',
            risk_level='medium',
            reasoning=reasoning,
            affected_params=param_names,
            confidence=40
        )
    
    def _create_candidate(self, cluster: EndpointCluster, attack_type: str,
                         risk_level: str, reasoning: str, 
                         affected_params: List[str], confidence: int):
        """
        Create attack candidate record
        """
        # Check if similar candidate already exists
        existing = AttackCandidate.query.filter_by(
            cluster_id=cluster.id,
            attack_type=attack_type
        ).first()
        
        if existing:
            return
        
        candidate = AttackCandidate(
            cluster_id=cluster.id,
            target_id=self.target_id,
            attack_type=attack_type,
            risk_level=risk_level,
            reasoning=reasoning,
            affected_parameters=json.dumps(affected_params),
            confidence_score=confidence,
            auto_generated=True,
            reviewed=False
        )
        
        db.session.add(candidate)
        self.candidates_generated += 1
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get attack candidate statistics"""
        total = AttackCandidate.query.filter_by(target_id=target_id).count()
        reviewed = AttackCandidate.query.filter_by(target_id=target_id, reviewed=True).count()
        approved = AttackCandidate.query.filter_by(target_id=target_id, approved_for_testing=True).count()
        
        # Count by type
        type_counts = db.session.query(
            AttackCandidate.attack_type,
            db.func.count(AttackCandidate.id)
        ).filter(
            AttackCandidate.target_id == target_id
        ).group_by(
            AttackCandidate.attack_type
        ).all()
        
        # Count by risk
        risk_counts = db.session.query(
            AttackCandidate.risk_level,
            db.func.count(AttackCandidate.id)
        ).filter(
            AttackCandidate.target_id == target_id
        ).group_by(
            AttackCandidate.risk_level
        ).all()
        
        return {
            'total': total,
            'reviewed': reviewed,
            'approved': approved,
            'pending_review': total - reviewed,
            'by_type': {attack_type: count for attack_type, count in type_counts},
            'by_risk': {risk: count for risk, count in risk_counts}
        }