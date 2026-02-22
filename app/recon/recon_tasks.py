"""
Phase 2: Celery Tasks for Recon Pipeline
Async task orchestration with proper error handling
"""
from celery import Celery, chain, group
from datetime import datetime
import logging
import json
from app import db, create_app
from app.models.recon import ReconJob
from app.recon.subdomain_enum import SubdomainEnumerator
from app.recon.livehost_detect import LiveHostDetector
from app.recon.port_scan import PortScanner
from app.recon.endpoint_collect import EndpointCollector
from app.recon.directory_fuzz import DirectoryFuzzer
from app.recon.js_analysis import JSAnalyzer


# Initialize Celery
celery = Celery(
    'recon_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Celery configuration
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minute soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

logger = logging.getLogger(__name__)

# Flask app context helper
def get_target(target_id):
    """Get target object with app context"""
    from app.models.phase1 import Target  # Assuming Phase 1 models
    return Target.query.get(target_id)


@celery.task(bind=True, name='recon.subdomain_enumeration')
def task_subdomain_enumeration(self, target_id):
    """
    Task: Subdomain enumeration
    Stage 1 of recon pipeline
    """
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            # Create job record
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
            
            # Run subdomain enumeration
            enumerator = SubdomainEnumerator(target)
            results = enumerator.enumerate_all()
            
            # Update job
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
    """
    Task: Live host detection
    Stage 2 of recon pipeline
    """
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            # Create job record
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
            
            # Run live host detection
            detector = LiveHostDetector(target)
            results = detector.detect_all()
            
            # Update job
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
    """
    Task: Port scanning
    Stage 3 of recon pipeline
    """
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            # Create job record
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
            
            # Run port scanning
            scanner = PortScanner(target, port_range=port_range)
            results = scanner.scan_all_hosts()
            
            # Update job
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
    """
    Task: Endpoint collection
    Stage 4 of recon pipeline
    """
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            # Create job record
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
            
            # Run endpoint collection
            collector = EndpointCollector(target)
            results = collector.collect_all()
            
            # Update job
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


@celery.task(bind=True, name='recon.directory_fuzzing')
def task_directory_fuzzing(self, target_id, wordlist='small'):
    """
    Task: Directory fuzzing
    Stage 5 of recon pipeline
    """
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            # Create job record
            job = ReconJob(
                target_id=target_id,
                stage='directory_fuzzing',
                status='running',
                celery_task_id=self.request.id,
                started_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()
            
            logger.info(f"Starting directory fuzzing for target {target_id}")
            
            # Run directory fuzzing
            fuzzer = DirectoryFuzzer(target, wordlist=wordlist)
            results = fuzzer.fuzz_all_hosts()
            
            # Update job
            job.status = 'done'
            job.finished_at = datetime.utcnow()
            job.results_count = results.get('paths_found', 0)
            job.raw_output = json.dumps(results)
            db.session.commit()
            
            logger.info(f"Directory fuzzing complete for target {target_id}: "
                       f"{results.get('paths_found', 0)} paths found")
            
            return {
                'status': 'success',
                'target_id': target_id,
                'results': results
            }
        
        except Exception as e:
            logger.error(f"Directory fuzzing failed for target {target_id}: {str(e)}")
            if job:
                job.status = 'failed'
                job.finished_at = datetime.utcnow()
                job.error_message = str(e)
                db.session.commit()
            raise


@celery.task(bind=True, name='recon.js_analysis')
def task_js_analysis(self, target_id):
    """
    Task: JavaScript analysis
    Stage 6 of recon pipeline
    """
    app = create_app()
    with app.app_context():
        job = None
        try:
            target = get_target(target_id)
            if not target:
                raise ValueError(f"Target {target_id} not found")
            
            # Create job record
            job = ReconJob(
                target_id=target_id,
                stage='js_analysis',
                status='running',
                celery_task_id=self.request.id,
                started_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()
            
            logger.info(f"Starting JS analysis for target {target_id}")
            
            # Run JS analysis
            analyzer = JSAnalyzer(target)
            results = analyzer.analyze_all()
            
            # Update job
            job.status = 'done'
            job.finished_at = datetime.utcnow()
            job.results_count = results.get('endpoints_extracted', 0)
            job.raw_output = json.dumps(results)
            db.session.commit()
            
            logger.info(f"JS analysis complete for target {target_id}: "
                       f"{results.get('endpoints_extracted', 0)} endpoints extracted")
            
            return {
                'status': 'success',
                'target_id': target_id,
                'results': results
            }
        
        except Exception as e:
            logger.error(f"JS analysis failed for target {target_id}: {str(e)}")
            if job:
                job.status = 'failed'
                job.finished_at = datetime.utcnow()
                job.error_message = str(e)
                db.session.commit()
            raise


@celery.task(name='recon.full_pipeline')
def task_full_recon_pipeline(target_id, config=None):
    """
    Task: Full recon pipeline orchestration
    Chains all recon stages in order
    """
    if config is None:
        config = {
            'port_range': 'top1000',
            'wordlist': 'small'
        }
    
    logger.info(f"Starting full recon pipeline for target {target_id}")
    
    # Create chain of tasks
    pipeline = chain(
        task_subdomain_enumeration.s(target_id),
        task_livehost_detection.s(target_id),
        task_port_scanning.s(target_id, config.get('port_range', 'top1000')),
        task_endpoint_collection.s(target_id),
        task_directory_fuzzing.s(target_id, config.get('wordlist', 'small')),
        task_js_analysis.s(target_id)
    )
    
    # Execute pipeline
    result = pipeline.apply_async()
    
    return {
        'status': 'pipeline_started',
        'target_id': target_id,
        'pipeline_id': result.id
    }


# Utility task for status checking
@celery.task(name='recon.get_pipeline_status')
def task_get_pipeline_status(target_id):
    """Get status of all recon jobs for a target"""
    app = create_app()
    with app.app_context():
        jobs = ReconJob.query.filter_by(target_id=target_id).order_by(
            ReconJob.started_at.desc()
        ).all()
        
        return {
            'target_id': target_id,
            'jobs': [job.to_dict() for job in jobs]
        }