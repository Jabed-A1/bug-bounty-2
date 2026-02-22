"""
Phase 2: Celery Recon Tasks
"""
from celery import Celery, chain
from datetime import datetime
import logging
import json
from app import db, create_app
from app.models.recon import ReconJob
from services.subdomain_enum import SubdomainEnumerator
from services.livehost_detect import LiveHostDetector
from services.port_scan import PortScanner
from services.endpoint_collect import EndpointCollector

celery = Celery(
    'recon_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    worker_prefetch_multiplier=1,
)

logger = logging.getLogger(__name__)


def get_target(target_id):
    """Get target object"""
    from app.models.phase1 import Target
    return Target.query.get(target_id)


@celery.task(bind=True, name='recon.subdomain_enumeration')
def task_subdomain_enumeration(self, target_id):
    """Task: Subdomain enumeration"""
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            job = ReconJob(
                target_id=target_id,
                stage='subdomain_enumeration',
                status='running',
                celery_task_id=self.request.id,
                started_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()
            
            logger.info(f"Starting subdomain enumeration for target {target_id}")
            
            enumerator = SubdomainEnumerator(target)
            results = enumerator.enumerate_all()
            
            job.status = 'done'
            job.finished_at = datetime.utcnow()
            job.results_count = results.get('new', 0)
            job.raw_output = json.dumps(results)
            db.session.commit()
            
            logger.info(f"Subdomain enumeration complete for target {target_id}: "
                       f"{results.get('new', 0)} new subdomains")
            
            return {
                'status': 'success',
                'target_id': target_id,
                'results': results
            }
        
        except Exception as e:
            logger.error(f"Subdomain enumeration failed for target {target_id}: {str(e)}")
            if job:
                job.status = 'failed'
                job.finished_at = datetime.utcnow()
                job.error_message = str(e)
                db.session.commit()
            raise


@celery.task(bind=True, name='recon.livehost_detection')
def task_livehost_detection(self, target_id):
    """Task: Live host detection"""
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            job = ReconJob(
                target_id=target_id,
                stage='livehost_detection',
                status='running',
                celery_task_id=self.request.id,
                started_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()
            
            logger.info(f"Starting live host detection for target {target_id}")
            
            detector = LiveHostDetector(target)
            results = detector.detect_all()
            
            job.status = 'done'
            job.finished_at = datetime.utcnow()
            job.results_count = results.get('alive', 0)
            job.raw_output = json.dumps(results)
            db.session.commit()
            
            logger.info(f"Live host detection complete for target {target_id}: "
                       f"{results.get('alive', 0)} alive hosts")
            
            return {
                'status': 'success',
                'target_id': target_id,
                'results': results
            }
        
        except Exception as e:
            logger.error(f"Live host detection failed for target {target_id}: {str(e)}")
            if job:
                job.status = 'failed'
                job.finished_at = datetime.utcnow()
                job.error_message = str(e)
                db.session.commit()
            raise


@celery.task(bind=True, name='recon.port_scanning')
def task_port_scanning(self, target_id, port_range='top1000'):
    """Task: Port scanning"""
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            job = ReconJob(
                target_id=target_id,
                stage='port_scanning',
                status='running',
                celery_task_id=self.request.id,
                started_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()
            
            logger.info(f"Starting port scanning for target {target_id}")
            
            scanner = PortScanner(target, port_range=port_range)
            results = scanner.scan_all_hosts()
            
            job.status = 'done'
            job.finished_at = datetime.utcnow()
            job.results_count = results.get('total_ports_found', 0)
            job.raw_output = json.dumps(results)
            db.session.commit()
            
            logger.info(f"Port scanning complete for target {target_id}: "
                       f"{results.get('total_ports_found', 0)} open ports")
            
            return {
                'status': 'success',
                'target_id': target_id,
                'results': results
            }
        
        except Exception as e:
            logger.error(f"Port scanning failed for target {target_id}: {str(e)}")
            if job:
                job.status = 'failed'
                job.finished_at = datetime.utcnow()
                job.error_message = str(e)
                db.session.commit()
            raise


@celery.task(bind=True, name='recon.endpoint_collection')
def task_endpoint_collection(self, target_id):
    """Task: Endpoint collection"""
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            job = ReconJob(
                target_id=target_id,
                stage='endpoint_collection',
                status='running',
                celery_task_id=self.request.id,
                started_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()
            
            logger.info(f"Starting endpoint collection for target {target_id}")
            
            collector = EndpointCollector(target)
            results = collector.collect_all()
            
            job.status = 'done'
            job.finished_at = datetime.utcnow()
            job.results_count = results.get('endpoints', 0)
            job.raw_output = json.dumps(results)
            db.session.commit()
            
            logger.info(f"Endpoint collection complete for target {target_id}: "
                       f"{results.get('endpoints', 0)} endpoints")
            
            return {
                'status': 'success',
                'target_id': target_id,
                'results': results
            }
        
        except Exception as e:
            logger.error(f"Endpoint collection failed for target {target_id}: {str(e)}")
            if job:
                job.status = 'failed'
                job.finished_at = datetime.utcnow()
                job.error_message = str(e)
                db.session.commit()
            raise


@celery.task(name='recon.full_pipeline')
def task_full_recon_pipeline(target_id):
    """Task: Full recon pipeline"""
    logger.info(f"Starting full recon pipeline for target {target_id}")
    
    pipeline = chain(
        task_subdomain_enumeration.s(target_id),
        task_livehost_detection.s(target_id),
        task_port_scanning.s(target_id, 'top1000'),
        task_endpoint_collection.s(target_id)
    )
    
    result = pipeline.apply_async()
    
    return {
        'status': 'pipeline_started',
        'target_id': target_id,
        'pipeline_id': result.id
    }