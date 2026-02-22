"""
Target Service
Business logic for target management
"""
from app.extensions import db
from app.models import Target, AttackProfile
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class TargetService:
    """Service class for target operations"""
    
    @staticmethod
    def create_target(name, base_domain, program_platform='Self', 
                     description=None, notes=None, status='active'):
        """
        Create a new target with default attack profiles
        
        Args:
            name: Target name
            base_domain: Base domain
            program_platform: Bug bounty platform
            description: Optional description
            notes: Optional notes
            status: Target status (default: active)
            
        Returns:
            tuple: (target, error_message)
        """
        try:
            # Validate required fields
            if not name or not base_domain:
                return None, "Name and base domain are required"
            
            # Create target
            target = Target(
                name=name.strip(),
                base_domain=base_domain.strip(),
                program_platform=program_platform,
                description=description,
                notes=notes,
                status=status
            )
            
            db.session.add(target)
            db.session.flush()  # Get target ID before commit
            
            # Create default attack profiles
            default_profiles = AttackProfile.get_default_profiles()
            for profile_data in default_profiles:
                attack_profile = AttackProfile(
                    target_id=target.id,
                    attack_type=profile_data['attack_type'],
                    enabled=profile_data['enabled'],
                    rate_limit=profile_data['rate_limit']
                )
                db.session.add(attack_profile)
            
            db.session.commit()
            return target, None
            
        except IntegrityError as e:
            db.session.rollback()
            return None, f"Target with name '{name}' already exists"
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
    
    @staticmethod
    def get_target(target_id):
        """
        Get target by ID
        
        Args:
            target_id: Target ID
            
        Returns:
            Target or None
        """
        return Target.query.get(target_id)
    
    @staticmethod
    def get_all_targets(status=None):
        """
        Get all targets, optionally filtered by status
        
        Args:
            status: Filter by status (optional)
            
        Returns:
            list of Target objects
        """
        query = Target.query
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(Target.created_at.desc()).all()
    
    @staticmethod
    def update_target(target_id, **kwargs):
        """
        Update target fields
        
        Args:
            target_id: Target ID
            **kwargs: Fields to update
            
        Returns:
            tuple: (target, error_message)
        """
        try:
            target = Target.query.get(target_id)
            
            if not target:
                return None, "Target not found"
            
            # Update allowed fields
            allowed_fields = ['name', 'base_domain', 'program_platform', 
                            'description', 'notes', 'status']
            
            for key, value in kwargs.items():
                if key in allowed_fields and value is not None:
                    setattr(target, key, value)
            
            db.session.commit()
            return target, None
            
        except IntegrityError:
            db.session.rollback()
            return None, f"Target with name '{kwargs.get('name')}' already exists"
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
    
    @staticmethod
    def delete_target(target_id):
        """
        Delete a target (cascades to scope, attack profiles, results)
        
        Args:
            target_id: Target ID
            
        Returns:
            tuple: (success, error_message)
        """
        try:
            target = Target.query.get(target_id)
            
            if not target:
                return False, "Target not found"
            
            db.session.delete(target)
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
    
    @staticmethod
    def get_target_stats():
        """
        Get overall target statistics
        
        Returns:
            dict with statistics
        """
        total = Target.query.count()
        active = Target.query.filter_by(status='active').count()
        paused = Target.query.filter_by(status='paused').count()
        
        return {
            'total': total,
            'active': active,
            'paused': paused
        }
