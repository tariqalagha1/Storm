from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserRole, DataSensitivityLevel
from ..schemas import AuditLogResponse, MessageResponse, PaginatedResponse
from ..permissions import require_permission, require_any_permission
from ..middleware import get_current_user_from_middleware
from ..audit import audit_logger, get_audit_logs, get_user_activity_summary

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Logs"])

@router.get("/logs", response_model=PaginatedResponse[AuditLogResponse])
async def get_audit_log_entries(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    start_date: Optional[datetime] = Query(None, description="Filter from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter to this date"),
    sensitivity_level: Optional[str] = Query(None, description="Filter by sensitivity level"),
    limit: int = Query(50, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_any_permission(["audit:read", "user:read"]))
):
    """Get audit log entries with filtering options"""
    
    # Non-admin users can only view their own audit logs
    if current_user.role != UserRole.ADMIN and user_id != current_user.id:
        if user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own audit logs"
            )
        user_id = current_user.id
    
    # Convert sensitivity level string to enum
    sensitivity_enum = None
    if sensitivity_level:
        try:
            sensitivity_enum = DataSensitivityLevel(sensitivity_level)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sensitivity level: {sensitivity_level}"
            )
    
    # Get audit logs
    logs = get_audit_logs(
        db=db,
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        sensitivity_level=sensitivity_enum,
        limit=limit,
        offset=offset
    )
    
    # Convert to response format
    log_responses = []
    for log in logs:
        log_response = AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            old_values=log.old_values,
            new_values=log.new_values,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            sensitivity_level=log.sensitivity_level.value,
            additional_context=log.additional_context,
            timestamp=log.timestamp
        )
        log_responses.append(log_response)
    
    # Get total count for pagination
    total_query = db.query(db.query(log.__class__).filter(
        *([log.__class__.user_id == user_id] if user_id else []),
        *([log.__class__.resource_type == resource_type] if resource_type else []),
        *([log.__class__.action == action] if action else []),
        *([log.__class__.timestamp >= start_date] if start_date else []),
        *([log.__class__.timestamp <= end_date] if end_date else []),
        *([log.__class__.sensitivity_level == sensitivity_enum] if sensitivity_enum else [])
    ).count())
    
    # Simplified count - in production you'd want a more efficient count query
    total = len(logs) + offset if len(logs) == limit else offset + len(logs)
    
    return PaginatedResponse(
        items=log_responses,
        total=total,
        page=offset // limit + 1,
        per_page=limit,
        pages=(total + limit - 1) // limit
    )

@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log_entry(
    log_id: int,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_any_permission(["audit:read", "user:read"]))
):
    """Get a specific audit log entry"""
    
    from ..models import AuditLog
    
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found"
        )
    
    # Non-admin users can only view their own audit logs
    if current_user.role != UserRole.ADMIN and log.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own audit logs"
        )
    
    return AuditLogResponse(
        id=log.id,
        user_id=log.user_id,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        old_values=log.old_values,
        new_values=log.new_values,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        sensitivity_level=log.sensitivity_level.value,
        additional_context=log.additional_context,
        timestamp=log.timestamp
    )

@router.get("/users/{user_id}/activity", response_model=dict)
async def get_user_activity(
    user_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_any_permission(["audit:read", "user:read"]))
):
    """Get user activity summary"""
    
    # Non-admin users can only view their own activity
    if current_user.role != UserRole.ADMIN and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own activity"
        )
    
    # Check if target user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    summary = get_user_activity_summary(db, user_id, days)
    
    return {
        "user_id": user_id,
        "analysis_period_days": days,
        "summary": summary
    }

@router.get("/stats", response_model=dict)
async def get_audit_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("audit:read"))
):
    """Get audit statistics (admin only)"""
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    from ..models import AuditLog
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all logs in the period
    logs = db.query(AuditLog).filter(
        AuditLog.timestamp >= start_date
    ).all()
    
    stats = {
        "period_days": days,
        "total_actions": len(logs),
        "unique_users": len(set(log.user_id for log in logs if log.user_id)),
        "actions_by_type": {},
        "resources_by_type": {},
        "sensitivity_breakdown": {
            "public": 0,
            "internal": 0,
            "confidential": 0,
            "restricted": 0
        },
        "failed_actions": 0,
        "top_users": {},
        "hourly_distribution": {str(i): 0 for i in range(24)}
    }
    
    for log in logs:
        # Actions by type
        stats["actions_by_type"][log.action] = stats["actions_by_type"].get(log.action, 0) + 1
        
        # Resources by type
        stats["resources_by_type"][log.resource_type] = stats["resources_by_type"].get(log.resource_type, 0) + 1
        
        # Sensitivity breakdown
        sensitivity_key = log.sensitivity_level.value.lower()
        stats["sensitivity_breakdown"][sensitivity_key] += 1
        
        # Failed actions
        if log.action.endswith('_failed'):
            stats["failed_actions"] += 1
        
        # Top users
        if log.user_id:
            stats["top_users"][log.user_id] = stats["top_users"].get(log.user_id, 0) + 1
        
        # Hourly distribution
        hour = str(log.timestamp.hour)
        stats["hourly_distribution"][hour] += 1
    
    # Convert top users to sorted list
    stats["top_users"] = sorted(
        [(user_id, count) for user_id, count in stats["top_users"].items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]  # Top 10 users
    
    return stats

@router.post("/export", response_model=MessageResponse)
async def export_audit_logs(
    start_date: datetime,
    end_date: datetime,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("audit:export"))
):
    """Export audit logs to CSV (admin only)"""
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Validate date range
    if end_date <= start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )
    
    # Limit export to reasonable time ranges
    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export period cannot exceed 365 days"
        )
    
    # Log the export action
    audit_logger.log_action(
        db=db,
        user_id=current_user.id,
        action="audit_export",
        resource_type="audit_log",
        additional_context={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "filter_user_id": user_id,
            "filter_resource_type": resource_type
        }
    )
    
    # In a real implementation, you would:
    # 1. Generate CSV file with audit logs
    # 2. Store it temporarily or send via email
    # 3. Return download link or confirmation
    
    return MessageResponse(
        message=f"Audit log export initiated for period {start_date.date()} to {end_date.date()}"
    )

@router.delete("/logs/cleanup", response_model=MessageResponse)
async def cleanup_old_audit_logs(
    days_to_keep: int = Query(365, ge=30, le=2555, description="Number of days of logs to keep"),
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("audit:delete"))
):
    """Clean up old audit logs (admin only)"""
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    from ..models import AuditLog
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    # Count logs to be deleted
    logs_to_delete = db.query(AuditLog).filter(
        AuditLog.timestamp < cutoff_date
    ).count()
    
    if logs_to_delete == 0:
        return MessageResponse(message="No old audit logs found to clean up")
    
    # Delete old logs
    deleted_count = db.query(AuditLog).filter(
        AuditLog.timestamp < cutoff_date
    ).delete()
    
    # Log the cleanup action
    audit_logger.log_action(
        db=db,
        user_id=current_user.id,
        action="audit_cleanup",
        resource_type="audit_log",
        additional_context={
            "cutoff_date": cutoff_date.isoformat(),
            "days_kept": days_to_keep,
            "logs_deleted": deleted_count
        }
    )
    
    db.commit()
    
    return MessageResponse(
        message=f"Successfully deleted {deleted_count} audit log entries older than {days_to_keep} days"
    )