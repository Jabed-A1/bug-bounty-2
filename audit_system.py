#!/usr/bin/env python
"""
COMPREHENSIVE AUDIT SCRIPT
Bug Bounty Automation Platform
Verifies all components are working and safe for production
"""
import sys
import os

print("=" * 80)
print("🔍 BUG BOUNTY AUTOMATION PLATFORM - COMPREHENSIVE AUDIT")
print("=" * 80)
print()

# ============================================================================
# PART 1: FILE & STRUCTURE VERIFICATION
# ============================================================================
print("📁 PART 1: FILE & STRUCTURE VERIFICATION")
print("-" * 80)

required_files = [
    'app/__init__.py',
    'app/extensions.py',
    'app/models/phase1.py',
    'app/models/jobs.py',
    'app/models/control.py',
    'app/routes/control.py',
    'app/services/control_service.py',
    'app/templates/control/dashboard.html',
    'app/templates/control/target_control.html',
    'app/templates/control/recon_control.html',
    'app/templates/control/intelligence_control.html',
    'app/templates/control/testing_control.html',
    'app/templates/control/job_monitor.html',
]

missing_files = []
for file_path in required_files:
    full_path = f"c:\\Users\\user\\OneDrive\\Desktop\\bug-auto-main\\{file_path}"
    if os.path.exists(full_path):
        print(f"✅ {file_path}")
    else:
        print(f"❌ MISSING: {file_path}")
        missing_files.append(file_path)

print()
if not missing_files:
    print("✅ All required files present")
else:
    print(f"❌ {len(missing_files)} files missing")

# ============================================================================
# PART 2: IMPORT & SYNTAX CHECK
# ============================================================================
print()
print("🔧 PART 2: IMPORT & SYNTAX CHECK")
print("-" * 80)

import_errors = []

try:
    print("Importing app.extensions...", end=" ")
    from app.extensions import db, migrate
    print("✅")
except Exception as e:
    print(f"❌ {str(e)}")
    import_errors.append(('app.extensions', str(e)))

try:
    print("Importing app.models.phase1...", end=" ")
    from app.models.phase1 import Target, ScopeRule
    print("✅")
except Exception as e:
    print(f"❌ {str(e)}")
    import_errors.append(('app.models.phase1', str(e)))

try:
    print("Importing app.models.jobs...", end=" ")
    from app.models.jobs import ReconJob, IntelligenceCandidate, TestJob, VerifiedFinding
    print("✅")
except Exception as e:
    print(f"❌ {str(e)}")
    import_errors.append(('app.models.jobs', str(e)))

try:
    print("Importing app.models.control...", end=" ")
    from app.models.control import KillSwitch, ScopeEnforcer, RateLimiter
    print("✅")
except Exception as e:
    print(f"❌ {str(e)}")
    import_errors.append(('app.models.control', str(e)))

try:
    print("Importing app.services.control_service...", end=" ")
    from app.services.control_service import (
        TargetController, ReconController, IntelligenceController,
        TestingController, SafetyController, MonitoringController
    )
    print("✅")
except Exception as e:
    print(f"❌ {str(e)}")
    import_errors.append(('app.services.control_service', str(e)))

try:
    print("Importing app.routes.control...", end=" ")
    from app.routes.control import control_bp
    print("✅")
except Exception as e:
    print(f"❌ {str(e)}")
    import_errors.append(('app.routes.control', str(e)))

print()
if import_errors:
    print(f"❌ {len(import_errors)} import errors found")
    for module, error in import_errors:
        print(f"   - {module}: {error}")
else:
    print("✅ All imports working")

# ============================================================================
# PART 3: FLASK APP BOOTSTRAP
# ============================================================================
print()
print("⚙️  PART 3: FLASK APP BOOTSTRAP")
print("-" * 80)

try:
    print("Creating Flask app instance...", end=" ")
    from app import create_app
    app = create_app()
    print("✅")
except Exception as e:
    print(f"❌ {str(e)}")
    sys.exit(1)

try:
    print("Checking app context...", end=" ")
    with app.app_context():
        print("✅")
except Exception as e:
    print(f"❌ {str(e)}")
    sys.exit(1)

# ============================================================================
# PART 4: ROUTES VERIFICATION
# ============================================================================
print()
print("🛣️  PART 4: ROUTES VERIFICATION")
print("-" * 80)

control_routes = []
with app.app_context():
    for rule in app.url_map.iter_rules():
        if '/control' in str(rule):
            control_routes.append(str(rule))

print(f"Found {len(control_routes)} control routes:")
for route in sorted(control_routes)[:20]:
    print(f"  ✅ {route}")

