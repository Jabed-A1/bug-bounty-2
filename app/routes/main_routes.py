"""
Main dashboard routes
Homepage and overview statistics
"""
from flask import render_template, current_app
from app.routes import main_bp
from app.services import TargetService, AttackService
from app.models import ScanResult


@main_bp.route('/')
def index():
    """
    Main dashboard - overview of all targets and recent activity
    """
    # Get target statistics
    target_stats = TargetService.get_target_stats()
    
    # Get all targets
    targets = TargetService.get_all_targets()
    
    # Get recent scan results (last 10)
    recent_scans = AttackService.get_scan_results(limit=10)
    
    # Calculate additional stats
    total_scans = ScanResult.query.count()
    active_scans = ScanResult.query.filter_by(status='running').count()
    
    current_app.logger.info('Dashboard accessed')
    
    return render_template('dashboard/index.html',
                         target_stats=target_stats,
                         targets=targets,
                         recent_scans=recent_scans,
                         total_scans=total_scans,
                         active_scans=active_scans)


@main_bp.route('/about')
def about():
    """About page with system information"""
    return render_template('dashboard/about.html')
