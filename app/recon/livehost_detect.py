"""
Phase 2: Live Host Detection Service
Identifies alive hosts using httpx
"""
import subprocess
import json
import logging
from datetime import datetime
from typing import List, Dict
from app import db
from app.models.recon import Subdomain, LiveHost


logger = logging.getLogger(__name__)


class LiveHostDetector:
    """
    Detect live hosts using httpx
    Captures HTTP/HTTPS status, title, technologies
    """
    
    def __init__(self, target):
        self.target = target
        self.results = []
    
    def detect_all(self) -> Dict[str, any]:
        """
        Check all subdomains for live hosts
        Returns: Dictionary with results and statistics
        """
        logger.info(f"Starting live host detection for target {self.target.domain}")
        
        results = {
            'target_id': self.target.id,
            'checked': 0,
            'alive': 0,
            'dead': 0,
            'hosts': []
        }
        
        # Get all subdomains that haven't been checked or need rechecking
        subdomains = Subdomain.query.filter_by(
            target_id=self.target.id
        ).all()
        
        if not subdomains:
            logger.warning(f"No subdomains found for target {self.target.id}")
            return results
        
        # Write subdomains to temp file for httpx
        subdomain_list = [s.subdomain for s in subdomains]
        temp_file = f"/tmp/subdomains_{self.target.id}.txt"
        
        with open(temp_file, 'w') as f:
            f.write('\n'.join(subdomain_list))
        
        # Run httpx
        httpx_results = self._run_httpx(temp_file)
        results['checked'] = len(subdomains)
        
        # Process results
        alive_subdomains = set()
        for host_data in httpx_results:
            subdomain_name = host_data.get('input', '').replace('http://', '').replace('https://', '').split(':')[0]
            alive_subdomains.add(subdomain_name)
            
            # Save live host
            saved = self._save_live_host(host_data)
            if saved:
                results['alive'] += 1
                results['hosts'].append(host_data)
        
        # Update subdomain alive status
        for subdomain in subdomains:
            if subdomain.subdomain in alive_subdomains:
                subdomain.alive = True
            else:
                subdomain.alive = False
        
        results['dead'] = results['checked'] - results['alive']
        db.session.commit()
        
        logger.info(f"Live host detection complete: {results['alive']} alive, {results['dead']} dead")
        
        # Cleanup
        try:
            import os
            os.remove(temp_file)
        except:
            pass
        
        return results
    
    def _run_httpx(self, input_file: str) -> List[Dict]:
        """
        Run httpx for live host detection
        Returns: List of live host data
        """
        logger.info(f"Running httpx on subdomains")
        hosts = []
        
        try:
            cmd = [
                'httpx',
                '-l', input_file,
                '-silent',
                '-json',  # JSON output
                '-status-code',
                '-title',
                '-tech-detect',  # Detect technologies
                '-follow-redirects',
                '-max-redirects', '3',
                '-timeout', '10',
                '-retries', '1',
                '-threads', '50',  # Controlled concurrency
                '-rate-limit', '100',  # 100 requests per second max
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0 or result.stdout:
                # Parse JSON output line by line
                for line in result.stdout.strip().split('\n'):
                    if not line.strip():
                        continue
                    
                    try:
                        host_data = json.loads(line)
                        hosts.append(host_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse httpx output: {line}")
                
                logger.info(f"httpx found {len(hosts)} live hosts")
            else:
                logger.error(f"httpx failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"httpx timeout")
        except FileNotFoundError:
            logger.error("httpx not installed")
        except Exception as e:
            logger.error(f"httpx error: {str(e)}")
        
        return hosts
    
    def _save_live_host(self, host_data: Dict) -> bool:
        """
        Save live host to database
        Returns: True if saved successfully
        """
        try:
            url = host_data.get('url', '')
            if not url:
                return False
            
            # Find corresponding subdomain
            input_domain = host_data.get('input', '').replace('http://', '').replace('https://', '').split(':')[0]
            subdomain = Subdomain.query.filter_by(
                target_id=self.target.id,
                subdomain=input_domain
            ).first()
            
            if not subdomain:
                logger.warning(f"Subdomain not found for {input_domain}")
                return False
            
            # Check if already exists
            existing = LiveHost.query.filter_by(url=url).first()
            
            if existing:
                # Update existing
                existing.status_code = host_data.get('status_code')
                existing.title = host_data.get('title', '')[:500]  # Limit length
                existing.technologies = json.dumps(host_data.get('tech', []))
                existing.content_length = host_data.get('content_length')
                existing.last_checked = datetime.utcnow()
                
                # Handle redirect chain
                chain = host_data.get('chain', [])
                if chain:
                    existing.redirect_chain = json.dumps(chain)
            else:
                # Create new
                new_host = LiveHost(
                    subdomain_id=subdomain.id,
                    url=url,
                    status_code=host_data.get('status_code'),
                    title=host_data.get('title', '')[:500],
                    technologies=json.dumps(host_data.get('tech', [])),
                    content_length=host_data.get('content_length'),
                    redirect_chain=json.dumps(host_data.get('chain', [])),
                    detected_at=datetime.utcnow(),
                    last_checked=datetime.utcnow()
                )
                db.session.add(new_host)
            
            db.session.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error saving live host: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get live host statistics for a target"""
        subdomains = Subdomain.query.filter_by(target_id=target_id).all()
        subdomain_ids = [s.id for s in subdomains]
        
        total_hosts = LiveHost.query.filter(
            LiveHost.subdomain_id.in_(subdomain_ids)
        ).count()
        
        http_hosts = LiveHost.query.filter(
            LiveHost.subdomain_id.in_(subdomain_ids),
            LiveHost.url.like('http://%')
        ).count()
        
        https_hosts = LiveHost.query.filter(
            LiveHost.subdomain_id.in_(subdomain_ids),
            LiveHost.url.like('https://%')
        ).count()
        
        return {
            'total': total_hosts,
            'http': http_hosts,
            'https': https_hosts
        }
    
    @staticmethod
    def get_web_ports(target_id: int) -> List[int]:
        """
        Get list of common web ports from live hosts
        For use in port scanning
        """
        subdomains = Subdomain.query.filter_by(target_id=target_id).all()
        subdomain_ids = [s.id for s in subdomains]
        
        hosts = LiveHost.query.filter(
            LiveHost.subdomain_id.in_(subdomain_ids)
        ).all()
        
        ports = set()
        for host in hosts:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(host.url)
                if parsed.port:
                    ports.add(parsed.port)
            except:
                pass
        
        # Add standard web ports
        ports.update([80, 443, 8080, 8443])
        
        return sorted(list(ports))