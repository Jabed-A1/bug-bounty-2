"""
Phase 2: Subdomain Enumeration Service
Passive subdomain discovery using subfinder and amass
"""
import subprocess
import json
import logging
from datetime import datetime
from typing import List, Set, Dict
from urllib.parse import urlparse
from app import db
from app.models.recon import Subdomain, ReconJob


logger = logging.getLogger(__name__)


class SubdomainEnumerator:
    """
    Passive subdomain enumeration using multiple tools
    Combines results and deduplicates
    """
    
    def __init__(self, target):
        self.target = target
        self.domain = target.domain
        self.results = set()
        self.source_mapping = {}
    
    def enumerate_all(self) -> Dict[str, any]:
        """
        Run all subdomain enumeration tools
        Returns: Dictionary with results and statistics
        """
        logger.info(f"Starting subdomain enumeration for {self.domain}")
        
        results = {
            'domain': self.domain,
            'subdomains': [],
            'sources': {},
            'total': 0,
            'new': 0,
            'existing': 0
        }
        
        # Run tools
        subfinder_results = self._run_subfinder()
        results['sources']['subfinder'] = len(subfinder_results)
        
        amass_results = self._run_amass()
        results['sources']['amass'] = len(amass_results)
        
        # Combine and deduplicate
        all_subs = subfinder_results | amass_results
        results['total'] = len(all_subs)
        
        # Store in database
        for subdomain in all_subs:
            if self._is_in_scope(subdomain):
                source = self.source_mapping.get(subdomain, 'unknown')
                saved = self._save_subdomain(subdomain, source)
                if saved:
                    results['subdomains'].append(subdomain)
                    if saved == 'new':
                        results['new'] += 1
                    else:
                        results['existing'] += 1
        
        logger.info(f"Subdomain enumeration complete: {results['total']} found, "
                   f"{results['new']} new, {results['existing']} existing")
        
        return results
    
    def _run_subfinder(self) -> Set[str]:
        """
        Run subfinder for subdomain enumeration
        Returns: Set of discovered subdomains
        """
        logger.info(f"Running subfinder for {self.domain}")
        subdomains = set()
        
        try:
            cmd = [
                'subfinder',
                '-d', self.domain,
                '-all',  # Use all sources
                '-silent',  # No banner
                '-nW',  # No wildcard filtering (we handle this)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    subdomain = line.strip().lower()
                    if subdomain:
                        subdomains.add(subdomain)
                        if subdomain not in self.source_mapping:
                            self.source_mapping[subdomain] = 'subfinder'
                
                logger.info(f"Subfinder found {len(subdomains)} subdomains")
            else:
                logger.error(f"Subfinder failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"Subfinder timeout for {self.domain}")
        except FileNotFoundError:
            logger.error("Subfinder not installed")
        except Exception as e:
            logger.error(f"Subfinder error: {str(e)}")
        
        return subdomains
    
    def _run_amass(self) -> Set[str]:
        """
        Run amass in PASSIVE mode for subdomain enumeration
        Returns: Set of discovered subdomains
        """
        logger.info(f"Running amass (passive) for {self.domain}")
        subdomains = set()
        
        try:
            cmd = [
                'amass',
                'enum',
                '-passive',  # PASSIVE MODE ONLY
                '-d', self.domain,
                '-silent',
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for amass
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    subdomain = line.strip().lower()
                    if subdomain:
                        subdomains.add(subdomain)
                        if subdomain not in self.source_mapping:
                            self.source_mapping[subdomain] = 'amass'
                
                logger.info(f"Amass found {len(subdomains)} subdomains")
            else:
                logger.warning(f"Amass completed with warnings: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"Amass timeout for {self.domain}")
        except FileNotFoundError:
            logger.warning("Amass not installed - skipping")
        except Exception as e:
            logger.error(f"Amass error: {str(e)}")
        
        return subdomains
    
    def _is_in_scope(self, subdomain: str) -> bool:
        """
        Check if subdomain is in scope
        Respects wildcard rules from Phase 1
        """
        # Basic domain check
        if not subdomain.endswith(self.domain):
            return False
        
        # Check against scope rules
        if hasattr(self.target, 'scope_rules'):
            scope_rules = json.loads(self.target.scope_rules) if isinstance(self.target.scope_rules, str) else self.target.scope_rules
            
            # Check exclusions
            if 'excluded_subdomains' in scope_rules:
                for excluded in scope_rules['excluded_subdomains']:
                    if subdomain == excluded or subdomain.endswith('.' + excluded):
                        logger.debug(f"Subdomain {subdomain} excluded by scope rules")
                        return False
            
            # Check wildcard restrictions
            if not scope_rules.get('allow_wildcards', True):
                # Count subdomain levels
                base_parts = self.domain.split('.')
                sub_parts = subdomain.split('.')
                extra_levels = len(sub_parts) - len(base_parts)
                
                if extra_levels > 1:
                    logger.debug(f"Subdomain {subdomain} exceeds depth limit")
                    return False
        
        return True
    
    def _save_subdomain(self, subdomain: str, source: str) -> str:
        """
        Save subdomain to database
        Returns: 'new' or 'existing'
        """
        try:
            existing = Subdomain.query.filter_by(
                target_id=self.target.id,
                subdomain=subdomain
            ).first()
            
            if existing:
                # Update last_seen
                existing.last_seen = datetime.utcnow()
                # Update source if different
                if source not in existing.source:
                    existing.source = f"{existing.source},{source}"
                db.session.commit()
                return 'existing'
            else:
                # Create new
                new_subdomain = Subdomain(
                    target_id=self.target.id,
                    subdomain=subdomain,
                    source=source,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )
                db.session.add(new_subdomain)
                db.session.commit()
                return 'new'
        
        except Exception as e:
            logger.error(f"Error saving subdomain {subdomain}: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get subdomain statistics for a target"""
        total = Subdomain.query.filter_by(target_id=target_id).count()
        alive = Subdomain.query.filter_by(target_id=target_id, alive=True).count()
        dead = Subdomain.query.filter_by(target_id=target_id, alive=False).count()
        unchecked = Subdomain.query.filter_by(target_id=target_id, alive=None).count()
        
        return {
            'total': total,
            'alive': alive,
            'dead': dead,
            'unchecked': unchecked
        }