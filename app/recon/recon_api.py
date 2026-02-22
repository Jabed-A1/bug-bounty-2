"""
Phase 2: Recon API Endpoints
RESTful API for recon operations
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models.recon import (
    Subdomain, LiveHost, OpenPort, Endpoint, 
    Directory, JSFile, ReconJob, ReconConfig
)
from app.tasks.recon_tasks import (
    task_subdomain_enumeration,
    task_livehost_detection,
    task_port_scanning,
    task_endpoint_collection,
    task_directory_fuzzing,
    task_js_analysis,
    task_full_recon_pipeline
)
from app.recon.subdomain_enum import SubdomainEnumerator
from app.recon.livehost_detect import LiveHostDetector
from app.recon.port_scan import PortScanner
from app.recon.endpoint_collect import EndpointCollector
from app.recon.directory_fuzz import DirectoryFuzzer
from app.recon.js_analysis import JSAnalyzer
import logging


recon_api = Blueprint('recon_api', __name__, url_prefix='/api/recon')
logger = logging.getLogger(__name__)


# ============================================================================
# RECON PIPELINE ENDPOINTS
# ============================================================================

@recon_api.route('/<int:target_id>/start', methods=['POST'])
def start_recon(target_id):
    """
    Start full recon pipeline for a target
    
    POST /api/recon/<target_id>/start
    Body: {
        "stages": ["subdomain", "livehost", "portscan", "endpoints", "directories", "js"],
        "config": {
            "port_range": "top1000",
            "wordlist": "small"
        }
    }
    """
    try:
        from app.models.phase1 import Target
        target = Target.query.get_or_404(target_id)
        
        data = request.get_json() or {}
        stages = data.get('stages', ['all'])
        config = data.get('config', {})
        
        results = {'target_id': target_id, 'started_stages': []}
        
        if 'all' in stages:
            # Start full pipeline
            task = task_full_recon_pipeline.apply_async(
                args=[target_id, config]
            )
            results['pipeline_task_id'] = task.id
            results['started_stages'] = ['full_pipeline']
        else:
            # Start individual stages
            if 'subdomain' in stages:
                task = task_subdomain_enumeration.apply_async(args=[target_id])
                results['subdomain_task_id'] = task.id
                results['started_stages'].append('subdomain')
            
            if 'livehost' in stages:
                task = task_livehost_detection.apply_async(args=[target_id])
                results['livehost_task_id'] = task.id
                results['started_stages'].append('livehost')
            
            if 'portscan' in stages:
                port_range = config.get('port_range', 'top1000')
                task = task_port_scanning.apply_async(args=[target_id, port_range])
                results['portscan_task_id'] = task.id
                results['started_stages'].append('portscan')
            
            if 'endpoints' in stages:
                task = task_endpoint_collection.apply_async(args=[target_id])
                results['endpoints_task_id'] = task.id
                results['started_stages'].append('endpoints')
            
            if 'directories' in stages:
                wordlist = config.get('wordlist', 'small')
                task = task_directory_fuzzing.apply_async(args=[target_id, wordlist])
                results['directories_task_id'] = task.id
                results['started_stages'].append('directories')
            
            if 'js' in stages:
                task = task_js_analysis.apply_async(args=[target_id])
                results['js_task_id'] = task.id
                results['started_stages'].append('js')
        
        return jsonify({
            'status': 'success',
            'message': f'Recon started for target {target_id}',
            'data': results
        }), 202
    
    except Exception as e:
        logger.error(f"Error starting recon: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@recon_api.route('/<int:target_id>/status', methods=['GET'])
def get_recon_status(target_id):
    """
    Get recon status for a target
    
    GET /api/recon/<target_id>/status
    """
    try:
        jobs = ReconJob.query.filter_by(target_id=target_id).order_by(
            ReconJob.started_at.desc()
        ).all()
        
        # Group by stage
        status_by_stage = {}
        for job in jobs:
            if job.stage not in status_by_stage:
                status_by_stage[job.stage] = job.to_dict()
        
        return jsonify({
            'status': 'success',
            'data': {
                'target_id': target_id,
                'stages': status_by_stage,
                'total_jobs': len(jobs)
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting recon status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@recon_api.route('/<int:target_id>/results', methods=['GET'])
def get_recon_results(target_id):
    """
    Get recon results summary for a target
    
    GET /api/recon/<target_id>/results
    """
    try:
        # Get statistics from each module
        subdomain_stats = SubdomainEnumerator.get_statistics(target_id)
        livehost_stats = LiveHostDetector.get_statistics(target_id)
        portscan_stats = PortScanner.get_statistics(target_id)
        endpoint_stats = EndpointCollector.get_statistics(target_id)
        directory_stats = DirectoryFuzzer.get_statistics(target_id)
        js_stats = JSAnalyzer.get_statistics(target_id)
        
        return jsonify({
            'status': 'success',
            'data': {
                'target_id': target_id,
                'subdomains': subdomain_stats,
                'live_hosts': livehost_stats,
                'ports': portscan_stats,
                'endpoints': endpoint_stats,
                'directories': directory_stats,
                'js_analysis': js_stats
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting recon results: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# SUBDOMAIN ENDPOINTS
# ============================================================================

@recon_api.route('/<int:target_id>/subdomains', methods=['GET'])
def get_subdomains(target_id):
    """
    Get all subdomains for a target
    
    GET /api/recon/<target_id>/subdomains?alive=true&limit=100&offset=0
    """
    try:
        alive = request.args.get('alive')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        query = Subdomain.query.filter_by(target_id=target_id)
        
        if alive is not None:
            alive_bool = alive.lower() == 'true'
            query = query.filter_by(alive=alive_bool)
        
        total = query.count()
        subdomains = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'subdomains': [s.to_dict() for s in subdomains]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting subdomains: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# LIVE HOST ENDPOINTS
# ============================================================================

@recon_api.route('/<int:target_id>/live-hosts', methods=['GET'])
def get_live_hosts(target_id):
    """
    Get all live hosts for a target
    
    GET /api/recon/<target_id>/live-hosts?limit=100&offset=0
    """
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Get subdomains for this target
        subdomains = Subdomain.query.filter_by(target_id=target_id).all()
        subdomain_ids = [s.id for s in subdomains]
        
        query = LiveHost.query.filter(LiveHost.subdomain_id.in_(subdomain_ids))
        total = query.count()
        hosts = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'hosts': [h.to_dict() for h in hosts]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting live hosts: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# PORT ENDPOINTS
# ============================================================================

@recon_api.route('/<int:target_id>/ports', methods=['GET'])
def get_ports(target_id):
    """
    Get all open ports for a target
    
    GET /api/recon/<target_id>/ports?service=http&limit=100&offset=0
    """
    try:
        service = request.args.get('service')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Get live hosts for this target
        subdomains = Subdomain.query.filter_by(target_id=target_id).all()
        subdomain_ids = [s.id for s in subdomains]
        live_hosts = LiveHost.query.filter(LiveHost.subdomain_id.in_(subdomain_ids)).all()
        live_host_ids = [h.id for h in live_hosts]
        
        query = OpenPort.query.filter(OpenPort.live_host_id.in_(live_host_ids))
        
        if service:
            query = query.filter(OpenPort.service.like(f'%{service}%'))
        
        total = query.count()
        ports = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'ports': [p.to_dict() for p in ports]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting ports: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# ENDPOINT ENDPOINTS
# ============================================================================

@recon_api.route('/<int:target_id>/endpoints', methods=['GET'])
def get_endpoints(target_id):
    """
    Get all endpoints for a target
    
    GET /api/recon/<target_id>/endpoints?has_params=true&limit=100&offset=0
    """
    try:
        has_params = request.args.get('has_params')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        query = Endpoint.query.filter_by(target_id=target_id)
        
        if has_params is not None:
            has_params_bool = has_params.lower() == 'true'
            query = query.filter_by(has_params=has_params_bool)
        
        total = query.count()
        endpoints = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'endpoints': [e.to_dict() for e in endpoints]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting endpoints: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# DIRECTORY ENDPOINTS
# ============================================================================

@recon_api.route('/<int:target_id>/directories', methods=['GET'])
def get_directories(target_id):
    """
    Get all discovered directories for a target
    
    GET /api/recon/<target_id>/directories?status_code=200&limit=100&offset=0
    """
    try:
        status_code = request.args.get('status_code')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Get live hosts for this target
        subdomains = Subdomain.query.filter_by(target_id=target_id).all()
        subdomain_ids = [s.id for s in subdomains]
        live_hosts = LiveHost.query.filter(LiveHost.subdomain_id.in_(subdomain_ids)).all()
        live_host_ids = [h.id for h in live_hosts]
        
        query = Directory.query.filter(Directory.live_host_id.in_(live_host_ids))
        
        if status_code:
            query = query.filter_by(status_code=int(status_code))
        
        total = query.count()
        directories = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'directories': [d.to_dict() for d in directories]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting directories: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# JS FILE ENDPOINTS
# ============================================================================

@recon_api.route('/<int:target_id>/js-files', methods=['GET'])
def get_js_files(target_id):
    """
    Get all JS files for a target
    
    GET /api/recon/<int:target_id>/js-files?analyzed=true&limit=100&offset=0
    """
    try:
        analyzed = request.args.get('analyzed')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        query = JSFile.query.filter_by(target_id=target_id)
        
        if analyzed is not None:
            analyzed_bool = analyzed.lower() == 'true'
            query = query.filter_by(analyzed=analyzed_bool)
        
        total = query.count()
        js_files = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'js_files': [j.to_dict() for j in js_files]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting JS files: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500