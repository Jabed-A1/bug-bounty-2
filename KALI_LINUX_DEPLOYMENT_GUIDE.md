# 🐧 KALI LINUX DEPLOYMENT & USAGE GUIDE
## Bug Bounty Automation Platform  
**Complete Step-by-Step Setup & Daily Operations**

---

## 📋 TABLE OF CONTENTS
1. [System Requirements](#system-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Installation (Fresh Kali Linux)](#installation-fresh-kali-linux)
4. [First-Time Setup](#first-time-setup)
5. [Daily Workflow](#daily-workflow)
6. [Common Errors & Troubleshooting](#common-errors--troubleshooting)
7. [Command Reference](#command-reference)
8. [Monitoring & Logging](#monitoring--logging)
9. [Safety Procedures](#safety-procedures)
10. [Performance Tuning](#performance-tuning)

---

## 🖥️ SYSTEM REQUIREMENTS

### Hardware (Minimum)
```
CPU:        2+ cores
RAM:        4GB minimum (8GB recommended for concurrent jobs)
Disk:       50GB available (20GB for tools + 20GB for job results)
Network:    Stable internet connection required
```

### Hardware (Recommended)
```
CPU:        4+ cores
RAM:        16GB
Disk:       100GB+ SSD
Network:    Dedicated machine on your network (not laptop)
```

### Software
```
OS:         Kali Linux 2024.x or 2025.x
Kernel:     5.10+ (check with: uname -r)
Python:     3.10+ (usually default on Kali)
Database:   SQLite (local, built-in) or PostgreSQL (production)
Message Queue: Redis (required for job scheduling)
```

### Kali Linux Variants Tested
- ✅ Kali Linux 2024.3 (official)
- ✅ Kali Linux 2024.4 (official)
- ✅ Kali Linux on WSL2 (Windows)
- ✅ Kali Linux in VirtualBox (5GB vDisk minimum)
- ✅ Kali Linux in Proxmox

---

## ✅ PRE-DEPLOYMENT CHECKLIST

Before starting, verify:

```bash
# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y
# Should complete without errors

# 2. Check Python version
python3 --version
# Should be 3.10 or higher

# 3. Check network connectivity
ping -c 1 google.com
# Should get response

# 4. Check disk space
df -h /
# Should have 50GB+ free

# 5. Verify you can execute code
python3 -c "print('Python works')"
# Should print: Python works

# 6. Check if Redis is installable
sudo apt-cache search redis
# Should list redis-server package

# 7. Check if git is installed
git --version
# Should show version
```

If all pass: ✅ Ready to deploy  
If any fail: Install missing component first

---

## 📦 INSTALLATION (FRESH KALI LINUX)

### Step 1: Clone Project (5 minutes)

```bash
# Create projects directory
mkdir -p ~/projects
cd ~/projects

# Clone the project
git clone https://github.com/your-username/bug-auto.git
# Or if local folder:
cp -r /mnt/share/bug-auto ./bug-auto

cd bug-auto
```

### Step 2: Install System Dependencies (10 minutes)

```bash
# Update package lists
sudo apt-get update

# Install Python development headers (required for pip packages)
sudo apt-get install -y python3-dev python3-pip python3-venv

# Install Redis (message broker for Celery)
sudo apt-get install -y redis-server

# Install database development libraries
sudo apt-get install -y libpq-dev  # For PostgreSQL support (optional)

# Install common bug bounty tools
sudo apt-get install -y nmap ffuf curl wget

# Install system libraries needed by Python packages
sudo apt-get install -y build-essential libssl-dev libffi-dev
```

**Verify installation**:
```bash
python3 --version          # Python 3.x.x
pip3 --version             # pip 23.x+
redis-server --version     # redis-server v7.x+
nmap --version             # Nmap 7.x+
```

### Step 3: Create Python Virtual Environment (5 minutes)

```bash
# Navigate to project
cd ~/projects/bug-auto

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation (prompt should show (venv))
# Should see: (venv) user@kali:~/projects/bug-auto$
```

**Keep this shell tab open!** Virtual env must stay activated.

### Step 4: Install Python Dependencies (10 minutes)

```bash
# Ensure pip is latest
pip install --upgrade pip

# Install from requirements.txt
pip install -r requirements.txt

# If requirements.txt doesn't exist, install manually:
pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-Login
pip install celery redis
pip install requests beautifulsoup4 lxml
pip install click colorama
```

**Verify packages**:
```bash
python3 -c "import flask; print(f'Flask {flask.__version__}')"
python3 -c "import celery; print(f'Celery {celery.__version__}')"
python3 -c "import redis; print(f'Redis installed')"
```

### Step 5: Install Bug Bounty Tools (15 minutes)

```bash
# Basic tools from Kali repos
sudo apt-get install -y \
  subfinder \
  amass \
  httpx \
  gau \
  waybackurls \
  feroxbuster

# ffuf (directory fuzzer)
sudo apt-get install -y ffuf

# Note: katana might need pip installation
pip install katana-framework  # Or apt-get install katana-framework
```

**Verify tools**:
```bash
which subfinder    # Should return /usr/bin/subfinder
which nmap         # Should return /usr/bin/nmap
which ffuf         # Should return /usr/bin/ffuf
httpx --version    # Should show version
```

### Step 6: Initialize Database (5 minutes)

```bash
# Still in venv, in project root

# Set Flask app
export FLASK_APP=app

# Create database tables
flask db upgrade

# Or if first time (no migrations folder):
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Verify database created
ls -la instance/
# Should see: sqlite.db or similar
```

---

## ⚙️ FIRST-TIME SETUP

### Step 1: Start Redis (Required!)

**New terminal window 1** (keep open):
```bash
# Start Redis server
redis-server

# Should show:
# Redis server v7.x.x...
# READY to accept connections

# Leave this running in background - don't close this window!
```

**Verify Redis**: In another terminal:
```bash
redis-cli ping
# Should respond: PONG
```

### Step 2: Start Flask Application

**New terminal window 2** (keep open):
```bash
cd ~/projects/bug-auto

# Activate venv (if not already)
source venv/bin/activate

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=development  # or production
export FLASK_DEBUG=1

# Run Flask development server
flask run --host=0.0.0.0 --port=5000

# Should show:
# * Running on http://127.0.0.1:5000
# * Press CTRL+C to quit
```

**Verify Flask**: Open browser:
```
http://localhost:5000
# Should see: Bug Bounty Automation Dashboard
```

### Step 3: Start Celery Worker

**New terminal window 3** (keep open):
```bash
cd ~/projects/bug-auto

# Activate venv
source venv/bin/activate

# Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Should show workers starting:
# ...Celery v5.x.x (mem: ...MB)
# [Tasks]
#   . app.tasks.recon_tasks.task_subdomain_enumeration
#   . app.tasks.testing_tasks.task_run_test
# [2024-01-15 10:30:00,123: WARNING/MainProcess] ...Ready
```

**Verify Celery**: In another terminal:
```bash
celery -A app.celery_app inspect active
# Should respond with worker details
```

### Step 4: Access the Dashboard

**Open in browser**:
```
http://localhost:5000/dashboard
# Login if required
# Should see control center with 4 phases:
# - Phase 1: Target Management
# - Phase 2: Reconnaissance
# - Phase 3: Intelligence Review
# - Phase 4: Security Testing
```

### Post-Setup Verification

✅ Redis running (window 1)  
✅ Flask serving (window 2, accessible at :5000)  
✅ Celery worker running (window 3, seeing tasks)  
✅ Dashboard accessible (browser)  
✅ Database initialized (instance/sqlite.db exists)  
✅ All tools installed (which subfinder, etc)  

---

## 🎯 DAILY WORKFLOW

### Start of Day (All processes)

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Flask
cd ~/projects/bug-auto
source venv/bin/activate
export FLASK_APP=app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000

# Terminal 3: Celery Worker
cd ~/projects/bug-auto
source venv/bin/activate
celery -A app.celery_app worker --loglevel=info

# Terminal 4: Your operations (run commands in this terminal)
cd ~/projects/bug-auto
source venv/bin/activate
```

### Phase 1: Add Target

```
1. Open browser: http://localhost:5000/dashboard

2. Click: "Phase 1: Target Management"

3. Click: "Add New Target"

4. Fill in form:
   - Target URL: example.com (or IP address)
   - Scope: Define what subdomains/IPs are in scope
   - Type: Domain, IP Range, or Wildcard
   - Priority: HIGH, MEDIUM, LOW
   - Notes: Any special instructions

5. Click: "Create Target"

6. Verify: Target appears in list with "ENABLED" status
```

### Phase 2: Start Reconnaissance

```
1. From dashboard, click: "Phase 2: Reconnaissance"

2. Select target: example.com

3. Choose recon modules to run:
   ☑ Subdomain Enumeration (find subdomains)
   ☑ Live Host Detection (probe live hosts)
   ☑ Port Scanning (find open ports)
   ☑ Endpoint Collection (find URLs/paths)
   ☑ JavaScript Analysis (extract URLs from JS)
   ☑ Directory Fuzzing (brute force paths)

4. Click: "Start Recon" (green button)

5. You should see each module status:
   - Subdomain Enumeration: QUEUED → RUNNING → COMPLETED
   - Live Host Detection: QUEUED → RUNNING → COMPLETED
   - etc.

6. Monitor progress in: "Job Monitor" tab
   - Real-time status updates
   - Stop/pause individual modules if needed
```

**What happens in background**:
```
1. Flask confirms job created and returned job_id
2. Celery worker picks up the task
3. Task spawns subprocess for each tool (subfinder, nmap, etc)
4. Results written to database in real-time
5. UI updates via auto-refresh (check every 5 seconds)
```

### Phase 3: Review Intelligence Candidates

```
1. From dashboard, click: "Phase 3: Intelligence Review"

2. See all found endpoints/subdomains:
   - collected.subdomains (from subdomain enum)
   - collected.live_hosts (from live host detection)
   - collected.open_ports (from port scan)
   - collected.endpoints (from endpoint collection)
   - Attack Candidates (auto-identified endpoints that look vulnerable)

3. For each endpoint/candidate:
   - Review the endpoint path
   - Check if it's in-scope
   - Look at HTTP status code
   - Examine any interesting parameters

4. Click: "Approve as Testing Candidate" for endpoints you want to test

5. These become "Intelligence Candidates" ready for Phase 4
```

### Phase 4: Run Security Tests

```
1. From dashboard, click: "Phase 4: Security Testing"

2. See list of approved candidates from Phase 3

3. For each candidate:
   - Basic tests: SQL injection, XSS, command injection
   - Parameter fuzzing: All params with common payloads
   - Authentication: Bypass detection
   - Logic flaws: Price checks, privilege escalation

4. Click: "Run Tests" for candidate

5. Tests execute (takes minutes to hours depending on scope)

6. Review results in: "Verified Findings" tab
   - Only confirmed vulnerabilities show here
   - Manual validation required for each finding
   - No auto-exploitation (human-in-loop only)

7. Export findings:
   - Download PDF report
   - Save JSON for reference
   - Email to yourself for safekeeping
```

### Emergency Stop (Kill Switch)

```
If anything goes wrong:

1. Click red "KILL SWITCH" button (top right)

2. Immediately stops:
   - All running recon jobs
   - All running tests
   - All Celery tasks
   - All subprocesses

3. System goes "SAFE" mode (all targets paused)

4. Investigation:
   - Check logs: tail -f logs/error.log
   - Check Celery logs
   - Find what triggered issue
```

### End of Day

```bash
# Save your findings in Phase 4

# Review any errors
tail -f logs/app.log
tail -f logs/celery.log

# Stop services (Ctrl+C in each terminal):
# Terminal 1: Ctrl+C (stop Redis)
# Terminal 2: Ctrl+C (stop Flask)
# Terminal 3: Ctrl+C (stop Celery)

# Archive results if doing bug bounty
tar -czf results-2024-01-15.tar.gz instance/

# Backup database
cp instance/sqlite.db instance/sqlite.db.backup-2024-01-15
```

---

## 🐛 COMMON ERRORS & TROUBLESHOOTING

### Error 1: "Redis Connection Refused"

**Symptom**: Celery worker fails to start with `ConnectionError`

**Root cause**: Redis not running

**Fix**:
```bash
# Check if Redis is running
redis-cli ping
# If no response:

# Start Redis:
redis-server &

# Or if installed as service:
sudo systemctl start redis-server
sudo systemctl status redis-server

# Verify:
redis-cli ping
# Should respond: PONG
```

### Error 2: "Module not found: app.tasks"

**Symptom**: Flask/Celery fails with import error

**Root cause**: Virtual environment not activated or path issues

**Fix**:
```bash
# Verify venv activated
which python
# Should show: /home/user/projects/bug-auto/venv/bin/python

# If not:
source venv/bin/activate

# Verify paths
python -c "import sys; print(sys.path)"
# Should include: /home/user/projects/bug-auto

# If still broken:
cd ~/projects/bug-auto
deactivate  # Exit old venv
source venv/bin/activate  # Reactivate
```

### Error 3: "Job is stuck in QUEUED status"

**Symptom**: Start a recon job but it never becomes RUNNING

**Root cause**: Celery worker not running or not seeing the task

**Fix**:
```bash
# Check if Celery worker is running
ps aux | grep celery
# Should see: celery -A app.celery_app worker

# If not running:
celery -A app.celery_app worker --loglevel=info

# Check if tasks are registered
celery -A app.celery_app inspect registered_tasks

# If no tasks show, Celery can't find them:
# 1. Check import paths (see AUDIT_REPORT.md)
# 2. Restart Celery worker after fixing imports
# 3. Verify Python modules reload
```

### Error 4: "Database is locked"

**Symptom**: SQLite error preventing job creation

**Root cause**: Multiple processes accessing database simultaneously

**Fix**:
```bash
# Check who's accessing database
lsof instance/sqlite.db

# Stop conflicting processes:
sudo pkill -f "flask run"
sleep 2
flask run --host=0.0.0.0 --port=5000

# Or use PostgreSQL instead (recommended for production):
sudo apt-get install postgresql postgresql-contrib
# Follow PostgreSQL setup guide
```

### Error 5: "Tool not found: subfinder"

**Symptom**: Recon job fails, error mentions tool not found

**Root cause**: Tool not installed or not in PATH

**Fix**:
```bash
# Verify tool exists
which subfinder
# If blank, not installed:

# Install via apt
sudo apt-get install subfinder

# Or install via go
sudo apt-get install golang-go
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
export PATH=$PATH:~/go/bin

# Verify
subfinder --version
```

### Error 6: "No such file or directory: nmap"

**Symptom**: Port scan jobs fail

**Root cause**: nmap not installed

**Fix**:
```bash
sudo apt-get install nmap
which nmap  # Should show /usr/bin/nmap
nmap --version
```

### Error 7: "Permission denied" during tool execution

**Symptom**: nmap or other tools fail due to permissions

**Root cause**: Tools require elevated privileges

**Fix**:
```bash
# Option 1: Add user to sudoers (less secure)
sudo usermod -aG sudo $USER

# Option 2: Configure sudo for specific commands (more secure)
sudo visudo
# Add line:
# your_user ALL=(ALL) NOPASSWD: /usr/bin/nmap

# Option 3: Run Flask/Celery as root (NOT RECOMMENDED)
sudo celery -A app.celery_app worker
# Not recommended - security risk!

# Best: Use option 2 for minimal sudo requirements
```

### Error 8: "port 5000 already in use"

**Symptom**: Flask won't start, error says port in use

**Root cause**: Old Flask process still running or other app using port

**Fix**:
```bash
# Find what's using port 5000
sudo lsof -i :5000
# Shows process using port

# Kill old Flask process
sudo kill -9 <PID>

# Or use different port
flask run --host=0.0.0.0 --port=5001

# Check port is free
netstat -tuln | grep 5000
# Should show nothing
```

### Error 9: "ImportError: No module named 'flask'"

**Symptom**: Python can't find Flask even after pip install

**Root cause**: Virtual env not activated or different Python interpreter

**Fix**:
```bash
# Verify which Python is being used
which python
# Should show: /home/user/projects/bug-auto/venv/bin/python
# If not, venv not activated

# Activate venv
source venv/bin/activate

# Verify packages
pip list | grep Flask
# Should show Flask package

# If still broken:
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Error 10: "Database migration failed"

**Symptom**: "flask db upgrade" fails

**Root cause**: Missing migration files or database corruption

**Fix**:
```bash
# Option 1: Fresh start (DELETE ALL DATA)
rm instance/sqlite.db
rm -rf migrations/
flask db init
flask db migrate -m "Initial"
flask db upgrade

# Option 2: Repair existing migrations
flask db stamp head
# Then try upgrade again

# Option 3: Check migration integrity
ls -la migrations/versions/
# Should have migration files like "1234_initial.py"
```

---

## 📚 COMMAND REFERENCE

### Startup Commands

```bash
# 1. Start Redis (Terminal 1)
redis-server

# 2. Start Flask (Terminal 2)
cd ~/projects/bug-auto
source venv/bin/activate
export FLASK_APP=app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000

# 3. Start Celery (Terminal 3)
cd ~/projects/bug-auto
source venv/bin/activate
celery -A app.celery_app worker --loglevel=info

# 4. Operations terminal (Terminal 4)
cd ~/projects/bug-auto
source venv/bin/activate
```

### Monitoring Commands

```bash
# Check Redis status
redis-cli ping

# Check Celery workers
celery -A app.celery_app inspect active

# Check Celery tasks
celery -A app.celery_app inspect registered_tasks

# Check Flask logs
tail -f logs/app.log

# Check Celery logs
tail -f logs/celery.log

# Check running processes
ps aux | grep -E 'redis|flask|celery'

# Check port usage
netstat -tuln | grep -E ':5000|:6379'

# Check database size
du -h instance/sqlite.db

# Check disk space
df -h /
```

### Database Commands

```bash
# Connect to SQLite
sqlite3 instance/sqlite.db

# List tables
.tables

# Check target count
SELECT COUNT(*) FROM target;

# Find a target
SELECT * FROM target WHERE target_url='example.com';

# Check job status
SELECT id, target_id, module_name, status FROM recon_job LIMIT 10;

# Count jobs
SELECT status, COUNT(*) FROM recon_job GROUP BY status;

# Exit
.quit
```

### Emergency Commands

```bash
# Force stop all toolprocesses
pkill -f subfinder
pkill -f nmap
pkill -f ffuf

# Force stop Celery workers
pkill -f 'celery worker'

# Force stop Flask
pkill -f 'flask run'

# Clear Redis cache
redis-cli FLUSHDB

# Restart everything
pkill -f 'redis\|flask\|celery'
sleep 5
redis-server &
flask run --host=0.0.0.0 --port=5000 &
celery -A app.celery_app worker --loglevel=info
```

---

## 📊 MONITORING & LOGGING

### Log Locations

```bash
# Application logs
logs/app.log

# Celery task logs
logs/celery.log

# Error logs
logs/error.log

# Database transactions
logs/db.log (if enabled)

# Redis logs
/var/log/redis/redis-server.log (if systemd)
```

### Real-time Monitoring

```bash
# Watch Flask requests
tail -f logs/app.log | grep -i request

# Watch Celery tasks
tail -f logs/celery.log | grep -E 'Received|Task|SUCCESS|FAILURE'

# Watch for errors
tail -f logs/error.log

# Combined monitoring (4-window setup)
# Window 1: Flask requests
tail -f logs/app.log

# Window 2: Celery tasks
tail -f logs/celery.log

# Window 3: Errors
tail -f logs/error.log

# Window 4: Send test command
while true; do sqlite3 instance/sqlite.db "SELECT COUNT(*) FROM target;" && sleep 5; done
```

### Dashboard Statistics

The control center dashboard shows:
- **Phase 1**: # targets, enabled/disabled status
- **Phase 2**: # running recon jobs, modules in progress
- **Phase 3**: # intelligence candidates waiting review
- **Phase 4**: # testing jobs completed, # findings verified

### Performance Metrics

```bash
# Check Celery queue depth (how many jobs waiting)
redis-cli LLEN celery

# Check database size growth
du -sh instance/sqlite.db

# Check memory usage
free -h

# Check process resource usage
top -b -n 1 | grep -E 'redis|python|celery'

# Check disk I/O for database
iostat -x 1
```

---

## 🔒 SAFETY PROCEDURES

### Kill Switch Procedure

**When to use**:
- A job is causing issues
- You need to halt all operations immediately
- System appears unstable
- You discovered a target is actually out-of-scope

**How to use**:
```
1. Click red "KILL SWITCH" button in dashboard (top right)
2. Confirm action when prompted
3. All jobs immediately paused
4. System enters SAFE mode
5. Click "Resume Operations" when ready
```

### Scope Management

```
1. Before adding target: Define scope
   - In-scope: example.com, *.example.com, 192.168.1.0/24
   - Out-of-scope: competitor.com, internal.com, aws.amazon.com

2. Target enable/disable:
   - Disable a target to prevent recon
   - Re-enable when scope expanded

3. Target pause/resume:
   - Pause temporarily to investigate issue
   - Resume when cleared

4. Scope enforcement (safety):
   - Recon jobs reject hosts outside scope
   - Rate limiting prevents DoS-like testing
```

### Backup & Recovery

```bash
# Daily backup (recommended)
cp instance/sqlite.db instance/sqlite.db.backup-$(date +%Y%m%d)

# Weekly archive
tar -czf bug-auto-backup-$(date +%Y%m%d).tar.gz \
  instance/ \
  logs/ \
  config/

# Store backup off-machine (USB, cloud, NAS)
scp bug-auto-backup-*.tar.gz backup_server:~/backups/

# Recovery procedure (if database corrupted)
rm instance/sqlite.db
cp instance/sqlite.db.backup-YYYYMMDD instance/sqlite.db
# Then restart Flask/Celery
```

### Rate Limiting

The system automatically limits:
- HTTP requests per second per target
- Concurrent subdomains being enumerated
- Port scan concurrency
- Directory fuzz rate

Configure limits in dashboard (Phase 1 → Target Settings):
```
Requests per second: 10 (default)
Concurrent jobs: 3 (default)
Timeout per check: 30 seconds (default)
```

---

## ⚡ PERFORMANCE TUNING

### For High-Load / Large Scope

```bash
# Increase Celery worker processes
celery -A app.celery_app worker --concurrency=4 --loglevel=info

# Increase concurrency for tools (in config)
# Edit config/settings.py
RECON_CONCURRENCY = 10  # Default: 3
SCAN_TIMEOUT = 60       # Default: 30
RATE_LIMIT_RPS = 20     # Default: 10

# Use PostgreSQL instead of SQLite
# SQLite gets slow with >100k records
# Consider upgrade to PostgreSQL for production
```

### Disk Space Management

```bash
# Archive old results monthly
tar -czf results-archive-2024-01.tar.gz \
  --exclude venv \
  --exclude .git \
  .

# Move to external storage
mv results-archive-*.tar.gz /mnt/external-drive/archives/

# Clean old logs
find logs/ -name "*.log.*" -mtime +30 -delete

# Check database size
sqlite3 instance/sqlite.db "SELECT ROUND(page_count * page_size / 1024.0 / 1024.0, 2) as db_size_mb FROM pragma_page_count(), pragma_page_size();"

# If >5GB, export and reimport to clean up
# This removes fragmentation
```

### Memory Optimization

```bash
# Monitor memory usage
watch -n 1 'free -h && echo "---" && ps aux | grep -E "celery|python|redis" | grep -v grep'

# If memory issues, restart Celery
pkill -f 'celery worker'
sleep 3
celery -A app.celery_app worker --loglevel=info

# Enable memory monitoring in Celery
celery -A app.celery_app worker --max-memory-per-child=512000
# Restarts worker after using 512MB
```

---

## 📞 SUPPORT & DEBUGGING

### Getting Help

If something breaks:

1. **Check logs first**:
   ```bash
   tail -f logs/app.log logs/celery.log logs/error.log
   ```

2. **Check common issues** (section above)

3. **Verify all services running**:
   ```bash
   redis-cli ping                    # Should: PONG
   curl http://localhost:5000        # Should: HTML response
   celery -A app.celery_app inspect active  # Should: Worker info
   ```

4. **Restart if unsure**:
   ```bash
   pkill -f 'redis\|flask\|celery'
   redis-server &
   flask run --host=0.0.0.0 --port=5000 &
   celery -A app.celery_app worker --loglevel=info &
   ```

5. **Check database integrity**:
   ```bash
   sqlite3 instance/sqlite.db "PRAGMA integrity_check;"
   # Should respond: ok
   ```

### Debug Mode

```bash
# Enable debug logging
export FLASK_DEBUG=1
export CELERY_LOG_LEVEL=DEBUG

# Run with verbose output
celery -A app.celery_app worker --loglevel=debug
```

---

## 🎓 KALI LINUX QUICK REFERENCE

### Key Kali Commands

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install new tools
sudo apt-get install [package-name]

# Check installed tool
which [tool-name]

# Run recon tool manually
nmap -sV -sC target.com
ffuf -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -u http://target.com/FUZZ

# Check for tool updates
sudo apt-get update && apt list --upgradable
```

### Useful Wordlists (Built-in)

```
/usr/share/wordlists/dirbrute/common.txt
/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
/usr/share/wordlists/rockyou.txt
/usr/share/wordlists/SecLists/Discovery/DNS/subdomains-top1million-5000.txt
```

### Firewall Considerations

```bash
# If behind firewall, tools might be blocked
# Check if outbound HTTP/HTTPS allowed:
curl https://google.com

# If tests fail, check:
sudo iptables -L
sudo ufw status

# Disable firewall for testing (if safe):
sudo ufw disable
```

---

## 🏁 CHECKLISTS

### Daily Startup Checklist

- [ ] Boot Kali Linux / SSH into KaliVM
- [ ] Open 4 terminal windows
- [ ] Terminal 1: `redis-server`
- [ ] Terminal 2: Activate venv + `flask run`
- [ ] Terminal 3: Activate venv + `celery worker`
- [ ] Terminal 4: Activate venv for commands
- [ ] Open browser: http://localhost:5000
- [ ] See dashboard with 4 phases
- [ ] Add today's target
- [ ] Start recon

### Weekly Maintenance Checklist

- [ ] Backup database: `cp instance/sqlite.db logs/backups/`
- [ ] Check logs for errors: `tail -f logs/error.log`
- [ ] Verify all tools still working: `which subfinder nmap ffuf`
- [ ] Update Kali: `sudo apt-get update && upgrade -y`
- [ ] Check disk space: `df -h /`
- [ ] Archive old results if >10GB
- [ ] Update `requirements.txt` if new packages added

### Pre-Bug-Bounty Checklist

- [ ] Verify target is in-scope with program
- [ ] Set Kill Switch ready to press
- [ ] Verify scope defined correctly in system
- [ ] Run quick test recon on example.com first
- [ ] Verify findings display correctly
- [ ] Backup database before starting
- [ ] Review export format for this program
- [ ] Have contact info for program if issues

---

## 📋 CONCLUSION

The Bug Bounty Automation Platform is ready for **Kali Linux deployment** after:

1. ✅ **Installing tools** (apt-get commands above)
2. ✅ **Starting Redis** (message broker)
3. ✅ **Starting Flask** (web interface)
4. ✅ **Starting Celery** (job execution)
5. ✅ **Using dashboard** (same workflow as above)

**Estimated setup time**: 30-45 minutes from fresh Kali  
**Issues expected**: Maybe 1-2 import/path issues (documented above)  
**Time to full operation**: 1 hour total

**Remember**: Always keep all 3 services running (Redis, Flask, Celery) for automation to work!

---

**Guide Complete** - Happy bug hunting! 🏆
