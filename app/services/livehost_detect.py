"""
Phase 2: Live Host Detection Service
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
    """Detect live hosts using httpx"""
    
    def __init__(self, target):
        self.target = target
        self.results = []
    
    def detect_all(self) -> Dict:
        """Check all subdomains for live hosts"""
        logger.info(f"Starting live host detection for target {self.target.domain}")
        
        results = {
            'target_id': self.target.id,
            'checked': 0,
            'alive': 0,
            'dead': 0,
            'hosts': []
        }
        
        subdomains = Subdomain.query.filter_by(
            target_id=self.target.id
        ).all()
        
        if not subdomains:
            logger.warning(f"No subdomains found for target {self.target.id}")
            return results
        
        subdomain_list = [s.subdomain for s in subdomains]
        temp_file = f"/tmp/subdomains_{self.target.id}.txt"
        
        with open(temp_file, 'w') as f:
            f.write('\n'.join(subdomain_list))
        
        httpx_results = self._run_httpx(temp_file)
        results['checked'] = len(subdomains)
        
        alive_subdomains = set()
        for host_data in httpx_results:
            subdomain_name = host_data.get('input', '').replace('http://', '').replace('https://', '').split(':')[0]
            alive_subdomains.add(subdomain_name)
            
            saved = self._save_live_host(host_data)
            if saved:
                results['alive'] += 1
                results['hosts'].append(host_data)
        
        for subdomain in subdomains:
            if subdomain.subdomain in alive_subdomains:
                subdomain.alive = True
            else:
                subdomain.alive = False
        
        results['dead'] = results['checked'] - results['alive']
        db.session.commit()
        
        logger.info(f"Live host detection complete: {results['alive']} alive, {results['dead']} dead")
        
        try:
            import os
            os.remove(temp_file)
        except:
            pass
        
        return results
    
    def _run_httpx(self, input_file: str) -> List[Dict]:
        """Run httpx for live host detection"""
        logger.info(f"Running httpx on subdomains")
        hosts = []
        
        try:
            cmd = [
                'httpx',
                '-l', input_file,
                '-silent',
                '-json',
                '-status-code',
                '-title',
                '-tech-detect',
                '-follow-redirects',
                '-max-redirects', '3',
                '-timeout', '10',
                '-retries', '1',
                '-threads', '50',
                '-rate-limit', '100',
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0 or result.stdout:
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
        """Save live host to database"""
        try:
            url = host_data.get('url', '')
            if not url:
                return False
            
            input_domain = host_data.get('input', '').replace('http://', '').replace('https://', '').split(':')[0]
            subdomain = Subdomain.query.filter_by(
                target_id=self.target.id,
                subdomain=input_domain
            ).first()
            
            if not subdomain:
                logger.warning(f"Subdomain not found for {input_domain}")
                return False
            
            existing = LiveHost.query.filter_by(url=url).first()
            
            if existing:
                existing.status_code = host_data.get('status_code')
                existing.title = host_data.get('title', '')[:500]
                existing.technologies = json.dumps(host_data.get('tech', []))
                existing.content_length = host_data.get('content_length')
                existing.last_checked = datetime.utcnow()
                
                chain = host_data.get('chain', [])
                if chain:
                    existing.redirect_chain = json.dumps(chain)
            else:
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
        """Get live host statistics"""
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