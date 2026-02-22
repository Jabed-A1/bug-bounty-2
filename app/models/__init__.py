"""
Database Models Package
"""
# Phase 1
from app.models.phase1 import Target, ScopeRule

# Phase 2 (if exists)
try:
    from app.models.recon import (
        Subdomain, LiveHost, OpenPort, Endpoint, 
        Directory, JSFile, ReconJob
    )
except ImportError:
    pass

# Phase 3 (if exists)
try:
    from app.models.intelligence import (
        EndpointCluster, EndpointParameter, AttackCandidate,
        AuthSurface, ResponseDiff
    )
except ImportError:
    pass

# Phase 4 (if exists)
try:
    from app.models.testing import (
        TestJob, Payload, TestResult, VerifiedFinding, TestJobFeedback
    )
except ImportError:
    pass
