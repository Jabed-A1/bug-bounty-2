"""
Attack Service
Business logic for attack profile and scan result management
"""
from app.extensions import db
from app.models import AttackProfile, ScanResult, Target
from sqlalchemy.exc import SQLAlchemyError, IntegrityError


class AttackService:
    """Service class for attack profile and scan operations"""
    
    @staticmethod
    def get_attack_profile(profile_id):
        """
        Get attack profile by ID
        
        Args:
            profile_id: Attack profile ID
            
        Returns:
            AttackProfile or None
        """
        return AttackProfile.query.get(profile_id)
    
    @staticmethod
    def get_target_attack_profiles(target_id):
        """
        Get all attack profiles for a target
        
        Args:
            target_id: Target ID
            
        Returns:
            list of AttackProfile objects
        """
        return AttackProfile.query.filter_by(target_id=target_id)\
            .order_by(AttackProfile.attack_type).all()
    
    @staticmethod
    def update_attack_profile(profile_id, **kwargs):
        """
        Update attack profile settings
        
        Args:
            profile_id: Attack profile ID
            **kwargs: Fields to update
            
        Returns:
            tuple: (profile, error_message)
        """
        try:
            profile = AttackProfile.query.get(profile_id)
            
            if not profile:
                return None, "Attack profile not found"
            
            # Update allowed fields
            allowed_fields = ['enabled', 'rate_limit', 'max_threads', 'config_json', 'notes']
            
            for key, value in kwargs.items():
                if key in allowed_fields and value is not None:
                    setattr(profile, key, value)
            
            db.session.commit()
            return profile, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
    
    @staticmethod
    def add_attack_profile(target_id, attack_type, enabled=True, rate_limit=10, 
                          max_threads=5, notes=None):
        """
        Add a new attack profile to a target
        
        Args:
            target_id: Target ID
            attack_type: Type of attack
            enabled: Whether profile is enabled
            rate_limit: Rate limit for requests
            max_threads: Max concurrent threads
            notes: Optional notes
            
        Returns:
            tuple: (profile, error_message)
        """
        try:
            # Validate target exists
            target = Target.query.get(target_id)
            if not target:
                return None, "Target not found"
            
            # Validate attack type
            if attack_type not in AttackProfile.get_attack_types():
                return None, f"Invalid attack type: {attack_type}"
            
            # Create profile
            profile = AttackProfile(
                target_id=target_id,
                attack_type=attack_type,
                enabled=enabled,
                rate_limit=rate_limit,
                max_threads=max_threads,
                notes=notes
            )
            
            db.session.add(profile)
            db.session.commit()
            return profile, None
            
        except IntegrityError:
            db.session.rollback()
            return None, f"Attack profile '{attack_type}' already exists for this target"
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
    
    @staticmethod
    def toggle_attack_profile(profile_id):
        """
        Toggle attack profile enabled status
        
        Args:
            profile_id: Attack profile ID
            
        Returns:
            tuple: (profile, error_message)
        """
        try:
            profile = AttackProfile.query.get(profile_id)
            
            if not profile:
                return None, "Attack profile not found"
            
            profile.enabled = not profile.enabled
            db.session.commit()
            return profile, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
    
    # Scan Result Methods (Phase 1 placeholder)
    
    @staticmethod
    def create_scan_result(target_id, attack_type, status='pending'):
        """
        Create a placeholder scan result (for Phase 2+ expansion)
        
        Args:
            target_id: Target ID
            attack_type: Type of attack
            status: Initial status
            
        Returns:
            tuple: (scan_result, error_message)
        """
        try:
            # Validate target exists
            target = Target.query.get(target_id)
            if not target:
                return None, "Target not found"
            
            scan_result = ScanResult(
                target_id=target_id,
                attack_type=attack_type,
                status=status
            )
            
            db.session.add(scan_result)
            db.session.commit()
            return scan_result, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
    
    @staticmethod
    def get_scan_results(target_id=None, attack_type=None, status=None, limit=50):
        """
        Get scan results with optional filters
        
        Args:
            target_id: Filter by target (optional)
            attack_type: Filter by attack type (optional)
            status: Filter by status (optional)
            limit: Maximum results to return
            
        Returns:
            list of ScanResult objects
        """
        query = ScanResult.query
        
        if target_id:
            query = query.filter_by(target_id=target_id)
        
        if attack_type:
            query = query.filter_by(attack_type=attack_type)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(ScanResult.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_scan_result(result_id):
        """
        Get scan result by ID
        
        Args:
            result_id: Scan result ID
            
        Returns:
            ScanResult or None
        """
        return ScanResult.query.get(result_id)
