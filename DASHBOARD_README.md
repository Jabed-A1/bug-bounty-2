# SOC Control Center Dashboard - Complete Rebuild

## Overview

The dashboard has been completely rebuilt as a **professional SOC (Security Operations Center) control center** for managing all phases of the bug bounty automation platform. This is not an analytics dashboard — it's an **operational control interface** where every action is intentional, confirmed, and traceable.

### Core Architecture

```
UI → Flask Route → Service Layer → Database Update → Response
```

**Key Principle**: The UI is the **single source of truth**. All state is read directly from the database, not cached or faked in JavaScript. Every button action writes to the database and the UI reflects the updated state immediately.

---

## Phase 1: Target Control

**Location**: `/control/target/<id>` or click "All Targets" from main dashboard

**What it controls**:
- **Enable/Disable**: Toggle if target can run ANY jobs (recon, testing)
- **Pause/Resume**: Pause ALL running/queued jobs for this target without disabling
- **View Active Jobs**: See all currently running/queued recon and test jobs
- **Scope Enforcement**: View which requests are allowed/blocked by scope rules
- **Rate Limiting**: See current requests/sec limit and configuration
- **Job History**: Browse past recon jobs and their results

**Key Features**:
- ✅ Enable/disable buttons require confirmation dialogs
- ✅ Pausing a target STOPS all running jobs atomically
- ✅ Active job counter shows real-time count from database
- ✅ Scope enforcer shows what's in/out of bounds
- ✅ Rate limiter displays current limits per target
- ✅ All timestamps show when actions occurred

**Safety Checks**:
```python
if not target.enabled or target.paused:
    # Cannot start recon jobs
    return error('Target is disabled or paused')
```

---

## Phase 2: Recon Module Control

**Location**: `/control/recon/<id>` or from target detail card

**What it controls**:
- **6 Recon Modules** (individual control):
  - subdomain_enum (Subdomain Enumeration)
  - livehost_detect (Live Host Detection)
  - port_scan (Port Scanning)
  - endpoint_collect (Endpoint Collection)
  - directory_fuzz (Directory Fuzzing)
  - js_analysis (JavaScript Analysis)

