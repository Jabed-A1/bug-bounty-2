"""
Phase 4: Testing Orchestrator
Coordinates test execution and result processing
"""
import logging
from typing import Dict, List
from app import db
from app.models.intelligence import AttackCandidate
from app.models.testing import TestJob, TestResult, VerifiedFinding, TestJobFeedback, Payload
from services.payload_library import PayloadLibrary
from services.request_executor import RequestExecutor
from services.response_verifier import ResponseVerifier
from services.confidence_scorer import ConfidenceScorer
import json

logger = logging.getLogger(__name__)


class TestingOrchestrator:
    """
    Orchestrates end-to-end testing workflow
    Converts AttackCandidates to VerifiedFindings
    """
    
    def __init__(self, target):
        self.target = target
        self.executor = RequestExecutor(target)
        self.verifier = ResponseVerifier()
        self.scorer = ConfidenceScorer()
    
    def execute_test_job(self, candidate: AttackCandidate) -> TestJob:
        """
        Execute complete test job for attack candidate
        Returns TestJob with results
        """
        logger.info(f"Starting test job for candidate {candidate.id}")
        
        # Create test job
        test_job = TestJob(
            candidate_id=candidate.id,
            target_id=self.target.id,
            status='CREATED'
        )
        db.session.add(test_job)
        db.session.commit()
        
        try:
            # Transition to RUNNING
            test_job.transition_to('RUNNING')
            db.session.commit()
            
            # Get cluster and parameters
            cluster = candidate.cluster
            if not cluster:
                raise ValueError("Candidate has no associated cluster")
            
            # Get payloads
            payloads = PayloadLibrary.get_payloads_for_attack_type(candidate.attack_type)
            if not payloads:
                raise ValueError(f"No payloads found for {candidate.attack_type}")
            
            # Get affected parameters
            affected_params = json.loads(candidate.affected_parameters) if candidate.affected_parameters else []
            if not affected_params:
                affected_params = ['id']  # Default parameter
            
            primary_param = affected_params[0]
            
            # Execute tests
            test_results = []
            baseline_response = None
            
            for payload in payloads[:5]:  # Limit to 5 payloads per job
                try:
                    # Build test URL from cluster
                    test_url = self._build_test_url(cluster, primary_param)
                    
                    # Execute request
                    response_snapshot = self.executor.execute_test_request(
                        url=test_url,
                        method=cluster.http_method,
                        parameter=primary_param,
                        payload=payload.payload_string
                    )
                    
                    if not response_snapshot.get('success'):
                        logger.warning(f"Request failed for payload {payload.id}")
                        continue
                    
                    # Verify response
                    signal_detected, confidence_delta, evidence = self._verify_response(
                        candidate.attack_type,
                        payload,
                        response_snapshot,
                        baseline_response
                    )
                    
                    # Create test result
                    test_result = TestResult(
                        test_job_id=test_job.id,
                        payload_id=payload.id,
                        request_url=response_snapshot['request_url'],
                        request_method=response_snapshot['request_method'],
                        request_headers=response_snapshot.get('request_headers'),
                        request_body=response_snapshot.get('request_body'),
                        response_status=response_snapshot.get('response_status'),
                        response_headers=response_snapshot.get('response_headers'),
                        response_body=response_snapshot.get('response_body'),
                        response_time_ms=response_snapshot.get('response_time_ms'),
                        signal_detected=signal_detected,
                        signal_type=payload.payload_type if signal_detected else None,
                        signal_evidence=evidence,
                        confidence_delta=confidence_delta if signal_detected else 0
                    )
                    
                    db.session.add(test_result)
                    test_results.append(test_result)
                    
                    # Store baseline for IDOR comparison
                    if not baseline_response and candidate.attack_type == 'IDOR':
                        baseline_response = response_snapshot
                    
                    test_job.payloads_tested += 1
                    if signal_detected:
                        test_job.signals_detected += 1
                
                except Exception as e:
                    logger.error(f"Payload execution error: {str(e)}")
                    continue
            
            db.session.commit()
            
            # Calculate confidence score
            confidence_score, explanation = self.scorer.calculate_score(
                test_results,
                candidate.attack_type
            )
            
            test_job.confidence_score = confidence_score
            
            # Check for false positives
            is_fp, fp_reason = self.verifier.detect_false_positive_signals(test_results)
            if is_fp:
                confidence_score, fp_explanation = self.scorer.apply_false_positive_penalty(
                    confidence_score,
                    {'is_echo_endpoint': 'echo' in fp_reason.lower()}
                )
                test_job.confidence_score = confidence_score
                explanation += f"; {fp_explanation}"
            
            # Store execution metadata
            test_job.execution_metadata = json.dumps({
                'explanation': explanation,
                'false_positive_check': fp_reason if is_fp else None
            })
            
            # Determine outcome
            category = self.scorer.categorize_confidence(confidence_score)
            
            if category == 'verified':
                # Create verified finding
                self._create_verified_finding(test_job, candidate, test_results)
                test_job.transition_to('VERIFIED')
            else:
                test_job.transition_to('FAILED')
            
            # Create feedback for Phase 3
            self._create_feedback(test_job, candidate, category)
            
            db.session.commit()
            
            logger.info(f"Test job {test_job.id} completed: {test_job.status} (confidence: {confidence_score})")
            
            return test_job
        
        except Exception as e:
            logger.error(f"Test job failed: {str(e)}")
            test_job.transition_to('FAILED', str(e))
            db.session.commit()
            raise
    
    def _build_test_url(self, cluster, parameter: str) -> str:
        """Build test URL from cluster pattern"""
        # Get a sample endpoint from the cluster
        from app.models.recon import Endpoint
        
        sample_endpoint = Endpoint.query.filter_by(
            target_id=self.target.id
        ).filter(
            Endpoint.url.like(f"%{cluster.normalized_path.replace('{id}', '%')}%")
        ).first()
        
        if sample_endpoint:
            return sample_endpoint.url
        
        # Fallback: construct from cluster pattern
        domain = self.target.domain
        path = cluster.normalized_path.replace('{id}', '1').replace('{uuid}', 'test')
        return f"https://{domain}{path}?{parameter}=test"
    
    def _verify_response(self, attack_type: str, payload: Payload,
                        response_snapshot: Dict, baseline_response: Dict = None):
        """Route to appropriate verifier"""
        if attack_type == 'XSS':
            return self.verifier.verify_xss(
                payload.payload_string,
                response_snapshot.get('response_body', ''),
                payload.detection_pattern
            )
        
        elif attack_type == 'SQLi':
            return self.verifier.verify_sqli(
                payload.payload_string,
                response_snapshot.get('response_body', ''),
                response_snapshot.get('response_status', 0)
            )
        
        elif attack_type == 'IDOR' and baseline_response:
            return self.verifier.verify_idor(
                baseline_response,
                response_snapshot
            )
        
        elif attack_type == 'Open Redirect':
            headers = json.loads(response_snapshot.get('response_headers', '{}'))
            return self.verifier.verify_open_redirect(
                payload.payload_string,
                headers,
                response_snapshot.get('response_status', 0)
            )
        
        elif attack_type == 'SSRF':
            return self.verifier.verify_ssrf(
                payload.payload_string,
                response_snapshot.get('response_status', 0),
                response_snapshot.get('response_time_ms', 0),
                response_snapshot.get('response_body', '')
            )
        
        elif attack_type == 'LFI':
            return self.verifier.verify_lfi(
                payload.payload_string,
                response_snapshot.get('response_body', ''),
                payload.detection_pattern
            )
        
        return False, 0, "Verification not implemented for this attack type"
    
    def _create_verified_finding(self, test_job: TestJob, candidate: AttackCandidate,
                                test_results: List[TestResult]):
        """Create VerifiedFinding record"""
        # Get best test result
        best_result = max(test_results, key=lambda r: r.confidence_delta)
        
        # Calculate severity
        severity = self.scorer.calculate_severity(
            candidate.attack_type,
            test_job.confidence_score
        )
        
        # Build proof of concept
        poc = self._build_proof_of_concept(best_result, test_results)
        
        # Build evidence
        evidence = self._build_evidence(test_results)
        
        finding = VerifiedFinding(
            test_job_id=test_job.id,
            target_id=self.target.id,
            attack_type=candidate.attack_type,
            severity=severity,
            confidence_score=test_job.confidence_score,
            endpoint_url=best_result.request_url,
            vulnerable_parameter=self._extract_parameter_from_url(best_result.request_url),
            payload_used=best_result.payload.payload_string,
            proof_of_concept=poc,
            evidence=evidence,
            reasoning=candidate.reasoning,
            reproduction_steps=self._build_reproduction_steps(best_result),
            false_positive_probability=self._calculate_fp_probability(test_job.confidence_score)
        )
        
        db.session.add(finding)
    
    def _build_proof_of_concept(self, best_result: TestResult, all_results: List[TestResult]) -> str:
        """Build PoC string"""
        poc_lines = [
            f"Attack Type: {best_result.test_job.candidate.attack_type}",
            f"Endpoint: {best_result.request_url}",
            f"Method: {best_result.request_method}",
            f"Payload: {best_result.payload.payload_string}",
            f"",
            f"Response Status: {best_result.response_status}",
            f"Signal Detected: {best_result.signal_type}",
            f"Evidence: {best_result.signal_evidence}",
            f"",
            f"Signals from {len([r for r in all_results if r.signal_detected])}/{len(all_results)} payloads"
        ]
        
        return "\n".join(poc_lines)
    
    def _build_evidence(self, test_results: List[TestResult]) -> str:
        """Build evidence summary"""
        evidence_items = []
        
        for result in test_results:
            if result.signal_detected:
                evidence_items.append(
                    f"[{result.payload.payload_type}] {result.signal_evidence}"
                )
        
        return "\n".join(evidence_items)
    
    def _build_reproduction_steps(self, test_result: TestResult) -> str:
        """Build reproduction steps"""
        steps = [
            f"1. Navigate to: {test_result.request_url}",
            f"2. Use HTTP method: {test_result.request_method}",
            f"3. Include payload: {test_result.payload.payload_string}",
            f"4. Observe response for: {test_result.signal_type}"
        ]
        
        return "\n".join(steps)
    
    def _extract_parameter_from_url(self, url: str) -> str:
        """Extract parameter name from URL"""
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if params:
            return list(params.keys())[0]
        
        return "unknown"
    
    def _calculate_fp_probability(self, confidence_score: int) -> int:
        """Calculate false positive probability (inverse of confidence)"""
        return max(0, 100 - confidence_score)
    
    def _create_feedback(self, test_job: TestJob, candidate: AttackCandidate, category: str):
        """Create feedback for Phase 3"""
        feedback = TestJobFeedback(
            test_job_id=test_job.id,
            candidate_id=candidate.id,
            outcome=category,
            confidence_score=test_job.confidence_score,
            false_positive=category == 'discard',
            reasoning=json.loads(test_job.execution_metadata).get('explanation', ''),
            adjustments_suggested=self._suggest_adjustments(test_job, candidate)
        )
        
        db.session.add(feedback)
    
    def _suggest_adjustments(self, test_job: TestJob, candidate: AttackCandidate) -> str:
        """Suggest improvements for Phase 3"""
        suggestions = []
        
        if test_job.confidence_score < 40:
            suggestions.append("Low confidence - consider excluding similar patterns")
        
        if test_job.signals_detected == 0:
            suggestions.append("No signals detected - endpoint may not be vulnerable")
        
        if test_job.payloads_tested < 3:
            suggestions.append("Few payloads tested - may need more diverse payload library")
        
        return "; ".join(suggestions) if suggestions else "No adjustments suggested"