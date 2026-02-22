# Quick Start Guide - SOC Control Center

Get the bug bounty automation dashboard running in 5 minutes.

---

## 📦 Prerequisites

```bash
# Python 3.8+
python --version

# Flask and dependencies installed
pip install flask flask-sqlalchemy flask-migrate
```

---

## 🚀 Get Running in 5 Steps

### Step 1: Navigate to Project
```bash
cd c:\Users\user\OneDrive\Desktop\bug-auto-main
```

### Step 2: Verify Application
```bash
# Check Python syntax
python -m py_compile app/routes/control.py
python -m py_compile app/services/control_service.py

# Verify imports
python -c "from app import create_app; app = create_app(); print('✅ App created successfully')"
```

**Expected Output**: ✅ App created successfully

### Step 3: Initialize Database
```bash
# Option A: Create fresh database
python << 'EOF'
from app import create_app, db
from app.models.phase1 import Target
from app.models.jobs import ReconJob, TestJob, IntelligenceCandidate, VerifiedFinding
from app.models.control import KillSwitch, ScopeEnforcer, RateLimiter

app = create_app()
with app.app_context():
    db.create_all()
    print("✅ Database tables created")
EOF
```

### Step 4: Create Sample Target (Optional)
```bash
python << 'EOF'
from app import create_app, db
from app.models.phase1 import Target

app = create_app()
with app.app_context():
    # Check if target already exists
    if not Target.query.filter_by(name='example.com').first():
        target = Target(
            name='example.com',
            target_url='https://example.com',
            enabled=True
        )
        db.session.add(target)
        db.session.commit()
        print(f"✅ Created target: {target.name} (ID: {target.id})")
    else:
        print("✅ Target already exists")
EOF
```

### Step 5: Start Development Server
```bash
# Set Flask app
set FLASK_APP=app

# Run with debug mode
python -m flask run --debug

# Or
python -m flask --app app run --debug
```

**Expected Output**:
```
 * Environment: production
   WARNING: This is a development server. Do not use it in production.
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

---

## 🌐 Access the Control Center

Open your browser:

### Main Dashboard
```
http://localhost:5000/control/
```

Shows overall system status, phases 1-4 overview, recent activity.

### Phase 1 - Targets
```
http://localhost:5000/control/target/1
```

Enable/disable/pause/resume targets. (Replace `1` with actual target ID)

### Phase 2 - Recon
```
http://localhost:5000/control/recon/1
```

Start/stop individual recon modules. (Replace `1` with target ID)

### Phase 3 - Intelligence
```
http://localhost:5000/control/intelligence/1
```

Approve/reject discovered endpoints. (Replace `1` with target ID)

### Phase 4 - Testing
```
http://localhost:5000/control/testing/1
```

Start tests on approved candidates. (Replace `1` with target ID)

### Job Monitor
```
http://localhost:5000/control/monitor/jobs
```

Real-time view of all running/completed jobs.

---

## 🎯 Try It Out

### 1. View Dashboard
Click "SOC CONTROL CENTER" → "Main Dashboard"

### 2. View Targets
Click "All Targets" to see targets list

### 3. Click on a Target
Click target name to see Phase 1 control panel

### 4. Start Recon
- Click "Recon Control" from target detail
- Click "Start" button on any module
- Watch progress in "Job Monitor"

### 5. Test Kill Switch
- Go back to main dashboard
- Click red "KILL SWITCH" button
- See confirmation dialog
- Click "Emergency Stop"
- All jobs should stop

### 6. Resume Operations
- Click "Resume Operations" button (shown when kill switch active)
- Confirm resumption
- System ready for new jobs

---

## 📊 Verify Everything Works

### Check Routes Loaded
```bash
python << 'EOF'
from app import create_app

app = create_app()
control_routes = [str(r) for r in app.url_map if '/control' in str(r)]
print(f"\n✅ Found {len(control_routes)} control routes:\n")
for route in sorted(control_routes):
    print(f"  {route}")
EOF
```

### Check Service Layer
```bash
python << 'EOF'
from app.services.control_service import (
    TargetController, ReconController, IntelligenceController,
    TestingController, SafetyController, MonitoringController
)

controllers = [
    ('TargetController', TargetController),
    ('ReconController', ReconController),
    ('IntelligenceController', IntelligenceController),
    ('TestingController', TestingController),
    ('SafetyController', SafetyController),
    ('MonitoringController', MonitoringController),
]

print("\n✅ Service Layer Controllers:\n")
for name, controller in controllers:
    methods = [m for m in dir(controller) if not m.startswith('_')]
    print(f"  {name}: {len(methods)} methods")
EOF
```

### Check Models
```bash
python << 'EOF'
from app import create_app, db
from app.models.jobs import ReconJob, TestJob, IntelligenceCandidate, VerifiedFinding
from app.models.control import KillSwitch, ScopeEnforcer, RateLimiter
from app.models.phase1 import Target

app = create_app()
with app.app_context():
    print("\n✅ Database Models:\n")
    models = [
        ('Target', Target),
        ('ReconJob', ReconJob),
        ('TestJob', TestJob),
        ('IntelligenceCandidate', IntelligenceCandidate),
        ('VerifiedFinding', VerifiedFinding),
        ('KillSwitch', KillSwitch),
        ('ScopeEnforcer', ScopeEnforcer),
        ('RateLimiter', RateLimiter),
    ]
    
    for name, model in models:
        columns = [c.name for c in model.__table__.columns]
        print(f"  {name}: {len(columns)} columns")
