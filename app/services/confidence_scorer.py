"""
Phase 4: Confidence Scoring Engine
Cumulative scoring with explainable results
"""
import logging
from typing import List, Dict, Tuple
from app.models.testing import TestResult

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Calculates confidence scores based on test signals
    Scores: 0-100
    Thresholds: <40 discard, 40-69 review, >=70 verified
    """
    
    # Base confidence by attack type
    BASE_CONFIDENCE = {
        'XSS': 30,
        'SQLi': 35,
        'IDOR': 25,
        'Open Redirect': 30,
        'SSRF': 28,
        'LFI': 32,
        'Auth Bypass': 20,
        'Business Logic': 15
    }
    
    def calculate_score(self, test_results: List[TestResult], 
                       attack_type: str) -> Tuple[int, str]:
        """
        Calculate final confidence score
        Returns: (score, explanation)
        """
        base_score = self.BASE_CONFIDENCE.get(attack_type, 25)
        
        signals_detected = sum(1 for r in test_results if r.signal_detected)
        total_tests = len(test_results)
        
        if total_tests == 0:
            return 0, "No tests executed"
        
        # Start with base confidence
        score = base_score
        explanations = [f"Base confidence for {attack_type}: {base_score}"]
        
        # Add confidence from detected signals
        signal_bonus = sum(r.confidence_delta for r in test_results if r.signal_detected)
        score += signal_bonus
        explanations.append(f"Signal bonus: +{signal_bonus} ({signals_detected}/{total_tests} signals)")
        
        # Multiple signal types increase confidence
        signal_types = set(r.signal_type for r in test_results if r.signal_detected and r.signal_type)
        if len(signal_types) > 1:
            diversity_bonus = len(signal_types) * 5
            score += diversity_bonus
            explanations.append(f"Signal diversity bonus: +{diversity_bonus} ({len(signal_types)} types)")
        
        # Consistency bonus (multiple payloads trigger signal)
        if signals_detected >= 2:
            consistency_bonus = min(signals_detected * 3, 15)
            score += consistency_bonus
            explanations.append(f"Consistency bonus: +{consistency_bonus} ({signals_detected} payloads)")
        
        # Response time consistency (for timing attacks)
        response_times = [r.response_time_ms for r in test_results if r.response_time_ms]
        if len(response_times) > 2:
            import statistics
            avg_time = statistics.mean(response_times)
            stdev_time = statistics.stdev(response_times) if len(response_times) > 1 else 0
            
            if stdev_time < avg_time * 0.1:  # Low variance = consistent
                score += 5
                explanations.append(f"Response time consistency: +5")
        
        # Cap at 100
        score = min(score, 100)
        
        explanation = "; ".join(explanations)
        
        logger.info(f"Confidence score calculated: {score} - {explanation}")
        
        return score, explanation
    
    def apply_false_positive_penalty(self, score: int, fp_signals: Dict) -> Tuple[int, str]:
        """
        Apply penalty for false positive indicators
        Returns: (adjusted_score, reason)
        """
        if fp_signals.get('is_echo_endpoint'):
            penalty = 30
            score = max(0, score - penalty)
            return score, f"Echo endpoint penalty: -{penalty}"
        
        if fp_signals.get('identical_responses'):
            penalty = 25
            score = max(0, score - penalty)
            return score, f"Identical responses penalty: -{penalty}"
        
        if fp_signals.get('no_behavioral_change'):
            penalty = 20
            score = max(0, score - penalty)
            return score, f"No behavioral change penalty: -{penalty}"
        
        return score, "No false positive penalty"
    
    def categorize_confidence(self, score: int) -> str:
        """
        Categorize confidence level
        Returns: 'verified', 'needs_review', or 'discard'
        """
        if score >= 70:
            return 'verified'
        elif score >= 40:
            return 'needs_review'
        else:
            return 'discard'
    
    def calculate_severity(self, attack_type: str, confidence_score: int) -> str:
        """
        Calculate severity based on attack type and confidence
        Returns: 'critical', 'high', 'medium', or 'low'
        """
        severity_map = {
            'SQLi': 'critical',
            'Auth Bypass': 'critical',
            'SSRF': 'high',
            'LFI': 'high',
            'XSS': 'medium',
            'IDOR': 'high',
            'Open Redirect': 'medium',
            'Business Logic': 'medium'
        }
        
        base_severity = severity_map.get(attack_type, 'medium')
        
        # Downgrade severity if confidence is low
        if confidence_score < 60:
            severity_order = ['critical', 'high', 'medium', 'low']
            current_index = severity_order.index(base_severity)
            if current_index < len(severity_order) - 1:
                base_severity = severity_order[current_index + 1]
        
        return base_severity