"""
Phase 2: Directory Fuzzing Service
Smart directory/file discovery using ffuf
"""
import subprocess
import json
import logging
from datetime import datetime
from typing import List, Dict
from app import db
from app.models.recon import LiveHost, Directory


logger = logging.getLogger(__name__)


class DirectoryFuzzer:
    """
    Smart directory and file discovery
    Rate-limited, intelligent wordlist selection
    """
    
    def __init__(self, target, wordlist='small'):
        self.target = target
        self.wordlist = self._get_wordlist(wordlist)
        self.rate_limit = 100  # requests per second
        self.error_threshold = 10  # Stop after 10 consecutive errors
    
    def fuzz_all_hosts(self) -> Dict[str, any]:
        """
        Fuzz all web services
        Returns: Dictionary with results and statistics
        """
        logger.info(f"Starting directory fuzzing for target {self.target.domain}")
        
        results = {
            'target_id': self.target.id,
            'hosts_fuzzed': 0,
            'paths_found': 0,
            'hosts': []
        }
        
        # Get all live hosts with web services
        web_hosts = self._get_web_hosts()
        
        if not web_hosts:
            logger.warning(f"No web hosts found for target {self.target.id}")
            return results
        
        logger.info(f"Fuzzing {len(web_hosts)} web hosts")
        
        for host in web_hosts:
            try:
                fuzz_result = self._fuzz_host(host)
                if fuzz_result and fuzz_result.get('paths'):
                    results['hosts_fuzzed'] += 1
                    results['paths_found'] += len(fuzz_result['paths'])
                    results['hosts'].append(fuzz_result)
            except Exception as e:
                logger.error(f"Error fuzzing {host.url}: {str(e)}")
        
        logger.info(f"Directory fuzzing complete: {results['hosts_fuzzed']} hosts, "
                   f"{results['paths_found']} paths found")
        
        return results
    
    def _get_web_hosts(self) -> List[LiveHost]:
        """Get all live hosts that are web services"""
        from app.models.recon import Subdomain
        
        # Get all subdomains for this target
        subdomains = Subdomain.query.filter_by(target_id=self.target.id).all()
        subdomain_ids = [s.id for s in subdomains]
        
        # Get live hosts
        web_hosts = LiveHost.query.filter(
            LiveHost.subdomain_id.in_(subdomain_ids),
            db.or_(
                LiveHost.url.like('http://%'),
                LiveHost.url.like('https://%')
            )
        ).all()
        
        return web_hosts
    
    def _fuzz_host(self, host: LiveHost) -> Dict:
        """
        Fuzz a single host
        Returns: Dictionary with discovered paths
        """
        logger.info(f"Fuzzing {host.url}")
        
        result = {
            'host_id': host.id,
            'url': host.url,
            'paths': [],
            'fuzz_time': datetime.utcnow().isoformat()
        }
        
        try:
            # Prepare base URL
            base_url = host.url.rstrip('/')
            fuzz_url = f"{base_url}/FUZZ"
            
            cmd = [
                'ffuf',
                '-u', fuzz_url,
                '-w', self.wordlist,
                '-mc', '200,201,202,203,204,301,302,307,308,401,403',  # Match these status codes
                '-fc', '404',  # Filter 404
                '-t', '50',  # 50 threads
                '-rate', str(self.rate_limit),
                '-timeout', '10',
                '-se',  # Stop on spurious errors
                '-json',  # JSON output
                '-o', '/dev/stdout',
                '-silent',
            ]
            
            proc_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if proc_result.returncode == 0 or proc_result.stdout:
                # Parse JSON output
                paths = self._parse_ffuf_output(proc_result.stdout, host)
                result['paths'] = paths
                
                # Save to database
                for path_data in paths:
                    self._save_directory(host, path_data)
            else:
                logger.warning(f"ffuf scan of {host.url} returned errors: {proc_result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"ffuf timeout for {host.url}")
        except FileNotFoundError:
            logger.error("ffuf not installed")
        except Exception as e:
            logger.error(f"ffuf error for {host.url}: {str(e)}")
        
        return result
    
    def _parse_ffuf_output(self, json_output: str, host: LiveHost) -> List[Dict]:
        """
        Parse ffuf JSON output
        Returns: List of discovered paths
        """
        paths = []
        
        try:
            data = json.loads(json_output)
            
            if 'results' in data:
                for result in data['results']:
                    path = result.get('input', {}).get('FUZZ', '')
                    status_code = result.get('status', 0)
                    length = result.get('length', 0)
                    
                    if path:
                        path_data = {
                            'path': f"/{path}",
                            'status_code': status_code,
                            'content_length': length
                        }
                        
                        paths.append(path_data)
                        logger.debug(f"Found path: {path} [{status_code}] on {host.url}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffuf JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing ffuf output: {str(e)}")
        
        return paths
    
    def _save_directory(self, host: LiveHost, path_data: Dict) -> bool:
        """
        Save discovered directory/path to database
        Returns: True if saved successfully
        """
        try:
            existing = Directory.query.filter_by(
                live_host_id=host.id,
                path=path_data['path']
            ).first()
            
            if existing:
                # Update existing
                existing.status_code = path_data['status_code']
                existing.content_length = path_data['content_length']
                existing.detected_at = datetime.utcnow()
            else:
                # Create new
                new_dir = Directory(
                    live_host_id=host.id,
                    path=path_data['path'],
                    status_code=path_data['status_code'],
                    content_length=path_data['content_length'],
                    detected_at=datetime.utcnow()
                )
                db.session.add(new_dir)
            
            db.session.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error saving directory {path_data['path']} for {host.url}: {str(e)}")
            db.session.rollback()
            return False
    
    def _get_wordlist(self, wordlist_type: str) -> str:
        """
        Get wordlist path based on type
        Returns: Full path to wordlist
        """
        wordlists = {
            'small': '/usr/share/wordlists/dirb/common.txt',
            'medium': '/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt',
            'api': '/usr/share/wordlists/api-endpoints.txt',
            'custom': '/opt/bugbounty_platform/wordlists/custom.txt'
        }
        
        # Default to small if not found
        path = wordlists.get(wordlist_type, wordlists['small'])
        
        # Check if exists, fallback to common
        import os
        if not os.path.exists(path):
            logger.warning(f"Wordlist {path} not found, using common.txt")
            return '/usr/share/wordlists/dirb/common.txt'
        
        return path
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get directory fuzzing statistics for a target"""
        from app.models.recon import Subdomain
        
        subdomains = Subdomain.query.filter_by(target_id=target_id).all()
        subdomain_ids = [s.id for s in subdomains]
        
        live_hosts = LiveHost.query.filter(
            LiveHost.subdomain_id.in_(subdomain_ids)
        ).all()
        live_host_ids = [h.id for h in live_hosts]
        
        total_dirs = Directory.query.filter(
            Directory.live_host_id.in_(live_host_ids)
        ).count()
        
        # Get status code distribution
        status_distribution = db.session.query(
            Directory.status_code,
            db.func.count(Directory.id)
        ).filter(
            Directory.live_host_id.in_(live_host_ids)
        ).group_by(
            Directory.status_code
        ).all()
        
        return {
            'total_directories': total_dirs,
            'hosts_fuzzed': len(set([d.live_host_id for d in Directory.query.filter(
                Directory.live_host_id.in_(live_host_ids)
            ).all()])),
            'status_distribution': {str(s[0]): s[1] for s in status_distribution}
        }