EOF
```

---

## 🔧 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'app'"
**Fix**: Make sure you're in the project root directory
```bash
# Check you're in right place
cd c:\Users\user\OneDrive\Desktop\bug-auto-main
ls app/  # Should show __init__.py, models/, routes/, etc
```

### Issue: "OperationalError: table targets does not exist"
**Fix**: Create database tables
```bash
python << 'EOF'
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print("✅ Tables created")
EOF
```

### Issue: Flask not found or "No module named 'flask'"
**Fix**: Install dependencies
```bash
pip install flask flask-sqlalchemy flask-migrate
```

### Issue: "TypeError: This operation raised an exception of type OperationalError"
**Fix**: Delete old database and recreate it
```bash
# Delete old database
del bugbounty.db

# Recreate
python << 'EOF'
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print("✅ Fresh database created")
EOF
```

### Issue: Page returns 404
**Fix**: Check that target ID exists in the URL
```bash
# First, get valid target IDs
python << 'EOF'
from app import create_app
from app.models.phase1 import Target

app = create_app()
with app.app_context():
    targets = Target.query.all()
    print(f"Found {len(targets)} targets:")
    for t in targets:
        print(f"  ID {t.id}: {t.name}")
EOF

# Then use valid ID in URL
# http://localhost:5000/control/target/1  (if you have target with ID 1)
```

### Issue: "Jinja2 EnvironmentNotFound" or template not found
**Fix**: Make sure browser is requesting correct path
```
# Correct
http://localhost:5000/control/

# Wrong
http://localhost:5000/control.html
http://localhost:5000/dashboard
```

---

## 📚 Documentation

Want more detail? See:

- [DASHBOARD_README.md](DASHBOARD_README.md) - Complete feature guide (1300+ lines)
  - Detailed explanation of each phase
  - All routes and how to use them
  - Database model reference
  - Architecture overview

- [VERIFICATION.md](VERIFICATION.md) - Testing and deployment checklist (500+ lines)
  - Pre-deployment checks
  - Runtime tests
  - Common issues and solutions
  - Security validation

- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - What was built (2000+ lines)
  - Complete list of deliverables
  - Architecture overview
  - Files created/modified
  - Code quality metrics

---

## 🎬 Demo Workflow

### 1. Create Target
```bash
python << 'EOF'
from app import create_app, db
from app.models.phase1 import Target

app = create_app()
with app.app_context():
    target = Target(
        name='mydomain.com',
        target_url='https://mydomain.com',
        enabled=True
    )
    db.session.add(target)
    db.session.commit()
    print(f"Created target ID: {target.id}")
EOF
```

### 2. Navigate in Browser
```
http://localhost:5000/control/target/1
```

### 3. Click "Start" on Recon Module
- System creates QUEUED job in database
- Job appears in list with QUEUED status
- (In production with Celery, job would be submitted to worker)

### 4. View Job Monitor
```
http://localhost:5000/control/monitor/jobs
```

- See queued job in timeline
- Job status: QUEUED
- No results yet (job hasn't run)

### 5. Click "Stop" Button
- Job status changes to STOPPED
- Job removed from running jobs list
- Appears in history with STOPPED status

### 6. Try Kill Switch
```
http://localhost:5000/control/
```

- Click large red button: "KILL SWITCH"
- See confirmation: "Are you sure?"
- Click "Emergency Stop"
- Red banner appears: "EMERGENCY STOP ACTIVATED"
- Any new job start attempts fail with "Kill switch active"

### 7. Resume Operations
- Click "Resume Operations" on banner
- Or go to `/control/kill-switch/deactivate`
- Banner disappears
- Can start jobs again

---

## 💾 Database File Location

SQLite database created at:
```
c:\Users\user\OneDrive\Desktop\bug-auto-main\bugbounty.db
```

To inspect database directly:
```bash
# Using sqlite3
sqlite3 bugbounty.db

# Common queries in sqlite
sqlite> .tables           # Show all tables
sqlite> SELECT * FROM targets;  # Show targets
sqlite> SELECT COUNT(*) FROM recon_jobs;  # Count jobs
```

---

## 🚨 Emergency Stop

If something goes wrong:

### Option 1: Kill Server
```bash
# Press Ctrl+C in terminal
^C
```

### Option 2: Disable Target
```bash
python << 'EOF'
from app import create_app
from app.services.control_service import TargetController

app = create_app()
with app.app_context():
    success, msg = TargetController.disable_target(1)
    print(f"Disabled: {msg}")
EOF
```

### Option 3: Activate Kill Switch
```
http://localhost:5000/control/
# Click red Kill Switch button
```

---

## 📞 Need Help?

1. Check [DASHBOARD_README.md](DASHBOARD_README.md) for detailed guide
2. Check [VERIFICATION.md](VERIFICATION.md) for troubleshooting
3. Review error output from Flask server
4. Check `logs/` directory for error logs
5. Verify database file exists and is readable

---

## ✅ You're Ready!

```bash
# Start server
python -m flask --app app run --debug

# Open browser
# http://localhost:5000/control/

# You now have a professional SOC control center! 🎉
```

---

**Next Steps:**
- Explore all templates
- Test all phase controls
- Try kill switch
- Read detailed docs
- (Soon) Integrate Celery for async jobs

**Questions?** See the comprehensive docs:
- [DASHBOARD_README.md](DASHBOARD_README.md) - Full feature guide
- [VERIFICATION.md](VERIFICATION.md) - Testing checklist  
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical details

Enjoy! 🛡️
