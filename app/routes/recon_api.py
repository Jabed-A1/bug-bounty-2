"""
Phase 2: Recon API Routes
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models.recon import Subdomain, LiveHost, OpenPort, Endpoint, ReconJob
from tasks.recon_tasks import (
    task_subdomain_enumeration,
    task_livehost_detection,
    task_port_scanning,
    task_endpoint_collection,
    task_full_recon_pipeline
)
from services.subdomain_enum import SubdomainEnumerator
from services.livehost_detect import LiveHostDetector
from services.port_scan import PortScanner
from services.endpoint_collect import EndpointCollector
import logging

recon_api = Blueprint('recon_api', __name__, url_prefix='/api/recon')
logger = logging.getLogger(__name__)


@recon_api.route('/<int:target_id>/start', methods=['POST'])
def start_recon(target_id):
    """Start recon pipeline"""
    try:
        from app.models.phase1 import Target
        target = Target.query.get_or_404(target_id)
        
        data = request.get_json() or {}
        stages = data.get('stages', ['all'])
        config = data.get('config', {})
        
        results = {'target_id': target_id, 'started_stages': []}
        
        if 'all' in stages:
            task = task_full_recon_pipeline.apply_async(args=[target_id])
            results['pipeline_task_id'] = task.id
            results['started_stages'] = ['full_pipeline']
        else:
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
        
        return jsonify({
            'status': 'success',
            'message': f'Recon started for target {target_id}',
            'data': results
        }), 202
    
    except Exception as e:
        logger.error(f"Error starting recon: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@recon_api.route('/<int:target_id>/status', methods=['GET'])
def get_recon_status(target_id):
    """Get recon status"""
    try:
        jobs = ReconJob.query.filter_by(target_id=target_id).order_by(
            ReconJob.started_at.desc()
        ).all()
        
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
        return jsonify({'status': 'error', 'message': str(e)}), 500


@recon_api.route('/<int:target_id>/results', methods=['GET'])
def get_recon_results(target_id):
    """Get recon results summary"""
    try:
        subdomain_stats = SubdomainEnumerator.get_statistics(target_id)
        livehost_stats = LiveHostDetector.get_statistics(target_id)
        portscan_stats = PortScanner.get_statistics(target_id)
        endpoint_stats = EndpointCollector.get_statistics(target_id)
        
        return jsonify({
            'status': 'success',
            'data': {
                'target_id': target_id,
                'subdomains': subdomain_stats,
                'live_hosts': livehost_stats,
                'ports': portscan_stats,
                'endpoints': endpoint_stats
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting recon results: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@recon_api.route('/<int:target_id>/subdomains', methods=['GET'])
def get_subdomains(target_id):
    """Get subdomains"""
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
        return jsonify({'status': 'error', 'message': str(e)}), 500


@recon_api.route('/<int:target_id>/live-hosts', methods=['GET'])
def get_live_hosts(target_id):
    """Get live hosts"""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
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
        return jsonify({'status': 'error', 'message': str(e)}), 500


@recon_api.route('/<int:target_id>/endpoints', methods=['GET'])
def get_endpoints(target_id):
    """Get endpoints"""
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
        return jsonify({'status': 'error', 'message': str(e)}), 500