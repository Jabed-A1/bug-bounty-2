"""
Phase 2: Port Scanning Service
"""
import subprocess
import xml.etree.ElementTree as ET
import logging
from datetime import datetime
from typing import List, Dict
from app import db
from app.models.recon import Subdomain, LiveHost, OpenPort

logger = logging.getLogger(__name__)


class PortScanner:
    """Safe and controlled port scanning"""
    
    def __init__(self, target, port_range='top1000'):
        self.target = target
        self.port_range = port_range
        self.rate_limit = 100
        self.timeout = 300
    
    def scan_all_hosts(self) -> Dict:
        """Scan all alive hosts"""
        logger.info(f"Starting port scanning for target {self.target.domain}")
        
        results = {
            'target_id': self.target.id,
            'hosts_scanned': 0,
            'total_ports_found': 0,
            'hosts': []
        }
        
        alive_subdomains = Subdomain.query.filter_by(
            target_id=self.target.id,
            alive=True
        ).all()
        
        if not alive_subdomains:
            logger.warning(f"No alive subdomains found for target {self.target.id}")
            return results
        
        hostnames = list(set([s.subdomain for s in alive_subdomains]))
        
        logger.info(f"Scanning {len(hostnames)} hosts")
        
        for hostname in hostnames:
            try:
                scan_result = self._scan_host(hostname)
                if scan_result and scan_result.get('ports'):
                    results['hosts_scanned'] += 1
                    results['total_ports_found'] += len(scan_result['ports'])
                    results['hosts'].append(scan_result)
            except Exception as e:
                logger.error(f"Error scanning {hostname}: {str(e)}")
        
        logger.info(f"Port scanning complete: {results['hosts_scanned']} hosts, "
                   f"{results['total_ports_found']} open ports found")
        
        return results
    
    def _scan_host(self, hostname: str) -> Dict:
        """Scan a single host"""
        logger.info(f"Scanning {hostname}")
        
        result = {
            'hostname': hostname,
            'ports': [],
            'scan_time': datetime.utcnow().isoformat()
        }
        
        try:
            if self.port_range == 'top1000':
                port_spec = '--top-ports=1000'
            elif self.port_range == 'top100':
                port_spec = '--top-ports=100'
            elif self.port_range == 'common':
                port_spec = '-p 21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5900,8080,8443'
            else:
                port_spec = f'-p {self.port_range}'
            
            cmd = [
                'nmap',
                '-sS',
                '-Pn',
                '--max-rate', str(self.rate_limit),
                '--max-retries', '1',
                '--host-timeout', f'{self.timeout}s',
                '-sV',
                '--version-light',
                '-oX', '-',
                port_spec,
                hostname
            ]
            
            proc_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 60
            )
            
            if proc_result.returncode == 0 or proc_result.stdout:
                ports = self._parse_nmap_xml(proc_result.stdout, hostname)
                result['ports'] = ports
                
                for port_data in ports:
                    self._save_port(hostname, port_data)
            else:
                logger.warning(f"Nmap scan of {hostname} returned errors: {proc_result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"Nmap scan timeout for {hostname}")
        except FileNotFoundError:
            logger.error("Nmap not installed")
        except Exception as e:
            logger.error(f"Nmap scan error for {hostname}: {str(e)}")
        
        return result
    
    def _parse_nmap_xml(self, xml_output: str, hostname: str) -> List[Dict]:
        """Parse nmap XML output"""
        ports = []
        
        try:
            root = ET.fromstring(xml_output)
            
            for host in root.findall('.//host'):
                for port in host.findall('.//port'):
                    port_id = port.get('portid')
                    protocol = port.get('protocol', 'tcp')
                    
                    state_elem = port.find('state')
                    if state_elem is not None and state_elem.get('state') == 'open':
                        service_elem = port.find('service')
                        service_name = service_elem.get('name', '') if service_elem is not None else ''
                        service_product = service_elem.get('product', '') if service_elem is not None else ''
                        service_version = service_elem.get('version', '') if service_elem is not None else ''
                        
                        version_str = f"{service_product} {service_version}".strip()
                        
                        port_data = {
                            'port': int(port_id),
                            'protocol': protocol,
                            'service': service_name,
                            'version': version_str if version_str else None
                        }
                        
                        ports.append(port_data)
                        logger.debug(f"Found open port {port_id}/{protocol} ({service_name}) on {hostname}")
        
        except ET.ParseError as e:
            logger.error(f"Failed to parse nmap XML: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing nmap output: {str(e)}")
        
        return ports
    
    def _save_port(self, hostname: str, port_data: Dict) -> bool:
        """Save discovered port to database"""
        try:
            subdomain = Subdomain.query.filter_by(
                target_id=self.target.id,
                subdomain=hostname
            ).first()
            
            if not subdomain:
                logger.warning(f"Subdomain not found: {hostname}")
                return False
            
            live_hosts = LiveHost.query.filter_by(
                subdomain_id=subdomain.id
            ).all()
            
            if not live_hosts:
                logger.warning(f"No live hosts found for subdomain {hostname}")
                return False
            
            for live_host in live_hosts:
                existing = OpenPort.query.filter_by(
                    live_host_id=live_host.id,
                    port=port_data['port'],
                    protocol=port_data['protocol']
                ).first()
                
                if existing:
                    existing.service = port_data.get('service')
                    existing.version = port_data.get('version')
                    existing.detected_at = datetime.utcnow()
                else:
                    new_port = OpenPort(
                        live_host_id=live_host.id,
                        port=port_data['port'],
                        protocol=port_data['protocol'],
                        service=port_data.get('service'),
                        version=port_data.get('version'),
                        detected_at=datetime.utcnow()
                    )
                    db.session.add(new_port)
            
            db.session.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error saving port {port_data['port']} for {hostname}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_statistics(target_id: int) -> Dict:
        """Get port scanning statistics"""
        subdomains = Subdomain.query.filter_by(target_id=target_id).all()
        subdomain_ids = [s.id for s in subdomains]
        
        live_hosts = LiveHost.query.filter(
            LiveHost.subdomain_id.in_(subdomain_ids)
        ).all()
        live_host_ids = [h.id for h in live_hosts]
        
        total_ports = OpenPort.query.filter(
            OpenPort.live_host_id.in_(live_host_ids)
        ).count()
        
        common_services = db.session.query(
            OpenPort.service,
            db.func.count(OpenPort.id)
        ).filter(
            OpenPort.live_host_id.in_(live_host_ids)
        ).group_by(
            OpenPort.service
        ).order_by(
            db.func.count(OpenPort.id).desc()
        ).limit(10).all()
        
        return {
            'total_ports': total_ports,
            'hosts_with_ports': len(set([p.live_host_id for p in OpenPort.query.filter(
                OpenPort.live_host_id.in_(live_host_ids)
            ).all()])),
            'common_services': [{'service': s[0], 'count': s[1]} for s in common_services]
        }