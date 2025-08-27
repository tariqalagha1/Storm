from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import event, inspect
from fastapi import Request
import json
import logging
from functools import wraps

from .models import AuditLog, User, DataSensitivityLevel
from .security import SensitiveFieldHandler

logger = logging.getLogger(__name__)

class AuditLogger:
    """Comprehensive audit logging system for sensitive data access and modifications"""
    
    def __init__(self):
        self.sensitive_handler = SensitiveFieldHandler()
        self.sensitive_actions = {
            'user_login', 'user_logout', 'password_change', 'email_change',
            'api_key_create', 'api_key_delete', 'permission_grant', 'permission_revoke',
            'sensitive_data_access', 'data_export', 'data_import', 'webhook_trigger'
        }
    
    def log_action(
        self,
        db: Session,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log an action with comprehensive audit information"""
        
        # Sanitize sensitive data in old and new values
        sanitized_old = self._sanitize_audit_data(old_values) if old_values else None
        sanitized_new = self._sanitize_audit_data(new_values) if new_values else None
        
        # Determine sensitivity level
        sensitivity_level = self._determine_sensitivity_level(action, resource_type, sanitized_new)
        
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=sanitized_old,
            new_values=sanitized_new,
            ip_address=ip_address,
            user_agent=user_agent,
            sensitivity_level=sensitivity_level,
            additional_context=additional_context or {},
            timestamp=datetime.utcnow()
        )
        
        db.add(audit_log)
        
        # Log to application logger for high sensitivity actions
        if sensitivity_level in [DataSensitivityLevel.CONFIDENTIAL, DataSensitivityLevel.RESTRICTED]:
            logger.warning(
                f"High sensitivity action logged: {action} on {resource_type} by user {user_id}"
            )
        
        return audit_log
    
    def _sanitize_audit_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data for audit logging"""
        if not data:
            return data
        
        sanitized = {}
        for key, value in data.items():
            if self.sensitive_handler.is_sensitive_field(key, str(value) if value else ""):
                # For audit logs, we mask but keep some information for tracking
                if key in ['password', 'api_key', 'secret']:
                    sanitized[key] = "[REDACTED]"
                elif key in ['email']:
                    sanitized[key] = self.sensitive_handler.mask_email(str(value))
                elif key in ['phone', 'phone_number']:
                    sanitized[key] = self.sensitive_handler.mask_phone(str(value))
                else:
                    sanitized[key] = f"[MASKED:{type(value).__name__}]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _determine_sensitivity_level(
        self, 
        action: str, 
        resource_type: str, 
        data: Optional[Dict[str, Any]]
    ) -> DataSensitivityLevel:
        """Determine the sensitivity level of an audit log entry"""
        
        # High sensitivity actions
        if action in self.sensitive_actions:
            return DataSensitivityLevel.CONFIDENTIAL
        
        # Check for sensitive resource types
        sensitive_resources = ['user', 'api_key', 'subscription', 'external_integration']
        if resource_type in sensitive_resources:
            return DataSensitivityLevel.INTERNAL
        
        # Check for sensitive data in the payload
        if data:
            for key, value in data.items():
                if self.sensitive_handler.is_sensitive_field(key, str(value) if value else ""):
                    return DataSensitivityLevel.CONFIDENTIAL
        
        return DataSensitivityLevel.PUBLIC
    
    def log_api_access(
        self,
        db: Session,
        user_id: Optional[int],
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        """Log API access with request/response data"""
        
        # Determine if this is a sensitive endpoint
        sensitive_endpoints = [
            '/external/', '/api/users/', '/api/auth/', '/api/subscriptions/',
            '/webhook', '/sync', '/integrations'
        ]
        
        is_sensitive = any(endpoint.startswith(se) for se in sensitive_endpoints)
        
        context = {
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'response_time': response_time,
            'is_sensitive_endpoint': is_sensitive
        }
        
        # Add sanitized request/response data for sensitive endpoints
        if is_sensitive:
            if request_data:
                context['request_data'] = self._sanitize_audit_data(request_data)
            if response_data and status_code >= 400:  # Log response data only for errors
                context['response_data'] = self._sanitize_audit_data(response_data)
        
        self.log_action(
            db=db,
            user_id=user_id,
            action='api_access',
            resource_type='api_endpoint',
            ip_address=ip_address,
            user_agent=user_agent,
            additional_context=context
        )
    
    def log_data_access(
        self,
        db: Session,
        user_id: int,
        resource_type: str,
        resource_id: int,
        access_type: str,  # 'read', 'write', 'delete'
        fields_accessed: Optional[List[str]] = None,
        ip_address: Optional[str] = None
    ):
        """Log access to sensitive data with field-level tracking"""
        
        context = {
            'access_type': access_type,
            'fields_accessed': fields_accessed or [],
            'sensitive_fields': []
        }
        
        # Identify which accessed fields are sensitive
        if fields_accessed:
            for field in fields_accessed:
                if self.sensitive_handler.is_sensitive_field(field, ""):
                    context['sensitive_fields'].append(field)
        
        self.log_action(
            db=db,
            user_id=user_id,
            action=f'data_{access_type}',
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            additional_context=context
        )
    
    def log_permission_change(
        self,
        db: Session,
        admin_user_id: int,
        target_user_id: int,
        permission: str,
        action: str,  # 'grant' or 'revoke'
        ip_address: Optional[str] = None
    ):
        """Log permission changes with detailed context"""
        
        context = {
            'target_user_id': target_user_id,
            'permission': permission,
            'permission_action': action
        }
        
        self.log_action(
            db=db,
            user_id=admin_user_id,
            action=f'permission_{action}',
            resource_type='user_permission',
            resource_id=target_user_id,
            ip_address=ip_address,
            additional_context=context
        )

# Global audit logger instance
audit_logger = AuditLogger()

# Decorator for automatic audit logging
def audit_action(action: str, resource_type: str, sensitivity_level: str = "medium"):
    """Decorator to automatically audit function calls"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract common parameters
            db = kwargs.get('db') or next((arg for arg in args if isinstance(arg, Session)), None)
            current_user = kwargs.get('current_user')
            request = kwargs.get('request')
            
            user_id = current_user.id if current_user else None
            ip_address = request.client.host if request else None
            user_agent = request.headers.get('user-agent') if request else None
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful action
                if db:
                    audit_logger.log_action(
                        db=db,
                        user_id=user_id,
                        action=action,
                        resource_type=resource_type,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        additional_context={'status': 'success'}
                    )
                    db.commit()
                
                return result
                
            except Exception as e:
                # Log failed action
                if db:
                    audit_logger.log_action(
                        db=db,
                        user_id=user_id,
                        action=f"{action}_failed",
                        resource_type=resource_type,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        additional_context={
                            'status': 'failed',
                            'error': str(e),
                            'error_type': type(e).__name__
                        }
                    )
                    db.commit()
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Similar logic for synchronous functions
            db = kwargs.get('db') or next((arg for arg in args if isinstance(arg, Session)), None)
            current_user = kwargs.get('current_user')
            request = kwargs.get('request')
            
            user_id = current_user.id if current_user else None
            ip_address = request.client.host if request else None
            user_agent = request.headers.get('user-agent') if request else None
            
            try:
                result = func(*args, **kwargs)
                
                if db:
                    audit_logger.log_action(
                        db=db,
                        user_id=user_id,
                        action=action,
                        resource_type=resource_type,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        additional_context={'status': 'success'}
                    )
                    db.commit()
                
                return result
                
            except Exception as e:
                if db:
                    audit_logger.log_action(
                        db=db,
                        user_id=user_id,
                        action=f"{action}_failed",
                        resource_type=resource_type,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        additional_context={
                            'status': 'failed',
                            'error': str(e),
                            'error_type': type(e).__name__
                        }
                    )
                    db.commit()
                
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# SQLAlchemy event listeners for automatic model change tracking
def setup_model_audit_listeners():
    """Set up SQLAlchemy event listeners for automatic audit logging"""
    
    from .models import User, Project, APIKey, Subscription, ExternalIntegration
    
    # Models to track
    tracked_models = [User, Project, APIKey, Subscription, ExternalIntegration]
    
    for model in tracked_models:
        # Track updates
        @event.listens_for(model, 'before_update')
        def receive_before_update(mapper, connection, target):
            # Store original values for comparison
            state = inspect(target)
            target._audit_old_values = {}
            
            for attr in state.attrs:
                if attr.history.has_changes():
                    old_value = attr.history.deleted[0] if attr.history.deleted else None
                    target._audit_old_values[attr.key] = old_value
        
        @event.listens_for(model, 'after_update')
        def receive_after_update(mapper, connection, target):
            # This would need access to the current session and user context
            # In practice, you'd need to implement this with request context
            pass
        
        # Track deletions
        @event.listens_for(model, 'before_delete')
        def receive_before_delete(mapper, connection, target):
            # Store values before deletion
            target._audit_deleted_values = {}
            for column in mapper.columns:
                target._audit_deleted_values[column.name] = getattr(target, column.name)

# Audit query functions
def get_audit_logs(
    db: Session,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sensitivity_level: Optional[DataSensitivityLevel] = None,
    limit: int = 100,
    offset: int = 0
) -> List[AuditLog]:
    """Query audit logs with filtering options"""
    
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    if sensitivity_level:
        query = query.filter(AuditLog.sensitivity_level == sensitivity_level)
    
    return query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

def get_user_activity_summary(
    db: Session,
    user_id: int,
    days: int = 30
) -> Dict[str, Any]:
    """Get summary of user activity for the specified number of days"""
    
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    logs = db.query(AuditLog).filter(
        AuditLog.user_id == user_id,
        AuditLog.timestamp >= start_date
    ).all()
    
    summary = {
        'total_actions': len(logs),
        'actions_by_type': {},
        'resources_accessed': {},
        'sensitive_actions': 0,
        'failed_actions': 0,
        'last_activity': None
    }
    
    for log in logs:
        # Count actions by type
        summary['actions_by_type'][log.action] = summary['actions_by_type'].get(log.action, 0) + 1
        
        # Count resources accessed
        summary['resources_accessed'][log.resource_type] = summary['resources_accessed'].get(log.resource_type, 0) + 1
        
        # Count sensitive actions
        if log.sensitivity_level in [DataSensitivityLevel.CONFIDENTIAL, DataSensitivityLevel.RESTRICTED]:
            summary['sensitive_actions'] += 1
        
        # Count failed actions
        if log.action.endswith('_failed'):
            summary['failed_actions'] += 1
        
        # Track last activity
        if not summary['last_activity'] or log.timestamp > summary['last_activity']:
            summary['last_activity'] = log.timestamp
    
    return summary