- **Per-Module Controls**:
  - Start button (creates QUEUED job)
  - Stop button (on running/queued jobs)
  - Status indicator (IDLE, QUEUED, RUNNING, DONE, FAILED, STOPPED)
  - Results counter (how many endpoints/ports discovered)
  - Progress percentage (0-100%)
  - Error messages (if job failed)
  - Duration timer (how long it's been running)

**Key Features**:
- ✅ Each module can run independently
- ✅ Start button disabled when target disabled/paused/kill switch active
- ✅ Stop button only appears on RUNNING/QUEUED jobs
- ✅ Auto-refresh every 5 seconds when jobs are running
- ✅ Each module shows its own state independently
- ✅ Past jobs listed with full history

**Safety Checks**:
```python
success, message, job_id = ReconController.start_recon_module(target_id, module)
# Checks:
# - Is kill switch active?
# - Is target enabled?
# - Is target paused?
# - Are there too many concurrent jobs?
```

---

## Phase 3: Intelligence Candidate Review

**Location**: `/control/intelligence/<id>` or from main dashboard

**What it controls**:
- **Pending Candidates**: Endpoints auto-discovered by Phase 2 recon
- **Manual Review**: Approve or reject each candidate
- **Approved Candidates**: Ready for Phase 4 testing
- **Rejected Candidates**: Will never be tested

**Workflow**:
1. Phase 2 creates IntelligenceCandidate records (pending review)
2. You see candidates with:
   - Endpoint URL
   - Confidence score (0-100%)
   - Why it was flagged (web form, authentication, API endpoint, etc)
   - Vulnerability indicators
3. Click **Approve** → Candidate marked for Phase 4 testing
4. Click **Reject** → Candidate marked as "do not test"

**Key Features**:
- ✅ Confidence score displayed with color coding (red=low, yellow=medium, green=high)
- ✅ Approve/Reject buttons require confirmation
- ✅ Shows how many candidates pending review
- ✅ Approved candidates table sorted by confidence
- ✅ Rejected candidates table with rejection reason
- ✅ Timestamps for when candidates were discovered and reviewed

**Safety Checks**:
```python
success, message = IntelligenceController.approve_candidate(candidate_id)
# Cannot approve if already approved
# Updates approved_at and reviewed_at timestamps
```

---

## Phase 4: Test Job Control & Finding Review

**Location**: `/control/testing/<id>` or from main dashboard

**What it controls**:
- **Test Jobs**: Run payload-based attacks on approved candidates
- **Payload Selection**: Choose attack type (XSS, SQL Injection, LFI, API, Auth, Other)
- **Findings Review**: Confirm/review discovered vulnerabilities

**Workflow**:
1. See all approved candidates ready for testing
2. Select payload type from dropdown
3. Click **Start Test** → TestJob created with QUEUED status
4. Tests run and send requests
5. If vulnerability found → VerifiedFinding created
6. Review findings: **Mark as Confirmed** (human verified) or **More Testing Needed**

**Test Job States**:
- **RUNNING**: Test actively sending requests
- **QUEUED**: Test waiting in queue
- **DONE**: Test completed (may have found vulnerability or not)
- **FAILED**: Test errored (rate limited, network error, etc)
- **STOPPED**: User manually stopped the test

**Finding States**:
- **Unreviewed**: Found by automated scanner, pending human review
- **Confirmed**: Human reviewed and confirmed real vulnerability
- **Rejected**: Human reviewed and determined it's false positive

**Key Features**:
- ✅ Payload dropdown only shows when approved candidates available
- ✅ Start button disabled if target not available or kill switch active
- ✅ Stop button on running/queued tests
- ✅ Auto-refresh every 5 seconds when tests running
- ✅ Findings split into unreviewed vs confirmed sections
- ✅ Severity color-coding (red=critical, orange=high, yellow=medium, blue=low)
- ✅ Findings show proof-of-concept code
- ✅ Timestamp for when findings were discovered

**Safety Checks**:
```python
success, message, job_id = TestingController.start_test(candidate_id, payload, target_id)
# Checks:
# - Is candidate approved?
# - Is kill switch active?
# - Is target available?
# - Is candidate already being tested?
```

---

## Global Safety: Kill Switch

**Location**: Main dashboard (large red button) or `/control/kill-switch/`

**What it does**:
- **EMERGENCY STOP**: Instantly stops ALL operations system-wide
- When activated:
  - All RUNNING jobs set to STOPPED
  - All QUEUED jobs set to STOPPED
  - All future start requests rejected with "Kill switch active" error
  - Red banner appears at top of all pages: "EMERGENCY STOP ACTIVATED"
  - Cannot start ANY new jobs until deactivated

**How to use**:
1. Large red button on dashboard
2. Click → "Are you sure?" confirmation
3. All running jobs stop immediately
4. Click "Resume Operations" button to deactivate

**Implementation**:
```python
# Every start request checks:
if KillSwitch.is_active():
    return {'success': False, 'error': 'System kill switch is ACTIVE'}

# Activating kill switch:
success, message, jobs_stopped = SafetyController.activate_kill_switch(reason)
# Returns number of jobs that were stopped
```

**Atomic Operation**:
- Single database write sets kill switch active
- Subsequent reads check this flag
- Transaction ensures no jobs start during activation
- Emergency-rated priority

---

## Real-Time Job Monitor

**Location**: `/control/monitor/jobs`

**What it shows**:
- **Status Summary**: Grid showing counts of all jobs by type and status
- **Live Job Timeline**: All recon and test jobs with live updates
- **Filtering**: View all, recon only, testing only, running only, failed only
- **Progress Tracking**: Progress bar for running jobs
- **Error Display**: Error messages for failed jobs
- **Vulnerability Found Badge**: Shows if test job found a vulnerability

**Features**:
- ✅ Auto-refresh every 3 seconds (configurable)
- ✅ Running jobs have animated pulse effect
- ✅ Filters switch dynamically without page reload
- ✅ Stop buttons on all running/queued jobs
- ✅ "Clear Completed" button removes done/failed from list
- ✅ Job timeline ordered by most recent first
- ✅ Duration shows elapsed time for running jobs

**Status Indicators**:
- 🟢 IDLE (not started)
- 🔵 QUEUED (waiting)
- 🟡 RUNNING (in progress)
- ✅ DONE (completed)
- ❌ FAILED (error occurred)
- ⏹️ STOPPED (user stopped)

---

## Main Control Dashboard

**Location**: `/control/` (Home page)

**What it shows**:
- **System Status**:
  - Kill switch status (red if active)
  - Overall operation health
  - Recent errors/warnings
  
- **Phase Overview Panels**:
  - Phase 1 (Targets): Total, Enabled, Paused
  - Phase 2 (Recon): Running, Queued, Idle, Failed
  - Phase 3 (Intelligence): Total candidates, Pending review, Approved, Rejected
  - Phase 4 (Testing): Tests running, Queued, Total findings, Unreviewed
  
- **Quick Action Cards**:
  - View all targets
  - View job monitor
  - Activate kill switch
  - Review pending candidates
  - Review unreviewed findings
  
- **Recent Activity Feeds**:
  - Latest recon jobs (started, completed, failed)
  - Latest test jobs (started, found vulnerability)
  - Latest findings (discovered, confirmed)
  
- **System Health**:
  - Active job counts
  - Worker status (Celery)
  - Last activity timestamps

**Features**:
- ✅ Auto-refresh every 10 seconds
- ✅ Color-coded status badges
- ✅ Links to detail pages
- ✅ Quick jump to problem areas
- ✅ Professional SOC layout with dark theme

---

## Database Models & State Management

### ReconJob
```python
target_id          # Which target
module             # Which module (subdomain_enum, etc)
status             # IDLE, QUEUED, RUNNING, DONE, FAILED, STOPPED
progress_percent   # 0-100
results_count      # How many endpoints/ports found
error_message      # If failed
celery_task_id     # Link to async job
created_at         # When job created
started_at         # When job started running
finished_at        # When job completed
```

### IntelligenceCandidate
```python
target_id              # Which target
endpoint_url           # The discovered endpoint
confidence_score       # 0-100 (AI confidence)
reason                 # Why flagged (web_form, auth, api, etc)
reviewed               # Has human reviewed?
approved_for_testing   # Can Phase 4 test this?
rejected               # Do not test
reviewed_at            # When human reviewed
approved_at            # When human approved
discovered_at          # When auto-discovered
```

### TestJob
```python
candidate_id           # Which candidate being tested
payload_category       # XSS, SQLi, LFI, API, Auth, Other
status                 # IDLE, QUEUED, RUNNING, DONE, FAILED, STOPPED
requests_sent          # How many requests
requests_received      # How many responses
vulnerability_found    # True if vuln discovered
error_message          # If failed
target_id              # Denormalized for queries
created_at             # When job created
started_at             # When started
finished_at            # When completed
```

### VerifiedFinding
```python
test_job_id            # Which test created this finding
vulnerability_type     # The type of vulnerability
severity               # Critical, High, Medium, Low
proof_of_concept       # The actual exploit/payload
human_reviewed         # Has human confirmed?
reviewed_at            # When human reviewed
discovered_at          # When auto-discovered
```

### KillSwitch
```python
active                 # True = system is stopped
activated_at           # When activated
deactivated_at         # When deactivated
reason                 # Why activated (optional)
```

### ScopeEnforcer
```python
target_id              # Per-target scope
allowed_count          # How many requests allowed
blocked_count          # How many requests blocked
last_blocked_url       # Most recent blocked request
```

### RateLimiter
```python
target_id              # Per-target rate limiting
requests_per_second    # Allowed rate
max_concurrent_jobs    # Max parallel job limit
current_requests_sec   # Current rate (read-only)
```

---

## Service Layer Architecture

**File**: `app/services/control_service.py`

All business logic is in the service layer, separate from routes:

### TargetController
```python
enable_target(target_id)      # Sets enabled=True
disable_target(target_id)     # Sets enabled=False
pause_target(target_id)       # Sets paused=True, stops running jobs
resume_target(target_id)      # Sets paused=False
can_target_run_jobs(target_id)# Returns bool: enabled AND NOT paused
```

### ReconController
```python
start_recon_module(target_id, module)  # Create QUEUED job (checks kill switch)
stop_recon_job(job_id)                 # Set to STOPPED
get_job_status(job_id)                 # Return current state
```

### IntelligenceController
```python
approve_candidate(candidate_id)        # Sets approved=True, reviewed=True
reject_candidate(candidate_id)         # Sets rejected=True, reviewed=True
add_candidate_note(candidate_id, note) # Adds user notes
```

### TestingController
```python
start_test(candidate_id, payload, target_id)  # Comprehensive checks + create job
stop_test(job_id)                             # Set to STOPPED
review_finding(finding_id, confirmed)         # Set human_reviewed
```

### SafetyController
```python
activate_kill_switch(reason)           # Emergency stop
deactivate_kill_switch()               # Resume operations
get_kill_switch_status()               # Return current state
setup_scope_enforcer(target_id)        # Initialize scope enforcement
setup_rate_limiter(target_id)          # Initialize rate limiting
```

### MonitoringController
```python
get_system_stats()                     # Return overall counts
get_target_activity(target_id)         # Return target-specific stats
```

---

## Integration with Celery (TODO)

All routes are marked with TODO comments showing where Celery tasks will be submitted:

```python
# TODO: Submit to Celery
# task = celery_app.send_task('recon.module_task', args=[job.id, target_id, module])
# job.celery_task_id = task.id
# db.session.commit()
```

**When Celery is integrated**:
1. Create AsyncResult handler to track task progress
2. Update `progress_percent` on ReconJob as task sends updates
3. Update `status` when task completes
4. Store `celery_task_id` for revoke on stop
5. Use `celery_app.control.revoke(task_id, terminate=True)` in stop routes

---

## Template Files

**Control Center Templates** (all located in `app/templates/control/`):

1. **dashboard.html** (650+ lines)
   - Main SOC dashboard
   - System status panels
   - Recent activity feeds
   - Kill switch control

2. **target_control.html** (500+ lines)
   - Phase 1 target management
   - Enable/disable/pause/resume controls
   - Active job viewing
   - Scope and rate limit config

3. **recon_control.html** (450+ lines)
   - Phase 2 module controls
   - 6 module cards with individual start/stop
   - Progress tracking
   - Job history

4. **intelligence_control.html** (400+ lines)
   - Phase 3 candidate review
   - Approve/reject workflow
   - Confidence score display
   - Pending/approved/rejected grouping

5. **testing_control.html** (600+ lines)
   - Phase 4 test job management
   - Payload selection
   - Finding review workflow
   - Unreviewed vs confirmed findings

6. **job_monitor.html** (500+ lines)
   - Real-time job timeline
   - Status summary grid
   - Filtering and auto-refresh
   - Stop controls on every job

---

## Routes Summary

```
GET  /control/                                    → Main dashboard
GET  /control/target/<id>                         → Phase 1 control panel
POST /control/target/<id>/enable                  → Enable target
POST /control/target/<id>/disable                 → Disable target
POST /control/target/<id>/pause                   → Pause target + stop jobs
POST /control/target/<id>/resume                  → Resume target

GET  /control/recon/<id>                          → Phase 2 control panel
POST /control/recon/<id>/start/<module>           → Start recon module
POST /control/recon/<id>/stop                     → Stop recon job

GET  /control/intelligence/<id>                   → Phase 3 control panel
POST /control/intelligence/candidate/<id>/approve → Approve candidate
POST /control/intelligence/candidate/<id>/reject  → Reject candidate

GET  /control/testing/<id>                        → Phase 4 control panel
POST /control/testing/<id>/start                  → Start test job
POST /control/testing/<id>/stop                   → Stop test job
POST /control/findings/<id>/review                → Mark finding reviewed

GET  /control/kill-switch/status                  → Get kill switch state
POST /control/kill-switch/activate                → EMERGENCY STOP
POST /control/kill-switch/deactivate              → Resume operations

GET  /control/monitor/jobs                        → Job monitor page
GET  /control/api/jobs/recent                     → JSON: recent job stats
```

---

## Key Design Decisions

### 1. No Fake State
**Decision**: UI reads from database only
**Why**: Users need to trust what they see. If the UI says a job is running, it needs to REALLY be running in the database. This prevents confusion and race conditions.

**Implementation**: Every template does `{{ job.status }}` not `{{ job.client_status }}`. The database is the only source of truth.

### 2. Confirmation Dialogs for Risky Actions
**Decision**: Enable/disable/pause/stop/approve/reject all require confirmation
**Why**: Prevents accidental termination of long-running operations

**Implementation**: JavaScript confirmation dialogs before POST requests

### 3. Per-Phase Granularity
**Decision**: Each phase has independent controls
**Why**: You might want to pause recon while testing runs, or review more candidates before testing

**Implementation**: Separate routes, templates, and service methods per phase

### 4. Kill Switch as Emergency Brakes
**Decision**: System-wide atomic stop, separate from individual target pause
**Why**: If one target is misbehaving (rate limited, detected), you need to stop EVERYTHING immediately

**Implementation**: Single KillSwitch row in database, checked on every operation start

### 5. Service Layer for Business Logic
**Decision**: All DB writes happen in service layer, not routes
**Why**: 
- Routes become thin and testable
- Business logic can be unit tested independently
- Easy to audit what the app can do
- Reusable across API endpoints

**Implementation**: All routes call service methods, get (bool, message, data) tuples

### 6. Auto-Refresh Polling
**Decision**: Templates don't WebSocket, they HTTP poll every N seconds
**Why**: 
- Simpler to implement and debug
- No dependency on WebSocket infrastructure
- UI can still work if server overloaded
- Celery integration straightforward

**Implementation**: `setInterval(()=>location.reload(), 5000)` in templates when jobs running

---

## Getting Started with the Control Center

### 1. Navigate to Control Dashboard
```
http://localhost:5000/control/
```

### 2. Create a Target (Phase 1)
- Go to "All Targets" → "New Target"
- Set target URL, scope rules
- Enable the target

### 3. Start Recon (Phase 2)
- Click target → "Recon Control"
- Select modules (or start all)
- Click "Start" on each module
- Watch progress in "Job Monitor"

### 4. Review Findings (Phase 3)
- Click target → "Intelligence Control"
- Review pending candidates
- Click "Approve" on endpoints to test
- Click "Reject" on false positives

### 5. Run Tests (Phase 4)
- Click target → "Testing Control"
- Select payload type
- Click "Start Test"
- Watch findings roll in

### 6. Emergency: Activate Kill Switch
- If anything goes wrong
- Click red button: "KILL SWITCH"
- Everything stops immediately
- Resume when ready

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Flask Application                         │
├─────────────────────┬───────────────────────┬───────────────┤
│ Routes              │ Service Layer         │ Database      │
│ (control.py)        │ (control_service.py)  │ (Models)      │
├─────────────────────┴───────────────────────┴───────────────┤
│                                                               │
│  GET  /control/          →  Dashboard          →  Read DB   │
│                                                               │
│  POST /target/<id>/pause →  TargetController    →  Update   │
│                          →  pause_target()      →  Target   │
│                                                   + Stop Jobs│
│                                                               │
│  POST /recon/.../start   →  ReconController     →  Create   │
│                          →  start_recon_module()→  ReconJob │
│                                                   (QUEUED)   │
│                                                               │
│  POST /intelligence/.../  →  Intelligence       →  Update   │
│       approve           →  Controller.approve() →  Candidate│
│                                                               │
│  POST /testing/.../start  →  TestingController  →  Create   │
│                          →  start_test()        →  TestJob  │
│                                                   (QUEUED)   │
│                                                               │
│  POST /kill-switch/       →  SafetyController   →  Atomic   │
│       activate          →  activate_kill_switch→  Update    │
│                                                   + Stop Jobs│
│                                                               │
│  GET  /monitor/jobs       →  Return Recent Jobs →  Read DB  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Monitoring & Debugging

### Check if Control Center is Working
```bash
# Check for import errors
python -c "from app import create_app; app = create_app(); print('OK')"

# Check routes registered
python -c "from app import create_app; app = create_app(); print([r for r in app.url_map])"

# Visit dashboard
curl http://localhost:5000/control/
```

### Check Database State
```python
from app import create_app, db
from app.models.jobs import ReconJob, TestJob
from app.models.control import KillSwitch

app = create_app()
with app.app_context():
    # Are there any running jobs?
    running = ReconJob.query.filter_by(status='RUNNING').all()
    print(f"Running recon jobs: {len(running)}")
    
    # Is kill switch active?
    switch = KillSwitch.query.first()
    print(f"Kill switch active: {switch.active if switch else False}")
```

### Common Issues

**Issue**: "Circular import error"
- **Check**: Did you import db from app.extensions, not flask_sqlalchemy?
- **Fix**: All models should: `from app.extensions import db`

**Issue**: Routes not registered
- **Check**: Does app/__init__.py have `app.register_blueprint(control_bp)`?
- **Fix**: Ensure control_bp is imported and registered BEFORE create_app returns

**Issue**: UI shows stale data after action
- **Check**: Is the route returning JSON? Is JavaScript reloading?
- **Fix**: Add `location.reload()` after successful action

**Issue**: Kill switch doesn't stop jobs
- **Check**: Are all start routes checking `if KillSwitch.is_active()`?
- **Fix**: Add check to every route that creates a job

---

## Next Steps: Celery Integration

When integrating Celery:

1. **Update ReconController.start_recon_module()**
   ```python
   job = ReconJob(...)
   db.session.add(job)
   db.session.flush()  # Get job.id without committing yet
   
   # Submit to Celery
   task = celery_app.send_task('recon.module_task', 
                               args=[job.id, target_id, module])
   job.celery_task_id = task.id
   job.status = 'QUEUED'  # Now it's really queued
   db.session.commit()
   ```

2. **Update ReconController.stop_recon_job()**
   ```python
   job = ReconJob.query.get(job_id)
   if job.celery_task_id:
       celery_app.control.revoke(job.celery_task_id, terminate=True)
   job.status = 'STOPPED'
   db.session.commit()
   ```

3. **Add progress tracking**
   ```python
   # In Celery task
   def recon_module_task(job_id, target_id, module):
       job = ReconJob.query.get(job_id)
       job.started_at = datetime.utcnow()
       job.status = 'RUNNING'
       db.session.commit()
       
       try:
           # Do work...
           job.progress_percent = 50
           db.session.commit()
           
           # More work...
           job.progress_percent = 100
           job.status = 'DONE'
           job.results_count = 42
           db.session.commit()
       except Exception as e:
           job.status = 'FAILED'
           job.error_message = str(e)
           db.session.commit()
   ```

---

## Files Modified/Created

**New Files**:
- `app/extensions.py` - Flask extensions
- `app/models/jobs.py` - Unified job models
- `app/models/control.py` - Safety models
- `app/routes/control.py` - All control routes
- `app/services/control_service.py` - Service layer
- `app/templates/control/dashboard.html` - Main dashboard
- `app/templates/control/target_control.html` - Phase 1 UI
- `app/templates/control/recon_control.html` - Phase 2 UI
- `app/templates/control/intelligence_control.html` - Phase 3 UI
- `app/templates/control/testing_control.html` - Phase 4 UI
- `app/templates/control/job_monitor.html` - Job timeline

**Modified Files**:
- `app/__init__.py` - Register control blueprint, fix imports
- `app/models/phase1.py` - Add control fields to Target
- `app/templates/base.html` - Update navigation to include control center

---

## Summary

This rebuilt dashboard transforms the application from an analytics tool into an **operational control center**. Every button is a conscious action, every state is real, and you have complete visibility and control over all phases of the bug bounty automation process.

**Key Guarantees**:
✅ UI always reflects database state
✅ All risky actions require confirmation
✅ Kill switch provides instant emergency stop
✅ Each phase independently controllable
✅ Professional SOC-grade appearance
✅ Real-time job monitoring
✅ Service layer architecture ready for testing and extension

Welcome to the Control Center. 🛡️
