"""
Phase 2: Endpoint Collection Service
"""
import subprocess
import logging
from datetime import datetime
from typing import Set, Dict
from urllib.parse import urlparse, parse_qs
import json
from app import db
from app.models.recon import Endpoint, JSFile

logger = logging.getLogger(__name__)


class EndpointCollector:
    """Collect URLs and endpoints from various sources"""
    
    def __init__(self, target):
        self.target = target
        self.domain = target.domain
        self.js_files = set()
    
    def collect_all(self) -> Dict:
        """Run all endpoint collection tools"""
        logger.info(f"Starting endpoint collection for {self.domain}")
        
        results = {
            'domain': self.domain,
            'endpoints': 0,
            'with_params': 0,
            'js_files': 0,
            'sources': {}
        }
        
        gau_endpoints = self._run_gau()
        results['sources']['gau'] = len(gau_endpoints)
        
        wayback_endpoints = self._run_waybackurls()
        results['sources']['waybackurls'] = len(wayback_endpoints)
        
        katana_endpoints = self._run_katana()
        results['sources']['katana'] = len(katana_endpoints)
        
        hakrawler_endpoints = self._run_hakrawler()
        results['sources']['hakrawler'] = len(hakrawler_endpoints)
        
        all_urls = gau_endpoints | wayback_endpoints | katana_endpoints | hakrawler_endpoints
        
        for url in all_urls:
            if self._is_valid_url(url):
                normalized = self._normalize_url(url)
                if normalized:
                    endpoint_data = self._parse_endpoint(normalized)
                    source = self._get_source_for_url(url, [
                        ('gau', gau_endpoints),
                        ('waybackurls', wayback_endpoints),
                        ('katana', katana_endpoints),
                        ('hakrawler', hakrawler_endpoints)
                    ])
                    
                    if self._save_endpoint(endpoint_data, source):
                        results['endpoints'] += 1
                        if endpoint_data['has_params']:
                            results['with_params'] += 1
                    
                    if self._is_js_file(normalized):
                        self.js_files.add(normalized)
        
        for js_url in self.js_files:
            self._save_js_file(js_url)
        
        results['js_files'] = len(self.js_files)
        
        logger.info(f"Endpoint collection complete: {results['endpoints']} endpoints, "
                   f"{results['with_params']} with parameters, {results['js_files']} JS files")
        
        return results
    
    def _run_gau(self) -> Set[str]:
        """Run gau"""
        logger.info(f"Running gau for {self.domain}")
        urls = set()
        
        try:
            cmd = [
                'gau',
                '--blacklist', 'png,jpg,jpeg,gif,svg,css,woff,woff2,ttf,eot',
                '--threads', '5',
                self.domain
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 or result.stdout:
                for line in result.stdout.strip().split('\n'):
                    url = line.strip()
                    if url:
                        urls.add(url)
                
                logger.info(f"gau found {len(urls)} URLs")
            else:
                logger.warning(f"gau completed with warnings: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"gau timeout for {self.domain}")
        except FileNotFoundError:
            logger.warning("gau not installed - skipping")
        except Exception as e:
            logger.error(f"gau error: {str(e)}")
        
        return urls
    
    def _run_waybackurls(self) -> Set[str]:
        """Run waybackurls"""
        logger.info(f"Running waybackurls for {self.domain}")
        urls = set()
        
        try:
            cmd = ['waybackurls']
            
            result = subprocess.run(
                cmd,
                input=self.domain,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 or result.stdout:
                for line in result.stdout.strip().split('\n'):
                    url = line.strip()
                    if url:
                        urls.add(url)
                
                logger.info(f"waybackurls found {len(urls)} URLs")
            else:
                logger.warning(f"waybackurls completed with warnings: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"waybackurls timeout for {self.domain}")
        except FileNotFoundError:
            logger.warning("waybackurls not installed - skipping")
        except Exception as e:
            logger.error(f"waybackurls error: {str(e)}")
        
        return urls
    
    def _run_katana(self) -> Set[str]:
        """Run katana"""
        logger.info(f"Running katana for {self.domain}")
        urls = set()
        
        try:
            cmd = [
                'katana',
                '-u', f"https://{self.domain}",
                '-d', '3',
                '-jc',
                '-silent',
                '-timeout', '10',
                '-delay', '1000',
                '-c', '10',
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0 or result.stdout:
                for line in result.stdout.strip().split('\n'):
                    url = line.strip()
                    if url:
                        urls.add(url)
                
                logger.info(f"katana found {len(urls)} URLs")
            else:
                logger.warning(f"katana completed with warnings: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"katana timeout for {self.domain}")
        except FileNotFoundError:
            logger.warning("katana not installed - skipping")
        except Exception as e:
            logger.error(f"katana error: {str(e)}")
        
        return urls
    
    def _run_hakrawler(self) -> Set[str]:
        """Run hakrawler"""
        logger.info(f"Running hakrawler for {self.domain}")
        urls = set()
        
        try:
            cmd = [
                'hakrawler',
                '-url', f"https://{self.domain}",
                '-depth', '2',
                '-plain',
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 or result.stdout:
                for line in result.stdout.strip().split('\n'):
                    url = line.strip()
                    if url:
                        urls.add(url)
                
                logger.info(f"hakrawler found {len(urls)} URLs")
            else:
                logger.warning(f"hakrawler completed with warnings: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"hakrawler timeout for {self.domain}")
        except FileNotFoundError:
            logger.warning("hakrawler not installed - skipping")
        except Exception as e:
            logger.error(f"hakrawler error: {str(e)}")
        
        return urls
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme or not parsed.netloc:
                return False
            
            if not parsed.netloc.endswith(self.domain):
                return False
            
            skip_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.css', '.woff', '.woff2', 
                             '.ttf', '.eot', '.ico', '.mp4', '.mp3', '.pdf', '.zip', '.tar.gz']
            
            if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
                return False
            
            return True
        
        except Exception:
            return False
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL"""
        try:
            parsed = urlparse(url)
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            if parsed.query:
                normalized += f"?{parsed.query}"
            
            return normalized
        
        except Exception:
            return url
    
    def _parse_endpoint(self, url: str) -> Dict:
        """Parse endpoint"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        return {
            'url': url,
            'method': 'GET',
            'parameter_names': list(params.keys()) if params else [],
            'has_params': bool(params)
        }
    
    def _is_js_file(self, url: str) -> bool:
        """Check if URL is a JavaScript file"""
        return url.lower().endswith('.js')
    
    def _get_source_for_url(self, url: str, source_sets: list) -> str:
        """Determine which tool discovered this URL"""
        sources = []
        for source_name, source_set in source_sets:
            if url in source_set:
                sources.append(source_name)
        return ','.join(sources) if sources else 'unknown'
    
    def _save_endpoint(self, endpoint_data: Dict, source: str) -> bool:
        """Save endpoint to database"""
        try:
            existing = Endpoint.query.filter_by(
                target_id=self.target.id,
                url=endpoint_data['url'],
                method=endpoint_data['method']
            ).first()
            
            if existing:
                if source not in existing.source:
                    existing.source = f"{existing.source},{source}"
                db.session.commit()
                return False
            else:
                new_endpoint = Endpoint(
                    target_id=self.target.id,
                    url=endpoint_data['url'],
                    method=endpoint_data['method'],
                    parameter_names=json.dumps(endpoint_data['parameter_names']),
                    has_params=endpoint_data['has_params'],
                    source=source,
                    discovered_at=datetime.utcnow()
                )
                db.session.add(new_endpoint)
                db.session.commit()
                return True
        
        except Exception as e:
            logger.error(f"Error saving endpoint {endpoint_data['url']}: {str(e)}")
            db.session.rollback()
            return False
    
    def _save_js_file(self, js_url: str) -> bool:
        """Save JS file to database"""
        try:
            existing = JSFile.query.filter_by(url=js_url).first()
            
            if not existing:
                new_js = JSFile(
                    target_id=self.target.id,
                    url=js_url,
                    discovered_at=datetime.utcnow()
                )
                db.session.add(new_js)
                db.session.commit()
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error saving JS file {js_url}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get endpoint statistics"""
        total = Endpoint.query.filter_by(target_id=target_id).count()
        with_params = Endpoint.query.filter_by(target_id=target_id, has_params=True).count()
        js_files = JSFile.query.filter_by(target_id=target_id).count()
        
        return {
            'total_endpoints': total,
            'with_parameters': with_params,
            'js_files': js_files
        }