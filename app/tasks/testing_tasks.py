"""
Phase 4: Testing Celery Tasks
Async test execution with isolation
"""
from celery import chain
from datetime import datetime
import logging
from app import db, create_app
from app.models.intelligence import AttackCandidate
from app.models.testing import TestJob
from services.testing_orchestrator import TestingOrchestrator
from services.payload_library import PayloadLibrary

logger = logging.getLogger(__name__)


def get_celery_app():
    """Get Celery app"""
    from tasks.recon_tasks import celery
    return celery


celery = get_celery_app()


@celery.task(bind=True, name='testing.initialize_payloads')
def task_initialize_payloads(self):
    """
    Task: Initialize payload library
    Run once on platform setup
    """
    app = create_app()
    with app.app_context():
        try:
            logger.info("Initializing payload library")
            PayloadLibrary.initialize_library()
            logger.info("Payload library initialized")
            return {'status': 'success'}
        except Exception as e:
            logger.error(f"Payload initialization failed: {str(e)}")
            raise


@celery.task(bind=True, name='testing.execute_test_job')
def task_execute_test_job(self, candidate_id: int):
    """
    Task: Execute single test job
    Isolated execution per candidate
    """
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"Starting test job for candidate {candidate_id}")
            
            # Get candidate
            candidate = AttackCandidate.query.get(candidate_id)
            if not candidate:
                raise ValueError(f"Candidate {candidate_id} not found")
            
            # Get target
            from app.models.phase1 import Target
            target = Target.query.get(candidate.target_id)
            if not target:
                raise ValueError(f"Target {candidate.target_id} not found")
            
            # Create orchestrator
            orchestrator = TestingOrchestrator(target)
            
            # Execute test
            test_job = orchestrator.execute_test_job(candidate)
            
            logger.info(f"Test job {test_job.id} completed: {test_job.status}")
            
            return {
                'status': 'success',
                'test_job_id': test_job.id,
                'test_status': test_job.status,
                'confidence_score': test_job.confidence_score
            }
        
        except Exception as e:
            logger.error(f"Test job failed for candidate {candidate_id}: {str(e)}")
            raise


@celery.task(bind=True, name='testing.batch_test_candidates')
def task_batch_test_candidates(self, target_id: int, candidate_ids: list = None):
    """
    Task: Execute batch testing
    Tests multiple candidates
    """
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"Starting batch testing for target {target_id}")
            
            # Get candidates
            if candidate_ids:
                candidates = AttackCandidate.query.filter(
                    AttackCandidate.id.in_(candidate_ids)
                ).all()
            else:
                candidates = AttackCandidate.query.filter_by(
                    target_id=target_id,
                    reviewed=True,
                    approved_for_testing=True
                ).all()
            
            logger.info(f"Found {len(candidates)} candidates to test")
            
            # Execute tests sequentially (can be parallelized)
            results = []
            for candidate in candidates:
                try:
                    task_result = task_execute_test_job.apply_async(args=[candidate.id])
                    results.append({
                        'candidate_id': candidate.id,
                        'task_id': task_result.id
                    })
                except Exception as e:
                    logger.error(f"Failed to start test for candidate {candidate.id}: {str(e)}")
                    results.append({
                        'candidate_id': candidate.id,
                        'error': str(e)
                    })
            
            logger.info(f"Batch testing started: {len(results)} jobs")
            
            return {
                'status': 'success',
                'target_id': target_id,
                'jobs_started': len(results),
                'results': results
            }
        
        except Exception as e:
            logger.error(f"Batch testing failed for target {target_id}: {str(e)}")
            raise


@celery.task(bind=True, name='testing.retest_low_confidence')
def task_retest_low_confidence(self, test_job_id: int):
    """
    Task: Retest low-confidence findings
    Uses additional payloads
    """
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"Retesting test job {test_job_id}")
            
            test_job = TestJob.query.get(test_job_id)
            if not test_job:
                raise ValueError(f"Test job {test_job_id} not found")
            
            if test_job.confidence_score >= 70:
                logger.info(f"Test job {test_job_id} already high confidence")
                return {'status': 'skipped', 'reason': 'already_high_confidence'}
            
            candidate = test_job.candidate
            from app.models.phase1 import Target
            target = Target.query.get(test_job.target_id)
            
            # Re-run with fresh orchestrator
            orchestrator = TestingOrchestrator(target)
            new_test_job = orchestrator.execute_test_job(candidate)
            
            logger.info(f"Retest complete: job {new_test_job.id}, confidence {new_test_job.confidence_score}")
            
            return {
                'status': 'success',
                'original_job_id': test_job_id,
                'new_job_id': new_test_job.id,
                'original_confidence': test_job.confidence_score,
                'new_confidence': new_test_job.confidence_score
            }
        
        except Exception as e:
            logger.error(f"Retest failed for job {test_job_id}: {str(e)}")
            raise