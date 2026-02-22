"""
Scope Service
Business logic for scope management
"""
from app.extensions import db
from app.models import Scope, Target
from sqlalchemy.exc import SQLAlchemyError


class ScopeService:
    """Service class for scope operations"""
    
    @staticmethod
    def add_scope(target_id, scope_type, value, in_scope=True, notes=None, priority=5):
        """
        Add a scope entry to a target
        
        Args:
            target_id: Target ID
            scope_type: Type of scope (domain, wildcard, url, api, etc.)
            value: The scope value
            in_scope: Whether this is in scope (True) or out of scope (False)
            notes: Optional notes
            priority: Priority level (1-10)
            
        Returns:
            tuple: (scope, error_message)
        """
        try:
            # Validate target exists
            target = Target.query.get(target_id)
            if not target:
                return None, "Target not found"
            
            # Validate required fields
            if not scope_type or not value:
                return None, "Scope type and value are required"
            
            # Validate scope type
            if scope_type not in Scope.get_scope_types():
                return None, f"Invalid scope type: {scope_type}"
            
            # Create scope
            scope = Scope(
                target_id=target_id,
                scope_type=scope_type,
                value=value.strip(),
                in_scope=in_scope,
                notes=notes,
                priority=priority
            )
            
            db.session.add(scope)
            db.session.commit()
            return scope, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
    
    @staticmethod
    def get_scope(scope_id):
        """
        Get scope by ID
        
        Args:
            scope_id: Scope ID
            
        Returns:
            Scope or None
        """
        return Scope.query.get(scope_id)
    
    @staticmethod
    def get_target_scopes(target_id, in_scope=None):
        """
        Get all scopes for a target
        
        Args:
            target_id: Target ID
            in_scope: Filter by in_scope status (optional)
            
        Returns:
            list of Scope objects
        """
        query = Scope.query.filter_by(target_id=target_id)
        
        if in_scope is not None:
            query = query.filter_by(in_scope=in_scope)
        
        return query.order_by(Scope.priority.desc(), Scope.created_at).all()
    
    @staticmethod
    def update_scope(scope_id, **kwargs):
        """
        Update scope fields
        
        Args:
            scope_id: Scope ID
            **kwargs: Fields to update
            
        Returns:
            tuple: (scope, error_message)
        """
        try:
            scope = Scope.query.get(scope_id)
            
            if not scope:
                return None, "Scope not found"
            
            # Update allowed fields
            allowed_fields = ['scope_type', 'value', 'in_scope', 'notes', 'priority']
            
            for key, value in kwargs.items():
                if key in allowed_fields and value is not None:
                    setattr(scope, key, value)
            
            db.session.commit()
            return scope, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
    
    @staticmethod
    def delete_scope(scope_id):
        """
        Delete a scope entry
        
        Args:
            scope_id: Scope ID
            
        Returns:
            tuple: (success, error_message)
        """
        try:
            scope = Scope.query.get(scope_id)
            
            if not scope:
                return False, "Scope not found"
            
            db.session.delete(scope)
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
    
    @staticmethod
    def bulk_add_scopes(target_id, scope_list):
        """
        Add multiple scopes at once
        
        Args:
            target_id: Target ID
            scope_list: List of dicts with scope data
            
        Returns:
            tuple: (created_count, error_message)
        """
        try:
            # Validate target exists
            target = Target.query.get(target_id)
            if not target:
                return 0, "Target not found"
            
            created_count = 0
            
            for scope_data in scope_list:
                scope = Scope(
                    target_id=target_id,
                    scope_type=scope_data.get('scope_type', 'domain'),
                    value=scope_data.get('value', '').strip(),
                    in_scope=scope_data.get('in_scope', True),
                    notes=scope_data.get('notes'),
                    priority=scope_data.get('priority', 5)
                )
                db.session.add(scope)
                created_count += 1
            
            db.session.commit()
            return created_count, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return 0, f"Database error: {str(e)}"
