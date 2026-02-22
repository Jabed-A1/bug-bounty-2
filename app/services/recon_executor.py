# services/recon_executor.py - MINIMAL WORKING RECON

import subprocess
import logging
from datetime import datetime
from app import db
from app.models.recon_simple import ReconJob, Subdomain

logger = logging.getLogger(__name__)


class ReconExecutor:
    """Execute recon tools and save results"""
    
    @staticmethod
    def run_subdomain_enum(job_id: int, target_domain: str):
        """Run subdomain enumeration"""
        job = ReconJob.query.get(job_id)
        if not job:
            return
        
        try:
            # Update status to RUNNING
            job.status = 'RUNNING'
            job.started_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Starting subdomain enum for {target_domain}")
            
            # Try subfinder first (if installed)
            subdomains = set()
            
            try:
                result = subprocess.run(
                    ['subfinder', '-d', target_domain, '-silent'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        subdomain = line.strip()
                        if subdomain and subdomain.endswith(target_domain):
                            subdomains.add(subdomain)
                            
                            # Save to database
                            existing = Subdomain.query.filter_by(
                                target_id=job.target_id,
                                subdomain=subdomain
                            ).first()
                            
                            if not existing:
                                sub = Subdomain(
                                    target_id=job.target_id,
                                    subdomain=subdomain,
                                    source='subfinder'
                                )
                                db.session.add(sub)
                    
                    db.session.commit()
                    logger.info(f"Found {len(subdomains)} subdomains with subfinder")
                
            except FileNotFoundError:
                logger.warning("subfinder not installed, skipping")
            except subprocess.TimeoutExpired:
                logger.warning("subfinder timeout")
            except Exception as e:
                logger.error(f"subfinder error: {str(e)}")
            
            # Fallback: Manual DNS enumeration
            if len(subdomains) == 0:
                common_subs = ['www', 'mail', 'ftp', 'admin', 'api', 'blog', 'dev', 'staging']
                for prefix in common_subs:
                    test_domain = f"{prefix}.{target_domain}"
                    
                    try:
                        result = subprocess.run(
                            ['host', test_domain],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        if result.returncode == 0 and 'has address' in result.stdout:
                            subdomains.add(test_domain)
                            
                            existing = Subdomain.query.filter_by(
                                target_id=job.target_id,
                                subdomain=test_domain
                            ).first()
                            
                            if not existing:
                                sub = Subdomain(
                                    target_id=job.target_id,
                                    subdomain=test_domain,
                                    source='dns_enum'
                                )
                                db.session.add(sub)
                    except:
                        pass
                
                db.session.commit()
            
            # Update job status
            job.status = 'DONE'
            job.finished_at = datetime.utcnow()
            job.results_count = len(subdomains)
            job.raw_output = f"Found {len(subdomains)} subdomains"
            db.session.commit()
            
            logger.info(f"Subdomain enum completed: {len(subdomains)} found")
            
        except Exception as e:
            logger.error(f"Subdomain enum failed: {str(e)}")
            job.status = 'FAILED'
            job.finished_at = datetime.utcnow()
            job.error_message = str(e)
            db.session.commit()
