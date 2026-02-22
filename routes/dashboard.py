from flask import Blueprint, render_template_string, request, redirect
from app import db
from app.models.phase1 import Target
import json
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def index():
    targets = Target.query.all()
    stats = {
        'total_targets': Target.query.count(),
        'active_targets': Target.query.filter_by(status='active').count()
    }
    recent_targets = Target.query.order_by(Target.created_at.desc()).limit(5).all()
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Bug Bounty Platform</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f1419; color: #e8eaed; margin: 0; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #00d4aa; }
        .card { background: #1a1f2e; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .btn { padding: 10px 20px; background: #00d4aa; color: #0f1419; text-decoration: none; border-radius: 6px; display: inline-block; margin-right: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #2d3748; }
        th { background: #242b3d; color: #00d4aa; }
        .nav { background: #1a1f2e; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .nav a { padding: 10px 20px; background: #242b3d; color: #e8eaed; text-decoration: none; border-radius: 6px; margin-right: 10px; }
        .badge { padding: 4px 10px; border-radius: 4px; font-size: 12px; background: rgba(0, 212, 170, 0.2); color: #00d4aa; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ Bug Bounty Platform</h1>
        
        <div class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/targets">Targets</a>
            <a href="/recon/jobs">Recon Jobs</a>
            <a href="/api-test">API Test</a>
        </div>
        
        <div class="card">
            <h2>System Overview</h2>
            <table>
                <tr><td><strong>Total Targets</strong></td><td>{{ stats.total_targets }}</td></tr>
                <tr><td><strong>Active Targets</strong></td><td>{{ stats.active_targets }}</td></tr>
                <tr><td><strong>Status</strong></td><td><span class="badge">Online</span></td></tr>
            </table>
        </div>
        
        <div class="card">
            <h2>Quick Actions</h2>
            <a href="/targets" class="btn">Manage Targets</a>
            <a href="/targets/new" class="btn">Add Target</a>
            <a href="/recon/jobs" class="btn">View Recon Jobs</a>
        </div>
        
        <div class="card">
            <h2>Recent Targets</h2>
            <table>
                <thead>
                    <tr><th>ID</th><th>Domain</th><th>Name</th><th>Status</th></tr>
                </thead>
                <tbody>
                    {% for target in recent_targets %}
                    <tr>
                        <td>{{ target.id }}</td>
                        <td><strong>{{ target.domain }}</strong></td>
                        <td>{{ target.name }}</td>
                        <td><span class="badge">{{ target.status }}</span></td>
                    </tr>
                    {% else %}
                    <tr><td colspan="4" style="text-align: center;">No targets yet</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
    ''', stats=stats, recent_targets=recent_targets)


@dashboard_bp.route('/targets')
def targets_list():
    targets = Target.query.all()
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Targets</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f1419; color: #e8eaed; margin: 0; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #00d4aa; }
        .card { background: #1a1f2e; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .btn { padding: 10px 20px; background: #00d4aa; color: #0f1419; text-decoration: none; border-radius: 6px; display: inline-block; margin: 5px; border: none; cursor: pointer; font-size: 14px; }
        .btn-danger { background: #ff4444; color: white; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #2d3748; }
        th { background: #242b3d; color: #00d4aa; }
        .nav { background: #1a1f2e; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .nav a { padding: 10px 20px; background: #242b3d; color: #e8eaed; text-decoration: none; border-radius: 6px; margin-right: 10px; }
        .badge { padding: 4px 10px; border-radius: 4px; font-size: 12px; background: rgba(0, 212, 170, 0.2); color: #00d4aa; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Targets</h1>
        
        <div class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/targets">Targets</a>
            <a href="/recon/jobs">Recon Jobs</a>
        </div>
        
        <div class="card">
            <a href="/targets/new" class="btn">+ Add New Target</a>
            
            <table>
                <thead>
                    <tr><th>ID</th><th>Domain</th><th>Name</th><th>Status</th><th>Actions</th></tr>
                </thead>
                <tbody>
                    {% for target in targets %}
                    <tr>
                        <td>{{ target.id }}</td>
                        <td><strong>{{ target.domain }}</strong></td>
                        <td>{{ target.name }}</td>
                        <td><span class="badge">{{ target.status }}</span></td>
                        <td>
                            <a href="/targets/{{ target.id }}" class="btn">View</a>
                            <a href="/targets/{{ target.id }}/edit" class="btn">Edit</a>
                            <form method="POST" action="/targets/{{ target.id }}/delete" style="display:inline;" onsubmit="return confirm('Delete?');">
                                <button type="submit" class="btn btn-danger">Delete</button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="5" style="text-align: center;">No targets yet</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
    ''', targets=targets)


@dashboard_bp.route('/targets/<int:target_id>')
def target_detail(target_id):
    target = Target.query.get_or_404(target_id)
    
    # Parse scope rules
    try:
        scope_rules = json.loads(target.scope_rules) if target.scope_rules else {}
        in_scope = scope_rules.get('in_scope', [])
        out_scope = scope_rules.get('out_of_scope', [])
    except:
        in_scope = []
        out_scope = []
    
    # Get recon statistics - THIS CODE MUST BE INSIDE THE FUNCTION!
    from app.models.recon_simple import ReconJob, Subdomain
    recon_jobs_count = ReconJob.query.filter_by(target_id=target_id).count()
    subdomains_count = Subdomain.query.filter_by(target_id=target_id).count()
    running_jobs = ReconJob.query.filter_by(target_id=target_id, status='RUNNING').count()
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>{{ target.domain }}</title>
    <style>
        body { font-family: Arial; background: #0f1419; color: #e8eaed; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1, h2 { color: #00d4aa; }
        .card { background: #1a1f2e; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .btn { padding: 10px 20px; background: #00d4aa; color: #0f1419; text-decoration: none; border-radius: 6px; display: inline-block; margin: 5px; border: none; cursor: pointer; }
        .btn-danger { background: #ff4444; color: white; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        td { padding: 10px; border-bottom: 1px solid #2d3748; }
        .nav { background: #1a1f2e; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .nav a { padding: 10px 20px; background: #242b3d; color: #e8eaed; text-decoration: none; border-radius: 6px; margin-right: 10px; }
        ul { margin-left: 20px; color: #9aa0a6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ target.domain }}</h1>
        
        <div class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/targets">Targets</a>
            <a href="/recon/jobs?target_id={{ target.id }}">Recon Jobs</a>
        </div>
        
        <div class="card">
            <h2>Target Information</h2>
            <table>
                <tr><td><strong>Domain</strong></td><td>{{ target.domain }}</td></tr>
                <tr><td><strong>Name</strong></td><td>{{ target.name }}</td></tr>
                <tr><td><strong>Status</strong></td><td>{{ target.status }}</td></tr>
            </table>
            <div style="margin-top: 20px;">
                <a href="/targets/{{ target.id }}/edit" class="btn">Edit</a>
                <a href="/targets" class="btn">Back</a>
                <form method="POST" action="/targets/{{ target.id }}/delete" style="display:inline;" onsubmit="return confirm('Delete?');">
                    <button type="submit" class="btn btn-danger">Delete</button>
                </form>
            </div>
        </div>
        
        <div class="card">
            <h2>🚀 Start Recon</h2>
            <p style="color: #9aa0a6;">
                Jobs: {{ recon_jobs_count }} | Subdomains: {{ subdomains_count }} | Running: {{ running_jobs }}
            </p>
            
            <button onclick="startRecon()" class="btn" style="background: #4da6ff; color: white; font-weight: 600;">
                🔍 Start Subdomain Enumeration
            </button>
            
            <a href="/recon/jobs?target_id={{ target.id }}" class="btn">View Recon Jobs</a>
            
            <div id="status" style="margin-top: 15px; padding: 10px; display: none; border-radius: 6px;"></div>
        </div>
        
        <div class="card">
            <h2>📋 Scope</h2>
            <h3 style="font-size: 16px;">In Scope:</h3>
            <ul>{% for s in in_scope %}<li>{{ s }}</li>{% else %}<li>None</li>{% endfor %}</ul>
            <h3 style="font-size: 16px;">Out of Scope:</h3>
            <ul>{% for s in out_scope %}<li>{{ s }}</li>{% else %}<li>None</li>{% endfor %}</ul>
        </div>
    </div>
    
    <script>
    async function startRecon() {
        const statusDiv = document.getElementById('status');
        statusDiv.style.display = 'block';
        statusDiv.style.background = 'rgba(77, 166, 255, 0.1)';
        statusDiv.style.color = '#4da6ff';
        statusDiv.innerHTML = '⏳ Starting...';
        
        try {
            const response = await fetch('/api/recon/targets/{{ target.id }}/start-subdomain', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                statusDiv.style.background = 'rgba(0, 212, 170, 0.1)';
                statusDiv.style.color = '#00d4aa';
                statusDiv.innerHTML = '✅ ' + data.message + ' (Job #' + data.job_id + ')';
                setTimeout(() => location.reload(), 2000);
            } else {
                statusDiv.style.background = 'rgba(255, 68, 68, 0.1)';
                statusDiv.style.color = '#ff4444';
                statusDiv.innerHTML = '❌ Error: ' + data.message;
            }
        } catch (error) {
            statusDiv.style.background = 'rgba(255, 68, 68, 0.1)';
            statusDiv.style.color = '#ff4444';
            statusDiv.innerHTML = '❌ Error: ' + error.message;
        }
    }
    </script>
</body>
</html>
    ''', target=target, in_scope=in_scope, out_scope=out_scope,
         recon_jobs_count=recon_jobs_count, subdomains_count=subdomains_count, running_jobs=running_jobs)


# Add other dashboard functions (target_create, target_edit, etc.) here
# Copy them from your old dashboard.py file

@dashboard_bp.route('/recon/jobs')
def recon_jobs_list():
    """Recon jobs page"""
    from app.models.recon_simple import ReconJob
    from app.models.phase1 import Target
    
    jobs = ReconJob.query.order_by(ReconJob.created_at.desc()).limit(100).all()
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Recon Jobs</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: Arial; background: #0f1419; color: #e8eaed; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #00d4aa; }
        .card { background: #1a1f2e; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #2d3748; }
        th { background: #242b3d; color: #00d4aa; }
        .badge { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .badge-created { background: rgba(255, 170, 0, 0.2); color: #ffaa00; }
        .badge-running { background: rgba(77, 166, 255, 0.2); color: #4da6ff; }
        .badge-done { background: rgba(0, 212, 170, 0.2); color: #00d4aa; }
        .badge-failed { background: rgba(255, 68, 68, 0.2); color: #ff4444; }
        .nav { background: #1a1f2e; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .nav a { padding: 10px 20px; background: #242b3d; color: #e8eaed; text-decoration: none; border-radius: 6px; margin-right: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Recon Jobs</h1>
        
        <div class="nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/targets">Targets</a>
            <a href="/recon/jobs">Recon Jobs</a>
        </div>
        
        <div class="card">
            <p style="color: #4da6ff;">⏱️ Auto-refreshing every 5 seconds</p>
            
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Target</th>
                        <th>Stage</th>
                        <th>Status</th>
                        <th>Results</th>
                        <th>Started</th>
                    </tr>
                </thead>
                <tbody>
                    {% for job in jobs %}
                    <tr>
                        <td>#{{ job.id }}</td>
                        <td>Target #{{ job.target_id }}</td>
                        <td>{{ job.stage }}</td>
                        <td><span class="badge badge-{{ job.status.lower() }}">{{ job.status }}</span></td>
                        <td>{{ job.results_count }}</td>
                        <td>{{ job.started_at.strftime('%H:%M:%S') if job.started_at else '-' }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="6" style="text-align: center; padding: 40px;">No jobs yet</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
    ''', jobs=jobs, Target=Target)