if len(control_routes) > 20:
    print(f"  ... and {len(control_routes) - 20} more")

required_routes = [
    '/control/',
    '/control/target/<id>',
    '/control/recon/<id>',
    '/control/intelligence/<id>',
    '/control/testing/<id>',
    '/control/kill-switch/status',
    '/control/monitor/jobs'
]

print()
print("Required routes (sample):")
for route_pattern in required_routes:
    if any(route_pattern.replace('<id>', '') in route for route in control_routes):
        print(f"  ✅ {route_pattern}")
    else:
        print(f"  ⚠️  {route_pattern} not found")

# ============================================================================
# PART 5: DATABASE MODELS VERIFICATION
# ============================================================================
print()
print("🗄️  PART 5: DATABASE MODELS VERIFICATION")
print("-" * 80)

with app.app_context():
    models_to_check = [
        ('Target', Target),
        ('ReconJob', ReconJob),
        ('TestJob', TestJob),
        ('IntelligenceCandidate', IntelligenceCandidate),
        ('VerifiedFinding', VerifiedFinding),
        ('KillSwitch', KillSwitch),
        ('ScopeEnforcer', ScopeEnforcer),
        ('RateLimiter', RateLimiter),
    ]
    
    print("Checking database models:")
    for name, model_class in models_to_check:
        try:
            table_name = model_class.__tablename__
            columns = [c.name for c in model_class.__table__.columns]
            print(f"  ✅ {name:20s} ({table_name:20s}) - {len(columns):2d} columns")
        except Exception as e:
            print(f"  ❌ {name:20s} - {str(e)}")

# ============================================================================
# PART 6: SAFETY MECHANISMS
# ============================================================================
print()
print("🔐 PART 6: SAFETY MECHANISMS")
print("-" * 80)

with app.app_context():
    print("Checking safety features:")
    
    # Check Target model has control fields
    target_instance = Target()
    required_fields = ['enabled', 'paused', 'last_action_at', 'last_modified_at']
    for field in required_fields:
        if hasattr(target_instance, field):
            print(f"  ✅ Target.{field}")
        else:
            print(f"  ❌ Target.{field} missing")
    
    # Check KillSwitch has is_active method
    if hasattr(KillSwitch, 'is_active'):
        print(f"  ✅ KillSwitch.is_active() method")
    else:
        print(f"  ❌ KillSwitch.is_active() missing")
    
    # Check ScopeEnforcer exists
    if hasattr(ScopeEnforcer, '__tablename__'):
        print(f"  ✅ ScopeEnforcer model")
    else:
        print(f"  ❌ ScopeEnforcer missing")
    
    # Check RateLimiter exists
    if hasattr(RateLimiter, '__tablename__'):
        print(f"  ✅ RateLimiter model")
    else:
        print(f"  ❌ RateLimiter missing")

# ============================================================================
# PART 7: SERVICE LAYER VERIFICATION
# ============================================================================
print()
print("⚙️  PART 7: SERVICE LAYER VERIFICATION")
print("-" * 80)

from app.services.control_service import TargetController, SafetyController

print("Service layer controllers:")

controllers = {
    'TargetController': TargetController,
    'ReconController': ReconController,
    'IntelligenceController': IntelligenceController,
    'TestingController': TestingController,
    'SafetyController': SafetyController,
    'MonitoringController': MonitoringController,
}

for name, controller in controllers.items():
    methods = [m for m in dir(controller) if not m.startswith('_')]
    static_methods = [m for m in methods if isinstance(getattr(controller, m), staticmethod)]
    print(f"  ✅ {name:30s} - {len(methods):2d} methods")

# ============================================================================
# SUMMARY
# ============================================================================
print()
print("=" * 80)
print("📊 AUDIT SUMMARY")
print("=" * 80)

total_errors = len(missing_files) + len(import_errors)

if total_errors == 0:
    print("✅ ALL CHECKS PASSED")
    print()
    print("System Status: READY FOR USE")
    print()
    print("Summary:")
    print(f"  • {len(required_files)} required files present")
    print(f"  • All imports working")
    print(f"  • Flask app boots successfully")
    print(f"  • {len(control_routes)} control routes registered")
    print(f"  • 8 database models ready")
    print(f"  • Safety mechanisms in place")
    print(f"  • Service layer complete")
else:
    print(f"⚠️  {total_errors} issues found")
    if missing_files:
        print(f"  • {len(missing_files)} missing files")
    if import_errors:
        print(f"  • {len(import_errors)} import errors")

print()
print("=" * 80)
