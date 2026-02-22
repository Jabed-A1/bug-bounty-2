"""
Flask extensions initialization
Extensions are initialized here and imported by the app factory
This pattern allows for proper initialization order and testing
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize extensions (without app binding)
db = SQLAlchemy()
migrate = Migrate()


def init_extensions(app):
    """
    Initialize all Flask extensions with the app instance
    
    Args:
        app: Flask application instance
    """
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Future extensions can be added here:
    # jwt.init_app(app)
    # limiter.init_app(app)
    # celery.init_app(app)
