# tasks/recon_tasks_simple.py - MINIMAL WORKING TASKS

from celery import Celery
import os

# Initialize Celery
celery = Celery('bugbounty',
                broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
                backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'))


@celery.task(name='tasks.run_subdomain_enum')
def task_run_subdomain_enum(job_id, target_domain):
    """Celery task for subdomain enumeration"""
    from app import app
    from services.recon_executor import ReconExecutor
    
    with app.app_context():
        ReconExecutor.run_subdomain_enum(job_id, target_domain)
    
    return {'job_id': job_id, 'status': 'completed'}
