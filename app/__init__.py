"""
Bug Bounty Platform - Application Factory
Unified control center for all phases (1-4)
"""
import os
from flask import Flask, redirect
from app.extensions import db, migrate

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bugbounty.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    register_blueprints(app)
    
    # Root routes
    @app.route('/')
    def index():
        return redirect('/dashboard')
    
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'database': 'connected'}
    
    return app

def register_blueprints(app):
    """Register all Flask blueprints"""
    
    # CORE: Control Center (NEW - UNIFIED DASHBOARD)
    try:
        from app.routes.control import control_bp
        app.register_blueprint(control_bp)
        app.logger.info('✅ Control Center registered')
    except ImportError as e:
        app.logger.error(f'❌ Control Center failed to load: {e}')
    
    # Phase 1: Targets API
    try:
        from routes.targets_api import targets_api
        app.register_blueprint(targets_api)
        app.logger.info('✅ Targets API registered')
    except ImportError as e:
        app.logger.warning(f'⚠️ Targets API not available: {e}')
    
    # Phase 2: Recon API
    try:
        from routes.recon_api_simple import recon_api
        app.register_blueprint(recon_api)
        app.logger.info('✅ Recon API registered')
    except ImportError as e:
        app.logger.warning(f'⚠️ Recon API not available: {e}')
    
    # Dashboard UI (legacy)
    try:
        from routes.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp)
        app.logger.info('✅ Dashboard UI registered')
    except ImportError as e:
        app.logger.warning(f'⚠️ Dashboard not available: {e}')

# Create app instance
app = create_app()

# Import models AFTER app creation to avoid circular imports
with app.app_context():
    from app.models.phase1 import Target, ScopeRule
    from app.models.jobs import ReconJob, IntelligenceCandidate, TestJob, VerifiedFinding
    from app.models.control import ScopeEnforcer, RateLimiter, KillSwitch
