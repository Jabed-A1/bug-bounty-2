"""Routes package - Blueprint registration"""
from flask import Blueprint

# Create blueprints
main_bp = Blueprint('main', __name__)
target_bp = Blueprint('targets', __name__, url_prefix='/targets')
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import routes to register them with blueprints
from . import main_routes
from . import target_routes
from . import api_routes

__all__ = ['main_bp', 'target_bp', 'api_bp']
