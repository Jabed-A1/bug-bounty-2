"""
Target management routes
CRUD operations for targets, scopes, and attack profiles
"""
from flask import render_template, request, redirect, url_for, flash, current_app
from app.routes import target_bp
from app.services import TargetService, ScopeService, AttackService
from app.utils import AuditLogger
from app.models import Scope, AttackProfile


@target_bp.route('/')
def list_targets():
    """List all targets"""
    status_filter = request.args.get('status')
    targets = TargetService.get_all_targets(status=status_filter)
    
    return render_template('targets/list.html', targets=targets, status_filter=status_filter)


@target_bp.route('/new', methods=['GET', 'POST'])
def new_target():
    """Create a new target"""
    if request.method == 'POST':
        name = request.form.get('name')
        base_domain = request.form.get('base_domain')
        program_platform = request.form.get('program_platform', 'Self')
        description = request.form.get('description')
        notes = request.form.get('notes')
        
        target, error = TargetService.create_target(
            name=name,
            base_domain=base_domain,
            program_platform=program_platform,
            description=description,
            notes=notes
        )
        
        if error:
            flash(error, 'danger')
        else:
            # Log the action
            audit = AuditLogger(current_app.logger)
            audit.log_target_created(target.id, target.name)
            
            flash(f'Target "{target.name}" created successfully', 'success')
            return redirect(url_for('targets.view_target', target_id=target.id))
    
    return render_template('targets/new.html')


@target_bp.route('/<int:target_id>')
def view_target(target_id):
    """View target details with scope and attack profiles"""
    target = TargetService.get_target(target_id)
    
    if not target:
        flash('Target not found', 'danger')
        return redirect(url_for('targets.list_targets'))
    
    # Get scopes
    in_scope = ScopeService.get_target_scopes(target_id, in_scope=True)
    out_of_scope = ScopeService.get_target_scopes(target_id, in_scope=False)
    
    # Get attack profiles
    attack_profiles = AttackService.get_target_attack_profiles(target_id)
    
    # Get recent scan results
    recent_scans = AttackService.get_scan_results(target_id=target_id, limit=20)
    
    return render_template('targets/view.html',
                         target=target,
                         in_scope=in_scope,
                         out_of_scope=out_of_scope,
                         attack_profiles=attack_profiles,
                         recent_scans=recent_scans,
                         scope_types=Scope.get_scope_types(),
                         attack_types=AttackProfile.get_attack_types())


@target_bp.route('/<int:target_id>/edit', methods=['GET', 'POST'])
def edit_target(target_id):
    """Edit target information"""
    target = TargetService.get_target(target_id)
    
    if not target:
        flash('Target not found', 'danger')
        return redirect(url_for('targets.list_targets'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        base_domain = request.form.get('base_domain')
        program_platform = request.form.get('program_platform')
        description = request.form.get('description')
        notes = request.form.get('notes')
        status = request.form.get('status')
        
        target, error = TargetService.update_target(
            target_id,
            name=name,
            base_domain=base_domain,
            program_platform=program_platform,
            description=description,
            notes=notes,
            status=status
        )
        
        if error:
            flash(error, 'danger')
        else:
            # Log the action
            audit = AuditLogger(current_app.logger)
            audit.log_target_updated(target.id, {'status': status})
            
            flash('Target updated successfully', 'success')
            return redirect(url_for('targets.view_target', target_id=target.id))
    
    return render_template('targets/edit.html', target=target)


@target_bp.route('/<int:target_id>/delete', methods=['POST'])
def delete_target(target_id):
    """Delete a target"""
    success, error = TargetService.delete_target(target_id)
    
    if error:
        flash(error, 'danger')
    else:
        # Log the action
        audit = AuditLogger(current_app.logger)
        audit.log_target_deleted(target_id)
        
        flash('Target deleted successfully', 'success')
    
    return redirect(url_for('targets.list_targets'))


@target_bp.route('/<int:target_id>/scope/add', methods=['POST'])
def add_scope(target_id):
    """Add scope entry to target"""
    scope_type = request.form.get('scope_type')
    value = request.form.get('value')
    in_scope = request.form.get('in_scope') == 'true'
    notes = request.form.get('notes')
    priority = int(request.form.get('priority', 5))
    
    scope, error = ScopeService.add_scope(
        target_id=target_id,
        scope_type=scope_type,
        value=value,
        in_scope=in_scope,
        notes=notes,
        priority=priority
    )
    
    if error:
        flash(error, 'danger')
    else:
        # Log the action
        audit = AuditLogger(current_app.logger)
        audit.log_scope_added(scope.id, target_id, scope_type, value)
        
        flash('Scope added successfully', 'success')
    
    return redirect(url_for('targets.view_target', target_id=target_id))


@target_bp.route('/<int:target_id>/scope/<int:scope_id>/delete', methods=['POST'])
def delete_scope(target_id, scope_id):
    """Delete a scope entry"""
    success, error = ScopeService.delete_scope(scope_id)
    
    if error:
        flash(error, 'danger')
    else:
        # Log the action
        audit = AuditLogger(current_app.logger)
        audit.log_scope_deleted(scope_id, target_id)
        
        flash('Scope deleted successfully', 'success')
    
    return redirect(url_for('targets.view_target', target_id=target_id))


@target_bp.route('/<int:target_id>/attack/<int:profile_id>/toggle', methods=['POST'])
def toggle_attack_profile(target_id, profile_id):
    """Toggle attack profile enabled status"""
    profile, error = AttackService.toggle_attack_profile(profile_id)
    
    if error:
        flash(error, 'danger')
    else:
        # Log the action
        audit = AuditLogger(current_app.logger)
        audit.log_attack_profile_updated(profile.id, profile.attack_type, profile.enabled)
        
        status = 'enabled' if profile.enabled else 'disabled'
        flash(f'Attack profile "{profile.attack_type}" {status}', 'success')
    
    return redirect(url_for('targets.view_target', target_id=target_id))


@target_bp.route('/<int:target_id>/attack/<int:profile_id>/update', methods=['POST'])
def update_attack_profile(target_id, profile_id):
    """Update attack profile settings"""
    rate_limit = request.form.get('rate_limit', type=int)
    max_threads = request.form.get('max_threads', type=int)
    notes = request.form.get('notes')
    
    profile, error = AttackService.update_attack_profile(
        profile_id,
        rate_limit=rate_limit,
        max_threads=max_threads,
        notes=notes
    )
    
    if error:
        flash(error, 'danger')
    else:
        flash('Attack profile updated successfully', 'success')
    
    return redirect(url_for('targets.view_target', target_id=target_id))
